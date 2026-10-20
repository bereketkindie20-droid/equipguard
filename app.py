import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
from datetime import datetime
import os
from PIL import Image
from streamlit_folium import st_folium
import folium
import requests
from db import get_connection, init_db
from utils import is_within_geofence, compare_photos

st.set_page_config(page_title="EquipGuard - Fotogenic Studio Tracker", layout="wide")

init_db()

st.title("🛡️ EquipGuard: Fotogenic Studio Fleet & Location X Tracker")
st.markdown("Professional gear tracking from Mickey Leland St base to Location X, 25km geofence monitoring, and AI inspection.")

# Fotogenic Studio Home Base Coordinates (Mickey Leland St, Addis Ababa)
STUDIO_LAT, STUDIO_LNG = 9.011556, 38.781258

# --- SECURITY & PRE-CONFIGURED TELEGRAM SETUP ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Hardcoded Telegram Credentials for Fotogenic Studio
TELEGRAM_BOT_TOKEN = "8417435900:AAHn1WCKaAbuY1zz1MxHsbybv-nqR_vSOQM"
TELEGRAM_CHAT_ID = "8108017872"

st.sidebar.title("🔐 Studio Access Portal")
password_input = st.sidebar.text_input("Manager Password", type="password")

ADMIN_PASSWORD = "fotogenic2026"

if password_input == ADMIN_PASSWORD:
    st.session_state["authenticated"] = True

if st.session_state["authenticated"]:
    st.sidebar.success("🔓 Manager Mode Unlocked")
    if st.sidebar.button("Lock Session"):
        st.session_state["authenticated"] = False
        st.rerun()
else:
    st.sidebar.info("🔒 Public Mode: View inventory and live map. Enter manager password for admin actions.")

# Telegram Notification Helper Function
def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Telegram alert error:", e)

# Navigation
choice = st.sidebar.radio("Go to", [
    "Dashboard & Live Fleet Map", 
    "Equipment Inventory (Catalog)", 
    "On-Location GPS Ping (Location X)",
    "Check-Out / Check-In Inspection (Manager Only)"
])

conn = get_connection()

if choice == "Dashboard & Live Fleet Map":
    st.subheader("📍 Fotogenic Studio Fleet & Location X Status")
    
    col1, col2, col3 = st.columns(3)
    total_eq = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    rented_eq = conn.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Rented'").fetchone()[0]
    available_eq = conn.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Available'").fetchone()[0]
    
    col1.metric("Total Studio Gear", total_eq)
    col2.metric("Rented Out (On Location X)", rented_eq)
    col3.metric("At Studio (Available)", available_eq)
    
    st.markdown("---")
    st.markdown("### 🗺️ Live Map: Fotogenic Studio Base vs. Gear at Location X")
    
    m = folium.Map(location=[STUDIO_LAT, STUDIO_LNG], zoom_start=12)
    
    folium.Marker(
        location=[STUDIO_LAT, STUDIO_LNG],
        popup="<b>🏠 Fotogenic Studio Base (Mickey Leland St)</b>",
        icon=folium.Icon(color="blue", icon="home", prefix="fa")
    ).add_to(m)
    
    folium.Circle(
        location=[STUDIO_LAT, STUDIO_LNG],
        radius=25000,
        color='blue',
        fill=True,
        fill_opacity=0.08,
        tooltip="25km Authorized Operational Zone"
    ).add_to(m)
    
    equipment_list = conn.execute("SELECT equipment_id, name, category, status, current_lat, current_lng, last_location_update FROM equipment").fetchall()
    
    for eq in equipment_list:
        eq_id, name, category, status, lat, lng, last_update = eq[0], eq[1], eq[2], eq[3], eq[4], eq[5], eq[6]
        
        lat = float(lat) if lat is not None else STUDIO_LAT
        lng = float(lng) if lng is not None else STUDIO_LNG
        
        inside, dist = is_within_geofence(lat, lng)
        is_rented = (status == 'Rented')
        
        status_color = "red" if not inside else ("orange" if is_rented else "green")
        
        popup_html = f"""
        <b>Equipment:</b> {name} ({eq_id})<br>
        <b>Status:</b> <span style="color:{status_color};"><b>{'On Location X' if is_rented else 'In Studio'}</b></span><br>
        <b>Distance from Studio:</b> {round(dist, 2)} km<br>
        <b>Last Updated:</b> {last_update or 'N/A'}
        """
        
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=status_color, icon="camera" if is_rented else "box", prefix="fa")
        ).add_to(m)
        
    st_folium(m, width=1200, height=520)

elif choice == "Equipment Inventory (Catalog)":
    st.subheader("📦 Fotogenic Studio Equipment Catalog")
    st.markdown("Browse available and rented equipment items currently in our studio catalog.")
    
    df_eq = pd.read_sql("SELECT equipment_id, name, category, model, status FROM equipment", conn)
    st.dataframe(df_eq, use_container_width=True)
    
    if st.session_state["authenticated"]:
        st.markdown("---")
        with st.expander("➕ Add New Studio Equipment (Manager Only)"):
            with st.form("add_eq_form"):
                eq_id = st.text_input("Equipment ID (e.g., EQ-CAM-02)")
                name = st.text_input("Equipment Name")
                category = st.selectbox("Category", ["Camera", "Lens", "Light", "Audio", "Accessories"])
                model = st.text_input("Model")
                serial = st.text_input("Serial Number")
                tracker_id = st.text_input("Tracker ID (optional)")
                submit = st.form_submit_button("Save Equipment")
                
                if submit and eq_id and name:
                    try:
                        conn.execute("""
                            INSERT INTO equipment (equipment_id, name, category, model, serial_number, tracker_id, current_lat, current_lng, status) 
                            VALUES (?,?,?,?,?,?,?,?,'Available')
                        """, (eq_id, name, category, model, serial, tracker_id if tracker_id else None, STUDIO_LAT, STUDIO_LNG))
                        conn.commit()
                        st.success("Equipment added successfully to Fotogenic Studio inventory!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.info("🔒 Want to add new equipment? Enter your manager password in the sidebar.")

elif choice == "On-Location GPS Ping (Location X)":
    st.subheader("📡 Update Live Location X from Smartphone")
    st.markdown("When on location with rented equipment, use this page on a smartphone to update the item's live location on the Fotogenic Studio map.")

    rented_items = conn.execute("SELECT equipment_id, name, current_lat, current_lng FROM equipment WHERE status='Rented'").fetchall()
    item_map = {f"{r[1]} ({r[0]})": r for r in rented_items}

    if not item_map:
        st.info("No equipment is currently rented out.")
    else:
        selected_item_key = st.selectbox("Select Equipment on Location X", list(item_map.keys()))
        selected_item = item_map[selected_item_key]
        eq_id, eq_name, cur_lat, cur_lng = selected_item[0], selected_item[1], selected_item[2], selected_item[3]

        geo_html = """
        <div style="padding: 20px; background-color: #1e1e1e; border-radius: 10px; color: white; text-align: center;">
            <h3>📍 Smartphone Location X Detector</h3>
            <p>Click below to capture your current location GPS coordinates:</p>
            <button onclick="getLocation()" style="background-color: #ff4b4b; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">Get Current GPS Location</button>
            <p id="demo" style="margin-top: 15px; font-family: monospace; font-size: 16px; color: #00ffcc;"></p>
        </div>

        <script>
        var x = document.getElementById("demo");
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(showPosition, showError);
            } else {
                x.innerHTML = "Geolocation is not supported by this browser.";
            }
        }
        function showPosition(position) {
            x.innerHTML = "LAT: " + position.coords.latitude + " | LNG: " + position.coords.longitude;
        }
        function showError(error) {
            x.innerHTML = "Error capturing location permission.";
        }
        </script>
        """
        components.html(geo_html, height=220)

        with st.form("update_location_x_form"):
            st.markdown("#### Save Location X Coordinates")
            new_lat = st.number_input("Latitude", value=float(cur_lat if cur_lat is not None else STUDIO_LAT), format="%.6f")
            new_lng = st.number_input("Longitude", value=float(cur_lng if cur_lng is not None else STUDIO_LNG), format="%.6f")
            
            submit_loc = st.form_submit_button("Update Equipment Position to Location X")
            
            if submit_loc:
                now = datetime.now()
                
                conn.execute("""
                    UPDATE equipment 
                    SET current_lat=?, current_lng=?, last_location_update=? 
                    WHERE equipment_id=?
                """, (new_lat, new_lng, now, eq_id))
                
                conn.execute("""
                    INSERT INTO location_logs (equipment_id, latitude, longitude, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (eq_id, new_lat, new_lng, now))
                
                conn.commit()
                
                inside, dist = is_within_geofence(new_lat, new_lng)
                if inside:
                    st.success(f"✅ Position updated! {eq_name} is at Location X ({round(dist, 2)} km from Fotogenic Studio).")
                else:
                    breach_msg = f"🚨 *GEOFENCE ALERT!* Equipment `{eq_name}` is {round(dist, 2)} km from Fotogenic Studio (EXCEEDS 25km LIMIT!)."
                    st.error(breach_msg)
                    send_telegram_alert(breach_msg)

elif choice == "Check-Out / Check-In Inspection (Manager Only)":
    if not st.session_state["authenticated"]:
        st.warning("🔒 This section is restricted to Fotogenic Studio managers. Please enter the manager password in the sidebar.")
    else:
        st.subheader("🔄 Gear Check-Out & Visual AI Damage Inspection")
        
        if st.button("🧪 Send Test Telegram Alert to My Phone"):
            send_telegram_alert("🔔 *Test Alert:* EquipGuard is successfully connected to Bereket's Telegram bot for Fotogenic Studio!")
            st.success("Test message sent! Check your Telegram app.")

        tab1, tab2, tab3 = st.tabs(["Check-Out Gear", "Check-In & Inspect Damage", "Active Rental Client Registry"])
        
        with tab1:
            st.markdown("### 📋 Client Registration & Check-Out")
            available_eq = conn.execute("SELECT equipment_id, name FROM equipment WHERE status='Available'").fetchall()
            eq_options = {item[1]: item[0] for item in available_eq}
            
            selected_name = st.selectbox("Select Equipment to Rent Out", list(eq_options.keys()) if eq_options else ["No equipment available"])
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                client_name = st.text_input("Client / Crew Full Name")
                client_phone = st.text_input("Phone Number", value="+251 ")
            with col_c2:
                client_digital_id = st.text_input("Digital ID / National ID Number")
            
            baseline_file = st.file_uploader("Upload Clean Baseline Photo (Pre-Rental)", type=["jpg", "jpeg", "png"], key="baseline")
            
            if st.button("Confirm Check-Out & Register Client") and eq_options and client_name:
                eq_id = eq_options[selected_name]
                os.makedirs("uploads", exist_ok=True)
                baseline_path = None
                if baseline_file:
                    baseline_path = f"uploads/baseline_{eq_id}_{int(datetime.now().timestamp())}.jpg"
                    with open(baseline_path, "wb") as f:
                        f.write(baseline_file.getbuffer())
                
                conn.execute("UPDATE equipment SET status='Rented' WHERE equipment_id=?", (eq_id,))
                conn.execute("""
                    INSERT INTO inspections (equipment_id, client_name, client_phone, client_digital_id, check_out_time, baseline_photo, status) 
                    VALUES (?,?,?,?,?,?,'Active')
                """, (eq_id, client_name, client_phone, client_digital_id, datetime.now(), baseline_path))
                conn.commit()
                
                checkout_msg = f"📋 *Gear Check-Out Alert*\n\n📦 *Equipment:* {selected_name} (`{eq_id}`)\n👤 *Client:* {client_name}\n📞 *Phone:* {client_phone}\n🆔 *Digital ID:* {client_digital_id}\n📍 *Base:* Fotogenic Studio"
                send_telegram_alert(checkout_msg)
                
                st.success(f"✅ {selected_name} checked out to {client_name} from Fotogenic Studio!")
                st.rerun()
                
        with tab2:
            st.markdown("### Equipment Return & Visual Damage Inspection")
            active_rentals = conn.execute("""
                SELECT i.inspection_id, e.name, i.client_name, i.client_phone, i.baseline_photo 
                FROM inspections i JOIN equipment e ON i.equipment_id = e.equipment_id 
                WHERE i.status='Active' OR i.status='Pending'
            """).fetchall()
            
            rental_options = {f"{r[1]} — Client: {r[2]} ({r[3]})": r for r in active_rentals}
            selected_key = st.selectbox("Select Return Item", list(rental_options.keys()) if rental_options else ["No active rentals found"])
            uploaded_file = st.file_uploader("Upload Photo of Returned Gear (Post-Rental)", type=["jpg", "jpeg", "png"], key="return")
            
            if st.button("Run AI Inspection & Complete Return") and rental_options and uploaded_file:
                rental_info = rental_options[selected_key]
                insp_id, baseline_img_path = rental_info[0], rental_info[4]
                
                os.makedirs("uploads", exist_ok=True)
                return_img_path = f"uploads/return_{insp_id}.jpg"
                with open(return_img_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                if baseline_img_path and os.path.exists(baseline_img_path):
                    highlighted_img, damage_score = compare_photos(baseline_img_path, return_img_path)
                else:
                    highlighted_img, damage_score = compare_photos(return_img_path, return_img_path)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.image(uploaded_file, caption="Returned Gear Photo", use_container_width=True)
                with col_b:
                    if highlighted_img:
                        st.image(highlighted_img, caption=f"AI Diff Analysis (Damage Score: {damage_score}%)", use_container_width=True)
                    
                if damage_score > 3.0:
                    st.warning(f"⚠️ Damage Detected! Score: {damage_score}% difference.")
                else:
                    st.success(f"✅ Gear returned in clean condition. Damage Score: {damage_score}%")
                    
                conn.execute("UPDATE inspections SET check_in_time=?, return_photo=?, damage_score=?, status=? WHERE inspection_id=?",
                             (datetime.now(), return_img_path, damage_score, 'Completed', insp_id))
                
                eq_row = conn.execute("""
                    SELECT equipment.equipment_id, equipment.name 
                    FROM inspections 
                    JOIN equipment ON inspections.equipment_id = equipment.equipment_id 
                    WHERE inspections.inspection_id = ?
                """, (insp_id,)).fetchone()
                
                if eq_row:
                    conn.execute("""
                        UPDATE equipment 
                        SET status='Available', current_lat=?, current_lng=?, last_location_update=? 
                        WHERE equipment_id=?
                    """, (STUDIO_LAT, STUDIO_LNG, datetime.now(), eq_row[0]))
                    
                    # FIXED: Send Telegram Alert for BOTH normal returns and damaged returns
                    if damage_score > 3.0:
                        return_msg = f"⚠️ *DAMAGE ALERT!* Equipment Returned with Damage!\n\n📦 *Equipment:* {eq_row[1]}\n📊 *AI Damage Score:* `{damage_score}%`\n🏠 *Status:* Returned & Reset to Fotogenic Studio"
                    else:
                        return_msg = f"✅ *Gear Return & Inspection Completed*\n\n📦 *Equipment:* {eq_row[1]}\n📊 *AI Damage Score:* `{damage_score}%`\n🏠 *Status:* Returned & Reset to Fotogenic Studio"
                    
                    send_telegram_alert(return_msg)

                conn.commit()
                st.success("Inspection recorded and equipment location reset to Fotogenic Studio base!")

        with tab3:
            st.markdown("### 📇 Active Rental Client Registry")
            df_rentals = pd.read_sql("""
                SELECT i.inspection_id, e.name as Equipment, i.client_name as Client_Name, 
                       i.client_phone as Phone, i.client_digital_id as Digital_ID, 
                       i.check_out_time as Check_Out_Time, i.status
            FROM inspections i 
            JOIN equipment e ON i.equipment_id = e.equipment_id
            WHERE i.status='Active'
        """, conn)
        st.dataframe(df_rentals, use_container_width=True)

conn.close()
