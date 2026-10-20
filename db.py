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
            category TEXT,
            model TEXT,
            serial_number TEXT,
            tracker_id TEXT,
            rental_price REAL,
            status TEXT DEFAULT 'Available',
            current_lat REAL DEFAULT 9.011556,
            current_lng REAL DEFAULT 38.781258,
            last_location_update DATETIME
        )
    """)
    
    # Location Logs Table (Tracks journey from Fotogenic Studio to Location X)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT,
            latitude REAL,
            longitude REAL,
            updated_at DATETIME,
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
    """)

    # Inspections Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            inspection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT,
            client_name TEXT,
            client_phone TEXT,
            client_digital_id TEXT,
            check_out_time DATETIME,
            check_in_time DATETIME,
            baseline_photo TEXT,
            return_photo TEXT,
            damage_score REAL,
            status TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
    """)

    # Populate initial sample gear for Fotogenic Studio if empty
    cursor.execute("SELECT COUNT(*) FROM equipment")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO equipment VALUES ('EQ-CAM-01', 'Sony A7IV Camera Kit', 'Camera', 'A7IV', 'SN987654', 'TRK-001', 50.0, 'Available', 9.011556, 38.781258, CURRENT_TIMESTAMP)")
        cursor.execute("INSERT INTO equipment VALUES ('EQ-LNS-01', 'Sigma 24-70mm f/2.8 Lens', 'Lens', 'Art Series', 'SN123456', 'TRK-002', 25.0, 'Available', 9.011556, 38.781258, CURRENT_TIMESTAMP)")
        cursor.execute("INSERT INTO equipment VALUES ('EQ-LGT-01', 'Aputure 300d II Light', 'Light', '300d II', 'SN456789', 'TRK-003', 40.0, 'Available', 9.011556, 38.781258, CURRENT_TIMESTAMP)")

    conn.commit()
    conn.close()
