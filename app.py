from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
import hashlib
import datetime
import stripe
from datetime import timedelta
from collections import OrderedDict, defaultdict
import os
from sqlalchemy.orm import relationship
from sqlalchemy.orm import joinedload
from sqlalchemy import asc
from itertools import groupby

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.jinja_env.globals.update(zip=zip)

stripe.api_key = 'your_stripe_api_key'  # Replace this with your Stripe API key



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
    schedules = db.relationship('Schedule', backref='year_day', lazy=True)

class Schedule(db.Model):
    schedule_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.worker_id'), nullable=True)
    position_id = db.Column(db.Integer, db.ForeignKey('position.position_id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.shift_id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.slot_id'), nullable=False)
    day_id = db.Column(db.Integer, db.ForeignKey('year_days.day_id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    week_number = db.Column(db.String(20), nullable=False)

    worker = db.relationship('Worker', backref='schedules')
    position = db.relationship('Position', backref='schedules')
    shift = db.relationship('Shift', backref='schedules')
    slot = db.relationship('Slot', backref='schedules')

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('position.position_id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.shift_id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.slot_id'), nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('templates', lazy=True))
    position = db.relationship('Position', backref='templates')
    shift = db.relationship('Shift', backref='templates')
    slot = db.relationship('Slot', backref='templates')

    def __init__(self, user_id, position_id, shift_id, slot_id):
        self.user_id = user_id
        self.position_id = position_id
        self.shift_id = shift_id
        self.slot_id = slot_id


class ActiveDaysTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    monday = db.Column(db.Boolean, nullable=False, default=True)
    tuesday = db.Column(db.Boolean, nullable=False, default=True)
    wednesday = db.Column(db.Boolean, nullable=False, default=True)
    thursday = db.Column(db.Boolean, nullable=False, default=True)
    friday = db.Column(db.Boolean, nullable=False, default=True)
    saturday = db.Column(db.Boolean, nullable=False, default=True)
    sunday = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships
    user = db.relationship('User', backref=db.backref('active_days_templates', lazy=True))

    def __init__(self, user_id):
        self.user_id = user_id




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


def get_week_number(year, month, day):
    date_obj = datetime.date(year, month, day)
    week_number = date_obj.isocalendar()[1]
    return week_number


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



def ensure_year_days_exist(user_id, year):
    # Check if the year already has entries
    year_exists = db.session.query(Year_Days).filter_by(user_id=user_id, year=year).first()
    if year_exists:
        return  # Exit if the year's days already exist

    # Generate days for the year if they do not exist
    is_leap_year = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    total_days = 366 if is_leap_year else 365
    for day_of_year in range(1, total_days + 1):
        date = datetime.date(year, 1, 1) + datetime.timedelta(days=day_of_year - 1)
        iso_year, iso_week, iso_day = date.isocalendar()
        week_number = f"{str(iso_year)[-2:]}{str(iso_week).zfill(2)}"  # Use ISO year and week number
        new_day = Year_Days(
            user_id=user_id,
            year=year,
            day_of_year=day_of_year,
            date=date,
            day_of_week=iso_day,  # ISO day of the week (1=Monday, 7=Sunday)
            week_number=week_number
        )
        db.session.add(new_day)
    db.session.commit()

def shift_has_data(existing_templates, position_id, shift_id):
    for template in existing_templates:
        if (template.position_id == position_id) and (template.shift_id == shift_id):
            return True
    return False










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







#FLASK ROUTES FOR WEB PAGES

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



@app.route('/functions')
@employer_required
def display_functions():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    functions = fetch_all(user_id, 'Function')
    return render_template('functions.html', functions=functions)


@app.route('/positions')
@employer_required
def display_positions():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    positions = fetch_all(user_id, 'Position')
    return render_template('positions.html', positions=positions)


@app.route('/shifts')
@employer_required
def display_shifts():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    shifts = fetch_all(user_id, 'Shift')
    return render_template('shifts.html', shifts=shifts)


@app.route('/slots')
@employer_required
def display_slots():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    slots = fetch_all(user_id, 'Slot')
    return render_template('slots.html', slots=slots)



@app.route('/template', methods=['GET', 'POST'])
@login_required
@employer_required
def template():
    user_id = current_user.id
    positions = Position.query.filter_by(user_id=user_id).all()
    shifts = Shift.query.filter_by(user_id=user_id).all()
    slots = Slot.query.filter_by(user_id=user_id).all()

    
    existing_templates = Template.query.filter_by(user_id=user_id).all()

    selected_combinations = {(template.position_id, template.shift_id, template.slot_id) for template in existing_templates}
    
    print(selected_combinations)  # Debugging: print selected_combinations to see its contents

    if request.method == 'POST':
        # Clear existing templates for this user
        Template.query.filter_by(user_id=user_id).delete()

        # Process form data and create new Template entries as needed
        for position in positions:
            if request.form.get(f'positions[{position.position_id}][include]'):
                for shift in shifts:
                    shift_checkbox_name = f'positions[{position.position_id}][shifts][{shift.shift_id}][include]'
                    if request.form.get(shift_checkbox_name):
                        for slot in slots:
                            slot_checkbox_name = f'positions[{position.position_id}][shifts][{shift.shift_id}][slots][{slot.slot_id}]'
                            if request.form.get(slot_checkbox_name):
                                new_template = Template(user_id=user_id, position_id=position.position_id, shift_id=shift.shift_id, slot_id=slot.slot_id)
                                db.session.add(new_template)

        db.session.commit()
        flash('Template saved successfully.')
        return redirect(url_for('template'))

    return render_template('template.html', positions=positions, shifts=shifts, slots=slots, selected_combinations=selected_combinations, existing_templates=existing_templates, shift_has_data=shift_has_data)



@app.route('/editor', methods=['GET', 'POST'])
@employer_required
def editor():
    user_id = session['user_id']

    if request.method == 'POST':
        input_week_number = request.form.get('week_number', type=int)
        year = request.form.get('year', type=int)

        ensure_year_days_exist(user_id, year)

        formatted_week_number = f"{str(year)[-2:]}{str(input_week_number).zfill(2)}"
        
        days_in_week = Year_Days.query.filter_by(user_id=user_id, year=year, week_number=formatted_week_number).all()

        if not days_in_week:
            flash('No days found for the selected week and year.', 'error')
            return redirect(url_for('editor')) 

        templates = Template.query.filter_by(user_id=user_id).all()

        for day in days_in_week:
            for template in templates:
                new_schedule = Schedule(
                    user_id=user_id,
                    position_id=template.position_id,
                    shift_id=template.shift_id,
                    slot_id=template.slot_id,
                    day_id=day.day_id,
                    year=year,
                    week_number=formatted_week_number,
                    worker_id=None 
                )
                db.session.add(new_schedule)
        
        db.session.commit()
        
        flash('Schedule template for the week created successfully!', 'success')
        
        return redirect(url_for('editor'))

    else:
         # Calculate the current week number and year
        from datetime import datetime, date

        today = date.today()
        current_week_number = today.isocalendar()[1]
        current_year = today.year
        week_number = request.args.get('week', default=current_week_number, type=int)
        year = request.args.get('year', default=current_year, type=int)
        week_str = f"{str(year)[-2:]}{str(week_number).zfill(2)}"

        all_workers = Worker.query.filter_by(user_id=user_id).all()

        # Convert workers to a format easy to use in the template, e.g., a list of tuples (id, name)
        workers_list = [(worker.worker_id, worker.name) for worker in all_workers]

        # Fetch schedules with related models preloaded to reduce database queries
        week_schedules = Schedule.query.options(
            joinedload(Schedule.position),
            joinedload(Schedule.shift),
            joinedload(Schedule.slot),
            joinedload(Schedule.worker),
            joinedload(Schedule.year_day)
        ).filter_by(user_id=user_id, week_number=week_str).order_by(
            asc(Schedule.position_id), 
            asc(Schedule.shift_id), 
            asc(Schedule.slot_id)
        ).all()

        # Aggregate schedules by position, shift, and slot
        aggregated_schedules = {}
        for schedule in week_schedules:
            key = (schedule.position_id, schedule.shift_id, schedule.slot_id)
            if key not in aggregated_schedules:
                aggregated_schedules[key] = {
                    "position_name": schedule.position.name,
                    "shift_name": schedule.shift.name,
                    "slot_name": schedule.slot.name,
                    "workers_by_day": [None] * 7,
                    "day_ids": [None] * 7, # Initialize with None for 7 days,
                    "position_id": schedule.position_id,  # Add position ID
                    "shift_id": schedule.shift_id,  # Add shift ID
                    "slot_id": schedule.slot_id,  # Add slot ID
                }
            day_index = schedule.year_day.date.weekday()  # 0 = Monday, 6 = Sunday
            aggregated_schedules[key]["workers_by_day"][day_index] = schedule.worker.name if schedule.worker else ""
            aggregated_schedules[key]["day_ids"][day_index] = schedule.day_id

        # Convert to a list for template rendering
        schedule_rows = list(aggregated_schedules.values())

        return render_template('editor.html', week_number=week_number, year=year, schedule_rows=schedule_rows, no_schedules=len(schedule_rows) == 0, workers_list=workers_list)


@app.route('/simple_view')
@employer_required
def simple_view():
    from datetime import date

    user_id = session['user_id']
    today = date.today()
    current_week_number = today.isocalendar()[1]
    current_year = today.year

    year = request.args.get('year', default=current_year, type=int)
    week_number = request.args.get('week', default=current_week_number, type=int)
    formatted_week_number = f"{str(year)[-2:]}{str(week_number).zfill(2)}"

    schedules = Schedule.query.options(
        joinedload(Schedule.worker),
        joinedload(Schedule.position),
        joinedload(Schedule.shift),
        joinedload(Schedule.slot),
        joinedload(Schedule.year_day)
    ).filter(
        Schedule.user_id == user_id,
        Schedule.year == year,
        Schedule.week_number == formatted_week_number
    ).all()

    position_shift_structure = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for schedule in schedules:
        position_shift_key = (schedule.position.name, schedule.shift.name)
        slot_name = schedule.slot.name
        worker_name = schedule.worker.name if schedule.worker else None
        day_of_week = schedule.year_day.date.strftime("%A")

        if worker_name:
            position_shift_structure[position_shift_key][slot_name][day_of_week].append(worker_name)
    
    def group_workers_by_consecutive_days(workers_by_day):
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        grouped = []
        prev_workers = None
        group_start = None
        prev_day_index = -2  # Initialize with an impossible index for comparison

        for day in days_order:
            current_day_index = days_order.index(day)
            workers = workers_by_day.get(day, [])
            # Skip days without workers
            if not workers:
                continue
            # Check if current day is consecutive to previous and has the same workers
            if current_day_index == prev_day_index + 1 and workers == prev_workers:
                prev_day_index = current_day_index
                continue
            else:
                # If there was a previous group, conclude it before starting a new one
                if prev_workers is not None:
                    days_range = f"{group_start} - {days_order[prev_day_index]}" if group_start != days_order[prev_day_index] else days_order[prev_day_index]
                    grouped_workers = ', '.join(prev_workers)
                    grouped.append(f"{days_range}: {grouped_workers}")
                # Start a new group with the current day
                group_start = day
                prev_day_index = current_day_index
                prev_workers = workers
        # Add the last group, if there are any workers
        if prev_workers:
            days_range = f"{group_start} - {days_order[prev_day_index]}" if group_start != days_order[prev_day_index] else days_order[prev_day_index]
            grouped_workers = ', '.join(prev_workers)
            grouped.append(f"{days_range}: {grouped_workers}")

        return "; ".join(grouped)

    rows = []

    for position_shift, slots in position_shift_structure.items():
        row = [*position_shift]
        relevant_slots = sorted(slots.keys())
        for slot in relevant_slots:
            workers_by_day = slots[slot]
            grouped_workers = group_workers_by_consecutive_days(workers_by_day)
            row.append(grouped_workers if grouped_workers else "No workers")
        rows.append(row)

    # For headers, we need a unique set of slots, but let's prepare it inside the loop
    unique_slots = sorted(set(slot for _, slots in position_shift_structure.items() for slot in slots))
    headers = ['Position', 'Shift'] + unique_slots

    return render_template('simple_view.html', headers=headers, rows=rows, year=year, week_number=week_number)



@app.route('/delete_week_schedule', methods=['POST'])
@employer_required
def delete_week_schedule():
    user_id = session['user_id']
    year = request.form.get('year', type=int)
    week_number = request.form.get('week_number', type=int)

    # Combine year and week_number to match your storage format
    combined_week_number = f"{year % 100:02d}{week_number:02d}"

    # Delete all schedule entries for the given week and the current user
    Schedule.query.filter_by(user_id=user_id, week_number=combined_week_number).delete()
    db.session.commit()
    
    flash(f'Schedules for week {combined_week_number} deleted successfully.')
    return redirect(url_for('editor'))


@app.route('/get_workers')
def get_workers():
    user_id = session.get('user_id')  # Assuming user_id is stored in the session
    workers = fetch_all(user_id, 'Worker')
    # Convert workers to a list of dictionaries for JSON serialization
    workers_data = [{'id': worker.worker_id, 'name': worker.name} for worker in workers]
    return jsonify(workers_data)




@app.route('/schedule_worker', methods=['POST'])
@employer_required
def schedule_worker():
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to perform this action.'}), 403

    user_id = session['user_id']
    data = request.get_json()

    print("Received data:", data)

    worker_id = data.get('workerId') or None
    position_id = data.get('positionId')
    shift_id = data.get('shiftId')
    slot_id = data.get('slotId')
    day_id = data.get('dayId')

    if not all([position_id, shift_id, slot_id, day_id]):
        return jsonify({'error': 'Missing required scheduling information.'}), 400

    existing_schedule = Schedule.query.filter_by(
        user_id=user_id,
        position_id=position_id,
        shift_id=shift_id,
        slot_id=slot_id,
        day_id=day_id
    ).first()

    if existing_schedule:
        # If found, update the worker_id
        existing_schedule.worker_id = worker_id
    else:
        # If not found, handle accordingly (either create a new one or just return an error/response)
        return jsonify({'error': 'No existing schedule found to update.'}), 404

    try:
        db.session.commit()
        return jsonify({'message': 'Worker scheduled successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500




@app.route('/fill_week_with_worker', methods=['POST'])
def fill_week_with_worker():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403

    data = request.get_json()
    user_id = session['user_id']

    try:
        # Retrieve all schedules for the week based on the provided day_id
        day = Year_Days.query.filter_by(day_id=data['dayId']).first()
        if not day:
            return jsonify({'error': 'Day not found'}), 404

        start_of_week = day.date - timedelta(days=day.date.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday

        schedules = Schedule.query.join(Year_Days).filter(
            Schedule.user_id == user_id,
            Schedule.position_id == data['positionId'],
            Schedule.shift_id == data['shiftId'],
            Schedule.slot_id == data['slotId'],
            Year_Days.date >= start_of_week,
            Year_Days.date <= end_of_week
        ).all()

        for schedule in schedules:
            schedule.worker_id = data.get('workerId')

        db.session.commit()
        return jsonify({'message': 'Week filled successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500






@app.route('/template_days', methods=['GET', 'POST'])
@login_required
@employer_required
def template_days():
    user_id = current_user.id
    active_days_template = ActiveDaysTemplate.query.filter_by(user_id=user_id).first()
    if not active_days_template:
        active_days_template = ActiveDaysTemplate(user_id=user_id)

    if request.method == 'POST':
        active_days_template.monday = bool(request.form.get('monday'))
        active_days_template.tuesday = bool(request.form.get('tuesday'))
        active_days_template.wednesday = bool(request.form.get('wednesday'))
        active_days_template.thursday = bool(request.form.get('thursday'))
        active_days_template.friday = bool(request.form.get('friday'))
        active_days_template.saturday = bool(request.form.get('saturday'))
        active_days_template.sunday = bool(request.form.get('sunday'))

        db.session.add(active_days_template)
        db.session.commit()

        flash('Active days template saved successfully.')
        return redirect(url_for('template_days'))

    return render_template('template_days.html', active_days_template=active_days_template)




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