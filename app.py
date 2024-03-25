from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
import hashlib
import datetime

from datetime import timedelta
from collections import OrderedDict
import os
from sqlalchemy.orm import relationship


app = Flask(__name__)
app.secret_key = 'your_secret_key'


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'app.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy database instance
db = SQLAlchemy(app)




# Define database models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def __init__(self, username, password, role, email):
        self.username = username
        self.password = password
        self.email = email
        self.role = role
    
class Worker(db.Model):
    worker_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    function_id = db.Column(db.Integer, db.ForeignKey('function.function_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('workers', lazy=True))
    function = db.relationship('Function', back_populates='workers')

    def __init__(self, name, last_name, email, function_id, user_id):
        self.name = name
        self.last_name = last_name
        self.email = email

        self.function_id = function_id
        self.user_id = user_id




class Function(db.Model):
    function_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)

    workers = db.relationship('Worker', back_populates='function')


class Position(db.Model):
    position_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)


class Shift(db.Model):
    shift_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)


class Slot(db.Model):
    slot_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)


class Year_Days(db.Model):
    __tablename__ = 'year_days' 
    day_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    day_of_year = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    week_number = db.Column(db.String(20), nullable=False)


class Schedule(db.Model):
    schedule_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.worker_id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('position.position_id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.shift_id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.slot_id'), nullable=False)
    day_id = db.Column(db.Integer, db.ForeignKey('year_days.day_id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)

    worker = db.relationship('Worker', backref='schedules')
    position = db.relationship('Position', backref='schedules')
    shift = db.relationship('Shift', backref='schedules')
    slot = db.relationship('Slot', backref='schedules')
    year_day = db.relationship('Year_Days', backref='schedules')






def employer_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to view this page.', 'error')
            return redirect(url_for('login'))
        if current_user.role != 'employer':
            flash('You do not have permission to view this page.', 'error')
            return redirect('/')
        return func(*args, **kwargs)
    return decorated_function


def create_user(username, email, password):
    user = User(username=username, email=email, password=password, role='employer')
    db.session.add(user)
    db.session.commit()


def authenticate_user(username, password):
    user = User.query.filter_by(username=username, password=password).first()
    return user


def get_user_role(user_id):
    user = User.query.get(user_id)
    return user.role if user else None


def fetch_all(user_id, table_name):
    if table_name not in ['Worker', 'Function', 'Position', 'Shift', 'Slot', 'Year_Days', 'Schedule']:
        return None  
    table_class = globals()[table_name]
    items = table_class.query.filter_by(user_id=user_id).all()
    return items


def fetch_data_for_viewer(user_id):
    tables = {
        'Workers': [row.__dict__ for row in fetch_all(user_id, 'Worker')],
        'Functions': [row.__dict__ for row in fetch_all(user_id, 'Function')],
        'Positions': [row.__dict__ for row in fetch_all(user_id, 'Position')],
        'Shifts': [row.__dict__ for row in fetch_all(user_id, 'Shift')],
        'Slots': [row.__dict__ for row in fetch_all(user_id, 'Slot')],
        'Year_Days': [row.__dict__ for row in fetch_all(user_id, 'Year_Days')],
        'Schedule': [row.__dict__ for row in fetch_all(user_id, 'Schedule')]
    }

    # Filter out empty tables
    non_empty_tables = {name: data for name, data in tables.items() if data}
    any_empty_table = any(len(data) == 0 for data in tables.values())

    return non_empty_tables, any_empty_table





def fetch_by_id(table_name, item_id, user_id):
    item = db.session.query(eval(table_name.capitalize())).filter_by(id=item_id, user_id=user_id).first()
    return item.__dict__ if item else None

def add_item(table_name, user_id, **kwargs):
    item = eval(table_name.capitalize())(user_id=user_id, **kwargs)
    db.session.add(item)
    db.session.commit()

def update_item(table_name, user_id, item_id, **kwargs):
    item = db.session.query(eval(table_name.capitalize())).filter_by(id=item_id, user_id=user_id).first()
    if item:
        for key, value in kwargs.items():
            setattr(item, key, value)
        db.session.commit()

def delete_item(table_name, user_id, item_id):
    item = db.session.query(eval(table_name.capitalize())).filter_by(id=item_id, user_id=user_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()


def create_user_database(user_id, year=None):
    if year is not None:
        year_int = int(year)
        # Populate Year_Days table with the days of the given year for the specific user
        total_days = 366 if year_int % 4 == 0 and (year_int % 100 != 0 or year_int % 400 == 0) else 365
        day_data = []
        current_date = datetime.date(year_int, 1, 1)  # Start from January 1st of the given year
        for i in range(1, total_days + 1):
            day_of_week = current_date.weekday() + 1  # Adjusting to 1-based index
            week_year = str(current_date.isocalendar()[0])[2:]  # Get the 2-digit year
            week_number = str(current_date.isocalendar()[1]).zfill(2)  # Get the 2-digit week and zero-pad if necessary
            week_number = week_year + week_number  # Concatenate year and week number
            day_data.append(Year_Days(user_id=user_id, year=year_int, day_of_year=i, date=current_date, day_of_week=day_of_week, week_number=week_number))
            current_date += datetime.timedelta(days=1)  # Move to the next day

        db.session.add_all(day_data)
        db.session.commit()


def get_date_for_day(year, week, day):
    iso_week_date_str = f'{year}-W{week}-{day}'
    start_date = datetime.datetime.strptime(iso_week_date_str, "%G-W%V-%u")
    return start_date.strftime("%Y-%m-%d")

def get_week_number(year, month, day):
    date_obj = datetime.date(year, month, day)
    week_number = date_obj.isocalendar()[1]
    return week_number

def fetch_by_id_days(user_id, day_id):
    day = Year_Days.query.filter_by(id_day=day_id, user_id=user_id).first()
    return day.__dict__ if day else None

def fetch_all_unique_years(user_id):
    # Use distinct() without arguments
    years = db.session.query(Year_Days.year).filter_by(user_id=user_id).distinct().order_by(Year_Days.year).all()
    return [year[0] for year in years]

def delete_year_entries(user_id, year):
    Year_Days.query.filter_by(user_id=user_id, year=year).delete()
    db.session.commit()

def fetch_days_by_year_and_week(user_id, year, week):
    days = Year_Days.query.filter_by(user_id=user_id, year=year, week_number=week).all()
    return [day.__dict__ for day in days]

def fetch_schedule_data_for_week(user_id, week):
    # Get the current year
    current_year = datetime.datetime.now().year
    
    # Calculate the start and end dates of the week based on the year and week number
    start_date = datetime.datetime.strptime(f'{current_year}-W{week}-1', "%Y-W%W-%w")
    end_date = start_date + datetime.timedelta(days=6)
    
    # Query the database for schedule data within the specified date range
    schedule_data = Schedule.query.filter(
        Schedule.user_id == user_id,
        Schedule.year == current_year,
        Schedule.day_id >= start_date.timetuple().tm_yday,  # Day of year for start date
        Schedule.day_id <= end_date.timetuple().tm_yday     # Day of year for end date
    ).all()
    
    # Format the fetched data for sending to the frontend
    formatted_data = []
    for entry in schedule_data:
        formatted_entry = {
            'worker_id': entry.worker_id,
            'position_id': entry.position_id,
            'shift_id': entry.shift_id,
            'slot_id': entry.slot_id,
            'day_id': entry.day_id - start_date.timetuple().tm_yday + 1,  # Adjust day ID relative to start of the week
            'year': entry.year
            # Add more fields as needed
        }
        formatted_data.append(formatted_entry)
    
    return formatted_data



def get_schedule_entry_for_day(schedule_data, day):
    for entry in schedule_data:
        if entry['day_id'] == day:
            return entry
    return None











# USERS LOGIN / REGISTER / LOGOUT

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        create_user(username, email, password)
        flash('Registration successful! Please log in.', 'success')
        # After registration, log in the user and set session variables
        user = authenticate_user(username, password)
        if user:
            login_user(user)
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))  # Redirect to dashboard after registration
        else:
            flash('Failed to log in after registration. Please try logging in manually.', 'error')
            return redirect(url_for('login'))  # Redirect to login page if unable to log in automatically
    return render_template('register.html')


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
            session['user_id'] = user.id
            session['username'] = user.username
            if user.role == 'employer':
                return redirect(url_for('index'))  # Redirect to employer dashboard for employers
            elif user.role == 'admin':
                return redirect(url_for('admin'))  # Redirect to admin page for admins
            else:
                return redirect(url_for('dashboard'))  # Redirect to home for other roles
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))  # Redirect back to login page
    return render_template('login.html')

# User logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect('/login')







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
    
    # Delete the associated workers
    workers_to_delete = Worker.query.filter_by(employer_id=user_id).all()
    for worker in workers_to_delete:
        db.session.delete(worker)


    # Delete the user from the database
    db.session.delete(user_to_delete)
    db.session.commit()

    flash(f'User {user_to_delete.username} has been successfully deleted.', 'success')
    return redirect(url_for('admin'))







# EMPLOYERS SECTION


@app.route('/')
def index():
    # Check if the user is logged in
    if current_user.is_authenticated:
        # Get username and role from the current_user object
        username = current_user.username
        role = current_user.role
        return render_template('index.html', username=username, role=role)
    else:
        # User is not logged in
        return render_template('index.html', username=None, role=None)


@app.route('/create_year', methods=['POST'])
@employer_required
def create_year():
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect('/login')

    year = int(request.form.get('year'))
    user_id = session['user_id']
    create_user_database(user_id, year)  # Pass user_id instead of username
    flash(f'Year {year} and its days created successfully!', 'success')
    return redirect('/')

@app.route('/database_viewer')
@employer_required  
def display_database_viewer():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    tables, any_empty_table = fetch_data_for_viewer(user_id)

    return render_template('database_viewer.html', tables=tables, any_empty_table=any_empty_table)




# CRUD DATABASE TABLE 

# Universal edit item route
@app.route('/edit/<table_name>/<int:item_id>', methods=['GET', 'POST'])
@employer_required
def edit_item(table_name, item_id):
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        form_data = dict(request.form)
        update_item(table_name, user_id, item_id, **form_data)
        flash('Item details updated successfully!', 'success')
        return redirect(f'/{table_name.lower()}s')
    
    elif request.method == 'GET':
        user_id = session['user_id']
        item = fetch_by_id(table_name, item_id, user_id)
        if item:
            # Additional data fetching for specific tables can be done here
            return render_template('edit_item.html', table_name=table_name, item=item)
        else:
            flash('Item not found!', 'error')
            return redirect('/')

# Universal add item route
@app.route('/add/<table_name>', methods=['POST'])
@employer_required
def add_item_route(table_name):
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))
        

    user_id = session['user_id']

    
    add_item(table_name, user_id, **request.form)
    flash('New item added successfully!', 'success')

    # Redirect to the appropriate route
    return redirect(f'/{table_name.lower()}s')

# Universal delete item route
@app.route('/delete/<table_name>/<int:item_id>', methods=['POST'])
@employer_required
def delete_item_route(table_name, item_id):
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    delete_item(table_name, user_id, item_id)
    flash('Item deleted successfully!', 'success')

    # Redirect to the appropriate route
    return redirect(f'/{table_name.lower()}s')







# Display workers route
@app.route('/workers')
@employer_required
def display_workers():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    workers = fetch_all(user_id, 'Worker')
    functions = fetch_all(user_id, 'Function')

    function_names = {function.function_id: function.name for function in functions}
    for worker in workers:
        worker.function_name = function_names.get(worker.function_id, 'N/A')

    return render_template('workers.html', workers=workers, functions=functions)




# Display functions route
@app.route('/functions')
@employer_required
def display_functions():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    functions = fetch_all(user_id, 'Function')
    return render_template('functions.html', functions=functions)

# Display positions route
@app.route('/positions')
@employer_required
def display_positions():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    positions = fetch_all(user_id, 'Position')
    return render_template('positions.html', positions=positions)

# Display shifts route
@app.route('/shifts')
@employer_required
def display_shifts():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    shifts = fetch_all(user_id, 'Shift')
    return render_template('shifts.html', shifts=shifts)

# Display slots route
@app.route('/slots')
@employer_required
def display_slots():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    slots = fetch_all(user_id, 'Slot')
    return render_template('slots.html', slots=slots)






# Display days for years route
@app.route('/days_for_years')
@employer_required
def days_for_years():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    years = fetch_all_unique_years(user_id)  # Fetch unique years by user_id
    return render_template('days_for_years.html', years=years)

# Delete year route
@app.route('/delete_year/<int:year>', methods=['GET', 'POST'])
@employer_required
def delete_year(year):
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    delete_year_entries(user_id, year)  # Delete year entries by user_id and year
    flash(f'Year {year} deleted successfully!', 'success')
    return redirect('/days_for_years')

# Add year route
@app.route('/add_year', methods=['POST'])
@employer_required
def add_year():
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    new_year = int(request.form.get('new_year'))
    if new_year:
        create_user_database(user_id, new_year) # Create user database entry for the new year
        flash(f'Year {new_year} added successfully!', 'success')
    else:
        flash('Invalid input for new year!', 'error')
    return redirect('/days_for_years')










# Scheduling route
@app.route('/scheduling')
@employer_required
def scheduling():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    workers = fetch_all(user_id, 'Worker')
    positions = fetch_all(user_id, 'Position')
    shifts = fetch_all(user_id, 'Shift')
    slots = fetch_all(user_id, 'Slot')
    schedule_events = fetch_all(user_id, 'Schedule') 
    days = fetch_all(user_id, 'Year_Days')

    # Fetch all unique years for the user
    unique_years = fetch_all_unique_years(user_id)

    # Create a dictionary of worker names
    worker_names = {worker.worker_id: f"{worker.name} {worker.last_name}" for worker in workers}

    return render_template('scheduling.html', workers=workers, positions=positions, shifts=shifts, slots=slots, days=days, schedule_events=schedule_events, unique_years=unique_years, worker_names=worker_names)






# Schedule worker route
@app.route('/schedule_worker', methods=['POST'])
@employer_required
def schedule_worker():
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    worker_id = request.form.get('worker')
    position_id = request.form.get('position')
    shift_id = request.form.get('shift')
    slot_id = request.form.get('slot')
    day_id = request.form.get('day')
    year = request.form.get('year')  # Get the selected year from the form

    print("Received form data:", user_id, worker_id, position_id, shift_id, slot_id, day_id, year)  # Debugging

    # Insert the scheduling information into the database
    try:
        add_item('Schedule', user_id=user_id, worker_id=worker_id, position_id=position_id, shift_id=shift_id, slot_id=slot_id, day_id=day_id, year=year)  # Include the year parameter here
        print("Scheduling successful!")  # Debugging
        flash('Worker scheduled successfully!', 'success')
        return redirect(url_for('scheduling'))
    except Exception as e:
        print("Error scheduling worker:", e)  # Debugging
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('scheduling'))


@app.route('/schedule_view')
@employer_required
def schedule_view():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    # Get the current week number
    current_week = datetime.datetime.now().isocalendar()[1]
    user_id = session['user_id']

    # Calculate the start date of the current week
    today = datetime.datetime.now()
    start_of_week = today - datetime.timedelta(days=today.weekday())

    # Fetch schedule data for the current week
    schedule_data = fetch_schedule_data_for_week(user_id, current_week)

    # Pass the first day of the current week and datetime module to the template
    return render_template('schedule_view.html', current_week=current_week, start_of_week=start_of_week, schedule_data=schedule_data, get_schedule_entry_for_day=get_schedule_entry_for_day, datetime=datetime)


# Edit schedule route
@app.route('/edit_schedule', methods=['POST'])
@employer_required
def edit_schedule():
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    year = request.form.get('year')
    week = request.form.get('week')

    # Fetch days based on the provided year and week number
    days = fetch_days_by_year_and_week(user_id, year, week)

    return render_template('edit_schedule.html', days=days)










# EMPLOYEE SECTION
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'employee':
        user_id = session.get('user_id')  # Retrieve user ID from the session
        username = session.get('username')
        return render_template('dashboard.html', user_id = user_id, username = username)
    else:
        flash('You are not authorized to view this page.', 'error')
        return redirect(url_for('index'))






if __name__ == '__main__':
    # Create SQLite database file if not exists
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()

    # Ensure admin user exists
    with app.app_context():
        admin_user = User.query.filter_by(username='admin', role='admin').first()
        if not admin_user:
            admin_user = User(username='admin', password='34000', role='admin', email='jsakoman1@gmail.com')
            db.session.add(admin_user)
            db.session.commit()

    app.run(host='0.0.0.0', port=5005)
