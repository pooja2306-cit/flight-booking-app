from flask import Flask, render_template, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateTimeField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flight_booking.db'

db = SQLAlchemy(app)

# ------------------ Login Manager ------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------ Forms ------------------
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class FlightForm(FlaskForm):
    flight_number = StringField('Flight Number', validators=[DataRequired()])
    departure_city = StringField('Departure City', validators=[DataRequired()])
    arrival_city = StringField('Arrival City', validators=[DataRequired()])
    departure_time = DateTimeField(
        'Departure Time',
        validators=[DataRequired()],
        format='%Y-%m-%d %H:%M:%S'
    )
    submit = SubmitField('Add Flight')


# ------------------ Models ------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    bookings = db.relationship('Booking', backref='user', lazy=True)


class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(10), unique=True, nullable=False)
    departure_city = db.Column(db.String(50), nullable=False)
    arrival_city = db.Column(db.String(50), nullable=False)
    departure_time = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='flight', lazy=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)


# ------------------ Routes ------------------

@app.route('/')
def home():
    return "Welcome to the Flight Booking App!"


# -------- Register --------
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)

            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful!', 'success')
            return redirect(url_for('login'))

    return render_template('registration.html', form=form)


# -------- Login --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('flights'))   # 🔥 redirect to flights page
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html', form=form)


# -------- Logout --------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# -------- View Flights (NEW) --------
@app.route('/flights')
@login_required
def flights():
    flights = Flight.query.all()
    return render_template('flights.html', flights=flights)


# -------- Add Flight --------
@app.route('/add_flight', methods=['GET', 'POST'])
@login_required
def add_flight():
    form = FlightForm()

    if form.validate_on_submit():
        flight = Flight(
            flight_number=form.flight_number.data,
            departure_city=form.departure_city.data,
            arrival_city=form.arrival_city.data,
            departure_time=form.departure_time.data
        )

        db.session.add(flight)
        db.session.commit()

        flash('Flight added successfully!', 'success')
        return redirect(url_for('flights'))

    return render_template('add_flight.html', form=form)


# -------- Book Flight --------
@app.route('/book_flight/<int:flight_id>', methods=['GET', 'POST'])
@login_required
def book_flight(flight_id):
    flight = Flight.query.get(flight_id)

    # ✅ FIX: prevent None error
    if not flight:
        flash("Flight not found!", "danger")
        return redirect(url_for('flights'))

    if request.method == 'POST':
        booking = Booking(
            user_id=current_user.id,
            flight_id=flight.id
        )

        db.session.add(booking)
        db.session.commit()

        flash('Flight booked successfully!', 'success')
        return redirect(url_for('view_bookings'))

    return render_template('book_flight.html', flight=flight)


# -------- View Bookings --------
@app.route('/view_bookings')
@login_required
def view_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('view_bookings.html', bookings=bookings)


# -------- Dashboard (optional) --------
@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('flights'))


# ------------------ Run ------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)