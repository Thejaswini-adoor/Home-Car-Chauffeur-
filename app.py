from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'chauffeurs.db'

def get_db():
    """Establish a connection to the database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the chauffeurs.db database and create the tables."""
    with get_db() as db:
        # Create User table
        db.execute('''CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )''')

        # Create Booking table
        db.execute('''CREATE TABLE IF NOT EXISTS Booking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            pickup_location TEXT NOT NULL,
            dropoff_location TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            FOREIGN KEY (user_id) REFERENCES User (id)
        )''')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        with get_db() as db:
            user = db.execute('SELECT * FROM User WHERE email = ?', (email,)).fetchone()
            if user:
                flash('Email already registered', 'danger')
                return redirect(url_for('register'))

            try:
                db.execute('INSERT INTO User (username, email, password) VALUES (?, ?, ?)', 
                           (username, email, password))
                db.commit()
                flash('Registration successful. Please login.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError as e:
                flash(f"Error: {e}", 'danger')
                return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with get_db() as db:
            user = db.execute('SELECT * FROM User WHERE email = ?', (email,)).fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Login successful.', 'success')
                return redirect(url_for('book'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        flash('Please login to book a chauffeur.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']
        pickup_location = request.form['pickup_location']
        dropoff_location = request.form['dropoff_location']
        vehicle_type = request.form['vehicle_type']

        if not date or not time or not pickup_location or not dropoff_location or not vehicle_type:
            flash('All fields are required.', 'danger')
            return redirect(url_for('book'))

        with get_db() as db:
            user = db.execute('SELECT * FROM User WHERE id = ?', (session['user_id'],)).fetchone()
            if not user:
                flash("User not found", 'danger')
                return redirect(url_for('login'))

            try:
                db.execute('INSERT INTO Booking (user_id, date, time, pickup_location, dropoff_location, vehicle_type, status) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                           (session['user_id'], date, time, pickup_location, dropoff_location, vehicle_type, 'waiting'))
                db.commit()
                flash('Booking successful. Waiting for driver confirmation.', 'info')
                return redirect(url_for('wait_for_driver'))
            except sqlite3.IntegrityError as e:
                flash(f"Error: {e}", 'danger')
            except Exception as e:
                flash(f"Unexpected error: {e}", 'danger')
                return redirect(url_for('book'))

    return render_template('book.html')

@app.route('/wait_for_driver')
def wait_for_driver():
    if 'user_id' not in session:
        flash('Please login to view your booking status.', 'warning')
        return redirect(url_for('login'))

    with get_db() as db:
        booking = db.execute('SELECT * FROM Booking WHERE user_id = ? AND status = "waiting"', (session['user_id'],)).fetchone()
        if not booking:
            flash('No active booking found.', 'warning')
            return redirect(url_for('book'))

    return render_template('wait_for_driver.html', booking=booking)

if __name__ == '__main__':
    init_db()  # Initialize database if not already initialized
    app.run(debug=True)
