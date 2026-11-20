import sqlite3

def get_conn():
    conn = sqlite3.connect("bus.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS routes (
            route_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            fare REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS buses (
            bus_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT NOT NULL,
            route_id INTEGER NOT NULL REFERENCES routes(route_id),
            travel_date TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            total_seats INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS passengers (
            passenger_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL REFERENCES buses(bus_id),
            passenger_id INTEGER NOT NULL REFERENCES passengers(passenger_id),
            seat_number INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'BOOKED',
            booked_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_seat
            ON bookings(bus_id, seat_number) WHERE status = 'BOOKED';
        """)

def add_sample_data():
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0] > 0:
            return  # already added
        conn.executemany(
            "INSERT INTO routes (source, destination, fare) VALUES (?, ?, ?)",
            [("Mysuru", "Bengaluru", 350), ("Mysuru", "Chennai", 800), ("Bengaluru", "Hyderabad", 900)],
        )
        conn.executemany(
            "INSERT INTO buses (bus_number, route_id, travel_date, departure_time, total_seats) VALUES (?, ?, ?, ?, ?)",
            [
                ("KA-09-1001", 1, "2026-11-25", "08:00", 40),
                ("KA-09-1002", 1, "2026-11-25", "14:30", 40),
                ("KA-09-2001", 2, "2026-11-26", "21:00", 30),
                ("KA-01-3001", 3, "2026-11-27", "20:00", 36),
            ],
        )

def search_buses(source, destination, travel_date):
    with get_conn() as conn:
        return conn.execute("""
            SELECT b.bus_id, b.bus_number, b.departure_time, r.fare, b.total_seats,
                   b.total_seats - (SELECT COUNT(*) FROM bookings k
                                    WHERE k.bus_id = b.bus_id AND k.status = 'BOOKED') AS seats_left
            FROM buses b JOIN routes r ON b.route_id = r.route_id
            WHERE r.source = ? AND r.destination = ? AND b.travel_date = ?
        """, (source, destination, travel_date)).fetchall()

def book_seat(bus_id, name, phone, seat_number):
    with get_conn() as conn:
        bus = conn.execute("SELECT total_seats FROM buses WHERE bus_id = ?", (bus_id,)).fetchone()
        if bus is None:
            return "Bus not found."
        if not 1 <= seat_number <= bus[0]:
            return f"Seat must be between 1 and {bus[0]}."
        taken = conn.execute(
            "SELECT 1 FROM bookings WHERE bus_id = ? AND seat_number = ? AND status = 'BOOKED'",
            (bus_id, seat_number)).fetchone()
        if taken:
            return f"Seat {seat_number} is already taken."
        cur = conn.execute("INSERT INTO passengers (name, phone) VALUES (?, ?)", (name, phone))
        booking = conn.execute(
            "INSERT INTO bookings (bus_id, passenger_id, seat_number) VALUES (?, ?, ?)",
            (bus_id, cur.lastrowid, seat_number))
        return f"Booked seat {seat_number} for {name}. Booking ID: {booking.lastrowid}"

def cancel_booking(booking_id):
    with get_conn() as conn:
        booking = conn.execute(
            "SELECT status, seat_number FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
        if booking is None:
            return "Booking not found."
        if booking[0] == "CANCELLED":
            return "This booking is already cancelled."
        conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = ?", (booking_id,))
        return f"Booking {booking_id} cancelled. Seat {booking[1]} is free again."

if __name__ == "__main__":
    create_tables()
    add_sample_data()
    print(book_seat(1, "Lalkrishna", "9999999999", 5))   # books seat 5
    print(book_seat(1, "Test User", "8888888888", 5))    # rejected, taken
    print(cancel_booking(1))                             # cancels it
    print(cancel_booking(1))                             # already cancelled
    print(book_seat(1, "Test User", "8888888888", 5))    # works, seat is free