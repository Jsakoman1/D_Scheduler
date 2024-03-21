from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure key



SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="sakoman",
    password="NekaNovaLozinka123",
    hostname="sakoman.mysql.pythonanywhere-services.com",
    databasename="sakoman$D_Scheduler",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy database instance
db = SQLAlchemy(app)



# Define User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'))
    subscription = db.relationship('Subscription', back_populates='users')

# Define Subscription model
class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)  # 'active' or 'inactive'
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)

    users = db.relationship('User', back_populates='subscription')

# Function to create database tables
def create_tables():
    with app.app_context():
        db.create_all()

# Call the function to create tables
create_tables()


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Custom decorators for role-based access control
def employer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'employer':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def employee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'employee':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# Home route
@app.route('/')
def index():
    if current_user.is_authenticated:
        username = current_user.username
        return render_template('index.html', username=username)
    else:
        return render_template('index.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'employer':
                return redirect(url_for('employer_dashboard'))
            elif user.role == 'employee':
                return redirect(url_for('employee_dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Subscribe route
@app.route('/subscribe')
@login_required
def subscribe():
    if not current_user.subscription:
        new_subscription = Subscription(status='active')
        db.session.add(new_subscription)
        current_user.subscription = new_subscription
        db.session.commit()
        flash('You have subscribed successfully!', 'success')
    else:
        flash('You are already subscribed', 'info')
    return redirect(url_for('profile'))

# Unsubscribe route
@app.route('/unsubscribe')
@login_required
def unsubscribe():
    if current_user.subscription:
        db.session.delete(current_user.subscription)
        current_user.subscription = None
        db.session.commit()
        flash('You have unsubscribed successfully!', 'success')
    else:
        flash('You are not subscribed', 'info')
    return redirect(url_for('profile'))

# User profile route
@app.route('/profile')
@login_required
def profile():
    username = current_user.username
    email = current_user.email
    role = current_user.role
    subscription_status = current_user.subscription.status if current_user.subscription else None
    subscription_start_date = current_user.subscription.start_date.strftime('%Y-%m-%d') if current_user.subscription else None
    subscription_end_date = current_user.subscription.end_date.strftime('%Y-%m-%d') if current_user.subscription else None

    return render_template('profile.html', username=username, email=email, role=role, subscription_status=subscription_status, subscription_start_date=subscription_start_date, subscription_end_date=subscription_end_date)

# Admin dashboard route
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin.html', users=users)

# Employer dashboard route
@app.route('/employer')
@login_required
@employer_required
def employer_dashboard():
    return render_template('employer.html', username=current_user.username)

# Employee dashboard route
@app.route('/employee')
@login_required
@employee_required
def employee_dashboard():
    return render_template('employee.html', username=current_user.username)

if __name__ == "__main__":

    app.run(host='0.0.0.0', port=5005)