from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from functools import wraps
import random

app = Flask(__name__)

# Secret key is required to use 'sessions' securely
app.secret_key = 'super_secret_key_change_this_later'

# --- 1. CONFIGURATION AND DB SETUP ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iara_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- 2. MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='fisherman')  # 'admin', 'inspector', 'fisherman'
    tickets = db.relationship('Ticket', backref='owner', lazy=True)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permit_id = db.Column(db.String(20), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Vessel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(20), unique=True, nullable=False)
    tonnage = db.Column(db.Float, nullable=False)
    engine_power = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Active")


# Create the database tables
with app.app_context():
    db.create_all()
    # Add role column if it doesn't exist (for existing databases)
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('user')]
    if 'role' not in columns:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'fisherman'"))
        db.session.commit()


# --- AUTHENTICATION DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in roles:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- PAGE ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role  # Store role in session
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/ticket')
@login_required
def ticket():
    return render_template('ticket.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'fisherman')  # Default to fisherman
    
    # Validate role
    valid_roles = ['admin', 'inspector', 'fisherman']
    if role not in valid_roles:
        flash('Invalid role selected!')
        return redirect(url_for('login'))
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Username already exists!')
        return redirect(url_for('login'))
    
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    session['username'] = new_user.username
    session['user_role'] = new_user.role
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    user_tickets = Ticket.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', tickets=user_tickets)


# --- VESSEL ROUTES ---
@app.route('/vessels')
@login_required
def vessels():
    # Fishermen see only their vessels, Inspectors/Admins see all
    if session['user_role'] in ['inspector', 'admin']:
        all_vessels = Vessel.query.all()
    else:
        all_vessels = Vessel.query.filter_by(user_id=session['user_id']).all()
    return render_template('vessels.html', vessels=all_vessels)


@app.route('/register_vessel', methods=['POST'])
@login_required
def register_vessel():

    name = request.form.get('name', '')
    reg_num = request.form.get('reg_num', '')
    tonnage_val = request.form.get('tonnage', '0')
    power_val = request.form.get('power', '0')

    new_vessel = Vessel(
        user_id=session['user_id'],
        name=name,
        registration_number=reg_num,
        tonnage=float(tonnage_val),
        engine_power=float(power_val)
    )
    db.session.add(new_vessel)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Vessel registered successfully'})


# --- ADMIN ROUTES ---
@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)


@app.route('/admin/all_tickets')
@login_required
@role_required('admin')
def admin_all_tickets():
    all_tickets = Ticket.query.all()
    return render_template('admin/all_tickets.html', tickets=all_tickets)


@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    total_users = User.query.count()
    total_tickets = Ticket.query.count()
    total_vessels = Vessel.query.count()
    return render_template('admin/dashboard.html', 
                         total_users=total_users,
                         total_tickets=total_tickets,
                         total_vessels=total_vessels)


# --- INSPECTOR ROUTES ---
@app.route('/inspector/dashboard')
@login_required
@role_required('inspector', 'admin')
def inspector_dashboard():
    return render_template('inspector/dashboard.html')


@app.route('/inspector/verify', methods=['POST'])
@login_required
@role_required('inspector', 'admin')
def inspector_verify_ticket():
    permit_id = request.form.get('permit_id')
    ticket = Ticket.query.filter_by(permit_id=permit_id).first()
    
    if ticket:
        owner = User.query.get(ticket.user_id)
        return jsonify({
            'status': 'valid',
            'permit_id': ticket.permit_id,
            'owner': owner.username,
            'purchase_date': ticket.purchase_date.strftime('%Y-%m-%d'),
            'price': ticket.price
        })
    else:
        return jsonify({'status': 'invalid', 'message': 'Permit not found'})


if __name__ == '__main__':
    app.run(debug=True)