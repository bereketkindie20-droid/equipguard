import sqlite3

def get_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Equipment Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        equipment_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        model TEXT,
        serial_number TEXT,
        tracker_id TEXT,
        damage_score REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Available'
    )
    """)
    
    # Trackers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trackers (
        tracker_id TEXT PRIMARY KEY,
        imei TEXT,
        last_lat REAL,
        last_lng REAL,
        battery_level INTEGER,
        last_updated DATETIME
    )
    """)
    
    # Inspections & Rental Records Table (Updated with Client Details)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspections (
        inspection_id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id TEXT,
        client_name TEXT NOT NULL,
        client_phone TEXT,
        client_digital_id TEXT,
        check_out_time DATETIME,
        check_in_time DATETIME,
        baseline_photo TEXT,
        return_photo TEXT,
        damage_score REAL,
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id)
    )
    """)
    
    # Insert default test equipment if empty
    cursor.execute("SELECT COUNT(*) FROM equipment")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO equipment VALUES ('EQ-CAM-01', 'Sony FX3 Camera', 'Camera', 'FX3', 'SN-998822', 'TRK-001', 0.0, 'Available')")
        cursor.execute("INSERT INTO equipment VALUES ('EQ-LNS-01', 'Sony 24-70mm G-Master', 'Lens', 'GM I', 'SN-112233', 'TRK-002', 0.0, 'Available')")
        cursor.execute("INSERT INTO trackers VALUES ('TRK-001', '864201049281001', 9.0107, 38.7612, 95, datetime('now'))")
        cursor.execute("INSERT INTO trackers VALUES ('TRK-002', '864201049281002', 9.0500, 38.7200, 88, datetime('now'))")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()