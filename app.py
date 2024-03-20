from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import bcrypt

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure secret key

mysql = MySQL(app)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'sakoman.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER'] = 'sakoman'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'sakoman$D_Scheduler'

@app.route('/')
def index():
    if 'username' in session:
        # Check user's role and render different templates accordingly
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        role = request.form['role']  # You can have a select input for role
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password, role_id) VALUES (%s, %s, %s)", (username, hashed_password, role))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid username/password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/workers')
def manage_workers():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch workers associated with the logged-in employer
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM workers WHERE employer_id = (SELECT id FROM users WHERE username = %s)", [session['username']])
    workers = cur.fetchall()
    cur.close()
    return render_template('manage_workers.html', workers=workers)

@app.route('/positions')
def manage_positions():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch positions associated with the logged-in employer
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM positions WHERE employer_id = (SELECT id FROM users WHERE username = %s)", [session['username']])
    positions = cur.fetchall()
    cur.close()
    return render_template('manage_positions.html', positions=positions)

if __name__ == "__main__":
    app.run(debug=True)
