from flask import Flask, render_template
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'  # Change this to your MySQL host
app.config['MYSQL_USER'] = 'your_username'  # Change this to your MySQL username
app.config['MYSQL_PASSWORD'] = 'your_password'  # Change this to your MySQL password
app.config['MYSQL_DB'] = 'your_database_name'  # Change this to your MySQL database name

mysql = MySQL(app)

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM users")
    users = cur.fetchall()
    cur.close()
    return render_template('index.html', users=users)

if __name__ == "__main__":
    app.run(debug=True)
