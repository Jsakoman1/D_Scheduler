from flask import Flask, session, redirect, url_for, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # SQLite database for demonstration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role_id = db.Column(db.Integer, nullable=False)  # Define role_id column
    workers = db.relationship('Worker', backref='user', lazy=True, cascade="all, delete-orphan")
    positions = db.relationship('Position', backref='user', lazy=True, cascade="all, delete-orphan")

class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if 'worker_id' in session:
        return redirect(url_for('index_employee'))

    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    workers = Worker.query.filter_by(user_id=user_id).all()
    positions = Position.query.filter_by(user_id=user_id).all()

    return render_template('index.html', user=user, workers=workers, positions=positions)

@app.route('/index_employee')
@login_required
def index_employee():
    if 'worker_id' not in session:
        return redirect(url_for('login_employee'))

    worker_id = session['worker_id']
    worker = Worker.query.get(worker_id)
    return render_template('index_employee.html', worker=worker)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Log out any current user
    session.pop('user_id', None)
    logout_user()

    if request.method == 'POST':
        login_type = request.form['login_type']
        if login_type == 'employer':
            return redirect(url_for('login_employer'))
        elif login_type == 'employee':
            return redirect(url_for('login_employee'))
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

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    session.pop('user_id', None)  # Clear user_id from session
    if request.method == 'POST':
        # Check if form submitted to delete a user
        user_id = request.form.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            db.session.delete(user)
            db.session.commit()
            return redirect(url_for('admin'))

    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/users')
@login_required
def display_users():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/login_employer', methods=['GET', 'POST'])
def login_employer():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password, role_id=1).first()
        if user:
            session['user_id'] = user.id
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login_employer.html')


@app.route('/login_employee', methods=['GET', 'POST'])
def login_employee():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        worker = Worker.query.filter_by(email=email, password=password).first()
        if worker:
            session['worker_id'] = worker.id
            return redirect(url_for('index'))  # Redirect to appropriate page after login
        else:
            flash('Invalid email or password', 'error')
    return render_template('login_employee.html')


@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    # Delete the user from the database
    db.session.delete(user)
    db.session.commit()
    # Redirect to the admin page after deletion
    return redirect(url_for('admin'))

@app.route('/add_worker', methods=['GET', 'POST'])
@login_required
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_id = session['user_id']  # Get the user ID from the session
        new_worker = Worker(name=name, email=email, password=password, user_id=user_id)
        db.session.add(new_worker)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_worker.html')


@app.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
@login_required
def edit_worker(worker_id):
    worker = Worker.query.get(worker_id)
    if request.method == 'POST':
        # Update the worker with the form data
        worker.name = request.form['name']
        worker.email = request.form['email']
        worker.password = request.form['password']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_worker.html', worker=worker)


@app.route('/remove_worker/<int:worker_id>', methods=['POST'])
@login_required
def remove_worker(worker_id):
    worker = Worker.query.get(worker_id)
    db.session.delete(worker)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_position', methods=['GET', 'POST'])
@login_required
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
@login_required
def edit_position(position_id):
    position = Position.query.get_or_404(position_id)
    if request.method == 'POST':
        position.name = request.form['name']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_position.html', position=position)

@app.route('/remove_position/<int:position_id>', methods=['POST'])
@login_required
def remove_position(position_id):
    position = Position.query.get_or_404(position_id)
    db.session.delete(position)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
