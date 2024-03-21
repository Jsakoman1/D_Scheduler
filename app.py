from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import relationship


from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure key

# Define SQLite database path
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'app.db')

# Configure SQLite database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy database instance
db = SQLAlchemy(app)

# Define User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role


class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    function = db.Column(db.String(100), nullable=False)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employer = relationship('User', backref=db.backref('workers', lazy=True))

    def __init__(self, name, function, employer_id):
        self.name = name
        self.function = function
        self.employer_id = employer_id




# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



#ADMIN SECTION
@app.route('/admin')
@login_required
def admin():
    if current_user.role == 'admin':
        users = User.query.all()  # Query all users
        return render_template('admin.html', users=users)  # Pass users to the template
    else:
        return redirect(url_for('index'))

@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    # Check if the current user is an admin
    if current_user.role != 'admin':
        flash('You are not authorized to delete users.', 'error')
        return redirect(url_for('admin'))

    # Get the user to be deleted from the database
    user_to_delete = User.query.get(user_id)

    # Check if the user exists
    if not user_to_delete:
        flash('User not found.', 'error')
        return redirect(url_for('admin'))

    # Delete the user from the database
    db.session.delete(user_to_delete)
    db.session.commit()

    flash(f'User {user_to_delete.username} has been successfully deleted.', 'success')
    return redirect(url_for('admin'))


#EMPLOYERS SECTION

@app.route('/employer_dashboard')
@login_required
def employer_dashboard():
    if current_user.role == 'employer':
        return render_template('employer.html')
    else:
        flash('You are not authorized to view this page.', 'error')
        return redirect(url_for('index'))
    
# CRUD operations for workers

# Create a new worker
@app.route('/add_worker', methods=['GET', 'POST'])
@login_required
def add_worker():
    if current_user.role == 'employer':
        if request.method == 'POST':
            name = request.form['name']
            function = request.form['function']
            employer_id = current_user.id

            new_worker = Worker(name=name, function=function, employer_id=employer_id)
            db.session.add(new_worker)
            db.session.commit()
            flash('Worker added successfully.', 'success')
            return redirect(url_for('view_workers'))
        return render_template('add_worker.html')
    else:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('index'))

# View all workers
@app.route('/view_workers')
@login_required
def view_workers():
    if current_user.role == 'employer':
        workers = Worker.query.filter_by(employer_id=current_user.id).all()
        return render_template('workers.html', workers=workers)
    else:
        flash('You are not authorized to view this page.', 'error')
        return redirect(url_for('index'))

# Edit a worker
@app.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
@login_required
def edit_worker(worker_id):
    if current_user.role == 'employer':
        worker = Worker.query.get(worker_id)
        if not worker:
            flash('Worker not found.', 'error')
            return redirect(url_for('view_workers'))

        if request.method == 'POST':
            worker.name = request.form['name']
            worker.function = request.form['function']
            db.session.commit()
            flash('Worker updated successfully.', 'success')
            return redirect(url_for('view_workers'))

        return render_template('edit_worker.html', worker=worker)
    else:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('index'))

# Delete a worker
@app.route('/delete_worker/<int:worker_id>', methods=['POST'])
@login_required
def delete_worker(worker_id):
    if current_user.role == 'employer':
        worker = Worker.query.get(worker_id)
        if not worker:
            flash('Worker not found.', 'error')
            return redirect(url_for('view_workers'))

        db.session.delete(worker)
        db.session.commit()
        flash('Worker deleted successfully.', 'success')
        return redirect(url_for('view_workers'))
    else:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('index'))

# API endpoint to get worker details
@app.route('/worker_details/<int:worker_id>')
@login_required
def worker_details(worker_id):
    if current_user.role == 'employer':
        worker = Worker.query.get(worker_id)
        if not worker or worker.employer_id != current_user.id:
            return jsonify({'error': 'Worker not found or unauthorized'})
        return jsonify({
            'id': worker.id,
            'name': worker.name,
            'function': worker.function
        })
    else:
        return jsonify({'error': 'You are not authorized to view this page.'})




#EMPLOYEES SECTION




#ROUTES OTHERS
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            if user.role == 'employer':
                return redirect(url_for('employer_dashboard'))  # Redirect to employer dashboard for employers
            elif user.role == 'admin':
                return redirect(url_for('admin'))  # Redirect to admin page for admins
            else:
                return redirect(url_for('index'))  # Redirect to home for other roles
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))  # Redirect back to login page
    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'employer'  # Set the role to 'employer' for users registering through this form
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


    

if __name__ == '__main__':
    # Create SQLite database file if not exists
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()

    # Ensure admin user exists
    with app.app_context():
        admin_user = User.query.filter_by(username='admin', role='admin').first()
        if not admin_user:
            admin_user = User(username='admin', password='34000', role='admin')
            db.session.add(admin_user)
            db.session.commit()

    app.run(host='0.0.0.0', port=5005)
