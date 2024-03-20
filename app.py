from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import login_user, login_required, logout_user, LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'NekaNovaLozinka123'

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_size': 20}  # Adjust pool size as needed

# Initialize SQLAlchemy
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Configure the login view
login_manager.login_view = 'login'

ADMIN_USERNAME = 'jsakoman'
ADMIN_PASSWORD = 'NekaNovaLozinka123'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define the User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)

# Worker model
class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Position model
class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Subscription model
class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Define indexes
db.Index('idx_user_id_worker', Worker.user_id)
db.Index('idx_user_id_position', Position.user_id)
db.Index('idx_user_id_subscription', Subscription.user_id)

# User schema for serialization/deserialization
class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username', 'password')

user_schema = UserSchema()
users_schema = UserSchema(many=True)

# Worker schema
class WorkerSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'user_id')

worker_schema = WorkerSchema()
workers_schema = WorkerSchema(many=True)

# Position schema
class PositionSchema(ma.Schema):
    class Meta:
        fields = ('id', 'title', 'user_id')

position_schema = PositionSchema()
positions_schema = PositionSchema(many=True)


# Subscription schema
class SubscriptionSchema(ma.Schema):
    class Meta:
        fields = ('id', 'status', 'start_date', 'end_date', 'user_id')

subscription_schema = SubscriptionSchema()
subscriptions_schema = SubscriptionSchema(many=True)


# Configure session management without Redis (uses secure cookies)
app.config['SESSION_TYPE'] = 'filesystem'  # Use 'filesystem' for server-side session storage


# Admin login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Authentication successful, redirect to admin dashboard
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')
    return render_template('admin_login.html')

# Admin dashboard route
@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if the user is logged in as admin
    if 'admin_logged_in' not in session:
        flash('You are not authorized to access this page.', 'error')
        return redirect(url_for('admin_login'))

    # Fetch all users or perform other admin tasks
    all_users = User.query.all()
    return render_template('admin_dashboard.html', users=all_users)

# Admin logout route
@app.route('/admin/logout')
def admin_logout():
    # Logout the admin and redirect to login page
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# Route for creating a new user
@app.route('/users', methods=['POST'])
def create_user():
    username = request.json['username']
    password = request.json['password']
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return user_schema.jsonify(new_user)

# Route for retrieving all users
@app.route('/users', methods=['GET'])
def get_users():
    all_users = User.query.all()
    result = users_schema.dump(all_users)
    return jsonify(result)

# Route for retrieving a single user by ID
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    return user_schema.jsonify(user)

# Route for updating a user
@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get(user_id)
    username = request.json['username']
    password = request.json['password']
    user.username = username
    user.password = password
    db.session.commit()
    return user_schema.jsonify(user)

# Route for deleting a user
@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    return user_schema.jsonify(user)


# Route for creating a new subscription
@app.route('/subscriptions', methods=['POST'])
def create_subscription():
    status = request.json['status']
    end_date = request.json['end_date']
    user_id = request.json['user_id']
    new_subscription = Subscription(status=status, end_date=end_date, user_id=user_id)
    db.session.add(new_subscription)
    db.session.commit()
    return subscription_schema.jsonify(new_subscription)

# Route for retrieving all subscriptions
@app.route('/subscriptions', methods=['GET'])
def get_subscriptions():
    all_subscriptions = Subscription.query.all()
    result = subscriptions_schema.dump(all_subscriptions)
    return jsonify(result)


# CRUD FOR PRIVATE USER DATABASE WOTH TABLES

# Route for rendering the workers template
@app.route('/workers', methods=['GET'])
def get_workers():
    all_workers = Worker.query.all()
    return render_template('workers.html', workers=all_workers)

# Route for creating a new worker (GET)
@app.route('/workers/create', methods=['GET'])
def create_worker_form():
    return render_template('create_worker.html')

# Route for creating a new worker (POST)
@app.route('/workers', methods=['POST'])
def create_worker():
    name = request.form['name']
    user_id = request.form['user_id']
    new_worker = Worker(name=name, user_id=user_id)
    db.session.add(new_worker)
    db.session.commit()
    flash('Worker created successfully', 'success')
    return redirect(url_for('get_workers'))


# Route for updating a worker
@app.route('/workers/<int:worker_id>/update', methods=['GET'])
def update_worker_form(worker_id):
    worker = Worker.query.get(worker_id)
    return render_template('update_worker.html', worker=worker)

@app.route('/workers/<int:worker_id>/update', methods=['POST'])
def update_worker(worker_id):
    worker = Worker.query.get(worker_id)
    worker.name = request.form['name']
    db.session.commit()
    flash('Worker updated successfully', 'success')
    return redirect(url_for('get_workers'))

# Route for deleting a worker
@app.route('/workers/<int:worker_id>/delete', methods=['POST'])
def delete_worker(worker_id):
    worker = Worker.query.get(worker_id)
    db.session.delete(worker)
    db.session.commit()
    flash('Worker deleted successfully', 'success')
    return redirect(url_for('get_workers'))

# Route for rendering the positions template
@app.route('/positions', methods=['GET'])
def get_positions():
    all_positions = Position.query.all()
    return render_template('positions.html', positions=all_positions)

# Route for creating a new position (GET)
@app.route('/positions/create', methods=['GET'])
def create_position_form():
    return render_template('create_position.html')

# Route for creating a new position (POST)
@app.route('/positions', methods=['POST'])
def create_position():
    title = request.form['title']
    user_id = request.form['user_id']
    new_position = Position(title=title, user_id=user_id)
    db.session.add(new_position)
    db.session.commit()
    flash('Position created successfully', 'success')
    return redirect(url_for('get_positions'))

# Route for updating a position (GET)
@app.route('/positions/<int:position_id>/update', methods=['GET'])
def update_position_form(position_id):
    position = Position.query.get(position_id)
    return render_template('update_position.html', position=position)

# Route for updating a position (POST)
@app.route('/positions/<int:position_id>/update', methods=['POST'])
def update_position(position_id):
    position = Position.query.get(position_id)
    position.title = request.form['title']
    db.session.commit()
    flash('Position updated successfully', 'success')
    return redirect(url_for('get_positions'))

# Route for deleting a position
@app.route('/positions/<int:position_id>/delete', methods=['POST'])
def delete_position(position_id):
    position = Position.query.get(position_id)
    db.session.delete(position)
    db.session.commit()
    flash('Position deleted successfully', 'success')
    return redirect(url_for('get_positions'))





# Route for registering a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route for logging in
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('index'))  # Redirect to 'index' endpoint
            else:
                flash('Invalid username or password.', 'error')
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    current_user_subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    current_user_workers = Worker.query.filter_by(user_id=current_user.id).all()
    current_user_positions = Position.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html',
                           subscriptions=current_user_subscriptions,
                           workers=current_user_workers,
                           positions=current_user_positions)


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))




@app.before_request
def clear_cookies():
    g.user = None
    if 'session_id' in request.cookies:
        # Clear the session cookie
        response = redirect(request.path)
        response.set_cookie('session_id', '', expires=0)
        return response


# Create database tables within the application context

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(host='0.0.0.0', port=5005)
