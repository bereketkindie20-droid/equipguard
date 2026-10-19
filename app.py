import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
from datetime import datetime
import os
from PIL import Image
from streamlit_folium import st_folium
import folium
from db import get_connection, init_db
from utils import is_within_geofence, compare_photos

st.set_page_config(page_title="EquipGuard - Studio Equipment & Geofence System", layout="wide")

# Ensure DB schema is initialized
init_db()

st.title("🛡️ EquipGuard: Studio Equipment & Geofence System")
st.markdown("Zero-cost gear tracking, geofence compliance, and AI visual damage inspection for Addis Ababa studios.")

# Sidebar Navigation
st.sidebar.title("Navigation")
choice = st.sidebar.radio("Go to", ["Dashboard & Live Map", "Equipment Inventory", "Check-Out / Check-In Inspection", "Client Mobile GPS Check"])

conn = get_connection()

if choice == "Dashboard & Live Map":
    st.subheader("📍 Live Fleet & Geofence Status (Addis Ababa)")
    
    col1, col2, col3 = st.columns(3)
    
    total_eq = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    rented_eq = conn.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Rented'").fetchone()[0]
    trackers_count = conn.execute("SELECT COUNT(*) FROM trackers").fetchone()[0]
    
    col1.metric("Total Equipment", total_eq)
    col2.metric("Currently Rented", rented_eq)
    col3.metric("Active Trackers", trackers_count)
    
    st.markdown("---")
    st.markdown("### 🗺️ GPS Tracking & 25km Geofence Perimeter")
    
    m = folium.Map(location=[9.0107, 38.7612], zoom_start=11)
    
    folium.Circle(
        location=[9.0107, 38.7612],
        radius=25000,
        color='blue',
        fill=True,
        fill_opacity=0.1,
        tooltip="Addis Ababa 25km Authorized Zone"
    ).add_to(m)
    
    trackers = conn.execute("SELECT * FROM trackers").fetchall()
    
    for trk in trackers:
        if trk['last_lat'] and trk['last_lng']:
            inside, dist = is_within_geofence(trk['last_lat'], trk['last_lng'])
            status_color = "green" if inside else "red"
            status_text = "Inside Zone (Safe)" if inside else f"OUT OF ZONE! ({round(dist, 2)} km away)"
            
            popup_html = f"""
            <b>Tracker ID:</b> {trk['tracker_id']}<br>
            <b>IMEI:</b> {trk['imei']}<br>
            <b>Battery:</b> {trk['battery_level']}%<br>
            <b>Status:</b> <span style="color:{status_color};"><b>{status_text}</b></span>
            """
            
            folium.Marker(
                location=[trk['last_lat'], trk['last_lng']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color="red" if not inside else "cadetblue", icon="camera", prefix="fa")
            ).add_to(m)
            
    st_folium(m, width=1200, height=500)

elif choice == "Equipment Inventory":
    st.subheader("📦 Studio Equipment Inventory")
    
    df_eq = pd.read_sql("SELECT * FROM equipment", conn)
    st.dataframe(df_eq, use_container_width=True)
    
    with st.expander("➕ Add New Equipment"):
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
                    conn.execute("INSERT INTO equipment VALUES (?,?,?,?,?,?,0,'Available')", 
                                 (eq_id, name, category, model, serial, tracker_id if tracker_id else None))
                    conn.commit()
                    st.success("Equipment added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

elif choice == "Check-Out / Check-In Inspection":
    st.subheader("🔄 Gear Check-Out & AI Damage Inspection Check-In")
    
    tab1, tab2, tab3 = st.tabs(["Check-Out Gear", "Check-In & Inspect Damage", "Active Rental Client Registry"])
    
    with tab1:
        st.markdown("### 📋 Client Registration & Check-Out (Pre-Rental Baseline)")
        available_eq = conn.execute("SELECT equipment_id, name FROM equipment WHERE status='Available'").fetchall()
        eq_options = {item['name']: item['equipment_id'] for item in available_eq}
        
        selected_name = st.selectbox("Select Equipment to Rent Out", list(eq_options.keys()) if eq_options else ["No equipment available"])
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            client_name = st.text_input("Client / Crew Full Name")
            client_phone = st.text_input("Phone Number (e.g., +251 9...)", value="+251 ")
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
            st.success(f"✅ {selected_name} checked out to {client_name} ({client_phone})!")
            st.rerun()
            
    with tab2:
        st.markdown("### Equipment Return & Visual Damage Inspection")
        active_rentals = conn.execute("""
            SELECT i.inspection_id, e.name, i.client_name, i.client_phone, i.baseline_photo 
            FROM inspections i JOIN equipment e ON i.equipment_id = e.equipment_id 
            WHERE i.status='Active' OR i.status='Pending'
        """).fetchall()
        
        rental_options = {f"{r['name']} — Client: {r['client_name']} ({r['client_phone']})": r for r in active_rentals}
        
        selected_key = st.selectbox("Select Return Item", list(rental_options.keys()) if rental_options else ["No active rentals found"])
        
        uploaded_file = st.file_uploader("Upload Photo of Returned Gear (Post-Rental)", type=["jpg", "jpeg", "png"], key="return")
        
        if st.button("Run AI Inspection & Complete Return") and rental_options and uploaded_file:
            rental_info = rental_options[selected_key]
            insp_id = rental_info['inspection_id']
            baseline_img_path = rental_info['baseline_photo']
            
            os.makedirs("uploads", exist_ok=True)
            return_img_path = f"uploads/return_{insp_id}.jpg"
            with open(return_img_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            if baseline_img_path and os.path.exists(baseline_img_path):
                highlighted_img, damage_score = compare_photos(baseline_img_path, return_img_path)
            else:
                st.info("No pre-rental baseline image was uploaded during check-out. Comparing return photo against self.")
                highlighted_img, damage_score = compare_photos(return_img_path, return_img_path)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.image(uploaded_file, caption="Returned Gear Photo", use_container_width=True)
            with col_b:
                if highlighted_img:
                    st.image(highlighted_img, caption=f"AI Diff Analysis (Damage Score: {damage_score}%)", use_container_width=True)
                
            if damage_score > 3.0:
                st.warning(f"⚠️ Damage Detected! Score: {damage_score}% difference from clean baseline.")
            else:
                st.success(f"✅ Gear returned in clean condition. Damage Score: {damage_score}%")
                
            conn.execute("UPDATE inspections SET check_in_time=?, return_photo=?, damage_score=?, status=? WHERE inspection_id=?",
                         (datetime.now(), return_img_path, damage_score, 'Completed', insp_id))
            
            eq_id_row = conn.execute("SELECT equipment_id FROM inspections WHERE inspection_id=?", (insp_id,)).fetchone()
            if eq_id_row:
                conn.execute("UPDATE equipment SET status='Available' WHERE equipment_id=?", (eq_id_row['equipment_id'],))
            conn.commit()
            st.success("Inspection recorded and equipment returned to inventory status!")

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

elif choice == "Client Mobile GPS Check":
    st.subheader("📱 Client Mobile Phone GPS Verification")
    st.markdown("Use this page when a client or crew member is picking up gear on-site using their smartphone. This captures their phone's live GPS coordinates to verify they are within the 25km Addis Ababa zone.")

    geo_html = """
    <div style="padding: 20px; background-color: #1e1e1e; border-radius: 10px; color: white; text-align: center;">
        <h3>📍 Smartphone GPS Locator</h3>
        <p>Click the button below to allow location access from your phone:</p>
        <button onclick="getLocation()" style="background-color: #ff4b4b; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">Get My Phone Location</button>
        <p id="demo" style="margin-top: 15px; font-family: monospace;"></p>
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
        x.innerHTML = "Latitude: " + position.coords.latitude + "<br>Longitude: " + position.coords.longitude;
    }
    function showError(error) {
        switch(error.code) {
            case error.PERMISSION_DENIED:
                x.innerHTML = "User denied the request for Geolocation.";
                break;
            case error.POSITION_UNAVAILABLE:
                x.innerHTML = "Location information is unavailable.";
                break;
            case error.TIMEOUT:
                x.innerHTML = "The request to get user location timed out.";
                break;
            case error.UNKNOWN_ERROR:
                x.innerHTML = "An unknown error occurred.";
                break;
        }
    }
    </script>
    """
    
    components.html(geo_html, height=250)
    
    st.markdown("---")
    st.markdown("### Manual Coordinate Verification Test")
    
    with st.form("client_geo_form"):
        c_lat = st.number_input("Latitude", value=9.0107, format="%.4f")
        c_lng = st.number_input("Longitude", value=38.7612, format="%.4f")
        client_name_input = st.text_input("Client / Crew Name")
        verify_btn = st.form_submit_button("Verify Geofence Status")
        
        if verify_btn:
            inside, dist = is_within_geofence(c_lat, c_lng)
            if inside:
                st.success(f"✅ Verified! {client_name_input} is **Inside Zone (Safe)**. Distance from Addis Ababa center: {round(dist, 2)} km.")
            else:
                st.error(f"🚨 ALERT! {client_name_input} is **OUT OF ZONE!** They are {round(dist, 2)} km away (exceeds 25km limit).")

conn.close()