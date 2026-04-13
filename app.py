from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)

# Secret key is required to use 'sessions' securely
app.secret_key = 'super_secret_key_change_this_later'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iara_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


# Create the database tables
with app.app_context():
    db.create_all()


# --- PAGE ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user in the database
        user = User.query.filter_by(username=username).first()

        # Check if user exists and password matches the hash
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/ticket')
def ticket():
    return render_template('ticket.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if username is already taken
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Username already exists! Please choose another.')
        return redirect(url_for('login'))

    # Hash the password and save the new user
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    # Automatically log them in after registering
    session['user_id'] = new_user.id
    session['username'] = new_user.username
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))


# --- API ROUTES (From before) ---
@app.route('/calculate', methods=['POST'])
def calculate_price():
    data = request.get_json()
    age_group = data.get('age')
    duration = data.get('duration')
    is_disabled = data.get('disabled')

    # UPDATED: Base prices now in Euros (roughly converted from Leva)
    prices = {
        'day': 5.0,
        'week': 15.0,
        'year': 50.0
    }

    price = prices.get(duration, 0)

    if is_disabled:
        price = 0.0
    elif age_group == 'child' or age_group == 'pensioner':
        price = price * 0.5

    return jsonify({'price': price})


@app.route('/buy', methods=['POST'])
def buy_ticket():
    data = request.get_json()
    price = data.get('price')
    ticket_id = f"IARA-{random.randint(1000, 9999)}"

    return jsonify({'ticket_id': ticket_id, 'price': price, 'status': 'success'})


if __name__ == '__main__':
    app.run(debug=True)