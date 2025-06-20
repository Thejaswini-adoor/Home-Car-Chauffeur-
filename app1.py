from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for session management
DATABASE = 'chauffeurs.db'

def get_db():
    """Establish a connection to the database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the chauffeurs.db database and create the drivers table."""
    with get_db() as db:
        db.execute('''
        CREATE TABLE IF NOT EXISTS chauffeurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            DL TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        ''')
         # Create status table
        db.execute('''
        CREATE TABLE IF NOT EXISTS status (
            status_id INTEGER PRIMARY KEY AUTOINCREMENT,
            status_def TEXT NOT NULL CHECK(status_def IN ('available', 'unavailable')),
            id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (id) REFERENCES chauffeurs(id)
        )
        ''')
        # Create rides table (for demonstration purposes)
        db.execute(''' CREATE TABLE IF NOT EXISTS rides (
            ride_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pickup TEXT NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'rejected')),
            driver_id INTEGER,
            FOREIGN KEY (driver_id) REFERENCES chauffeurs(id))
            ''')



@app.route('/')
def home():
    """Render the main home page."""
    return render_template('home.html')

@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle driver registration."""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        DL = request.form['DL']
        password = request.form['password']

        with get_db() as db:
            try:
                db.execute(
                    'INSERT INTO chauffeurs (name, email, phone, address, DL, password) VALUES (?, ?, ?, ?, ?, ?)',
                    (name, email, phone, address, DL, password)
                )
                db.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError as e:
                return f"Error: {e}"  # Handle unique constraint errors
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle driver login."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with get_db() as db:
            driver = db.execute('SELECT * FROM chauffeurs WHERE email = ? AND password = ?', (email, password)).fetchone()
            if driver:
                session['driver_id'] = driver['id']
                session['driver_name'] = driver['name']
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('signup'))
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    """Driver dashboard."""
    if 'driver_id' not in session:
        return redirect(url_for('login'))

    driver_id = session['driver_id']
    with get_db() as db:
        # Set driver status to 'unavailable' initially if not set
        db.execute('INSERT OR IGNORE INTO status (status_def, id) VALUES (?, ?)', ('unavailable', driver_id))
        db.commit()

    return render_template('dashboard.html', driver_name=session['driver_name'])

@app.route('/go_online')
def go_online():
    """Set driver status to 'available' and show rides."""
    if 'driver_id' not in session:
        return redirect(url_for('login'))

    driver_id = session['driver_id']
    with get_db() as db:
        # Update driver status to 'available'
        db.execute('UPDATE status SET status_def = ? WHERE id = ?', ('available', driver_id))
        db.commit()

        # Fetch pending rides
        rides = db.execute('SELECT * FROM rides WHERE status = ?', ('pending',)).fetchall()

    return render_template('rides.html', rides=rides)


@app.route('/ride_action/<int:ride_id>/<action>')
def ride_action(ride_id, action):
    """Handle ride acceptance or rejection."""
    if 'driver_id' not in session:
        return redirect(url_for('login'))

    if action not in ['accept', 'reject']:
        return "Invalid action.", 400

    driver_id = session['driver_id']
    with get_db() as db:
        if action == 'accept':
            db.execute('UPDATE rides SET status = ?, driver_id = ? WHERE ride_id = ?', ('accepted', driver_id, ride_id))
        elif action == 'reject':
            db.execute('UPDATE rides SET status = ? WHERE ride_id = ?', ('rejected', ride_id))
        db.commit()

    return redirect(url_for('go_online'))

@app.route('/logout')
def logout():
    """Log out the driver."""
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()  # Ensure the database is initialized
    app.run(debug=True)

