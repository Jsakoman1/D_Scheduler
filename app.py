from flask import Flask, session, redirect, url_for, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # SQLite database for demonstration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    workers = db.relationship('Worker', backref='user', lazy=True)
    positions = db.relationship('Position', backref='user', lazy=True)

class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    workers = Worker.query.filter_by(user_id=user_id).all()
    positions = Position.query.filter_by(user_id=user_id).all()

    return render_template('index.html', user=user, workers=workers, positions=positions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password, role_id=1)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin')
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/users')
def display_users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/add_worker', methods=['GET', 'POST'])
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        user_id = session['user_id']  # Get the user ID from the session
        new_worker = Worker(name=name, user_id=user_id)
        db.session.add(new_worker)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_worker.html')


@app.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
def edit_worker(worker_id):
    worker = Worker.query.get(worker_id)
    if request.method == 'POST':
        # Update the worker with the form data
        worker.name = request.form['name']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_worker.html', worker=worker)

@app.route('/remove_worker/<int:worker_id>', methods=['POST'])
def remove_worker(worker_id):
    worker = Worker.query.get(worker_id)
    db.session.delete(worker)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_position', methods=['GET', 'POST'])
def add_position():
    if request.method == 'POST':
        name = request.form['name']
        user_id = session['user_id']  # Get the user ID from the session
        new_position = Position(name=name, user_id=user_id)
        db.session.add(new_position)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_position.html')

@app.route('/edit_position/<int:position_id>', methods=['GET', 'POST'])
def edit_position(position_id):
    position = Position.query.get_or_404(position_id)
    if request.method == 'POST':
        position.name = request.form['name']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_position.html', position=position)

@app.route('/remove_position/<int:position_id>', methods=['POST'])
def remove_position(position_id):
    position = Position.query.get_or_404(position_id)
    db.session.delete(position)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
