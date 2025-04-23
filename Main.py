from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import timedelta


app = Flask(__name__)
# socketio = SocketIO(app)

# Configure database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')  # Use SQLite for simplicity, or PostgreSQL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Suppress a warning
db = SQLAlchemy(app)
migrate = Migrate(app, db) 

# Secret key for session management
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key') # Change to a long random string in production

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Set session timeout


# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), default='student')  # Added role field

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

# Function to create database tables (run this once)
def create_database():
    with app.app_context():
        db.create_all()

users = {
    'admin': {'password': generate_password_hash('admin@123'), 'role': 'admin'},
    'student1': {'password': generate_password_hash('student@123'), 'role': 'student'},
    'librarian1': {'password': generate_password_hash('librarian@123'), 'role': 'librarian'},
    'lecturer1': {'password': generate_password_hash('lecturer@123'), 'role': 'lecturer'},
    'personnel1': {'password': generate_password_hash('it@123'), 'role': 'personnel'}
}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for(f"{user['role']}_dashboard"))
        else:
            flash('Invalid username or password')
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))  # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')  

        if User.query.filter_by(username=username).first():
            flash('Username already taken', )
            return render_template('register.html')  

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('register.html') 

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')  


@app.route('/student/dashboard')
def student_dashboard():
    if 'username' in session and session['role'] == 'student':
        return render_template('std_dash.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/librarian/dashboard')
def librarian_dashboard():
    if 'username' in session and session['role'] == 'librarian':
        return render_template('librarian.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/lecturer/dashboard')
def lecturer_dashboard():
    if 'username' in session and session['role'] == 'lecturer':
        return render_template('lecturer.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
        return render_template('Adm_dash.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/personnel/dashboard')
def personnel_dashboard():
    if 'username' in session and session['role'] == 'personnel':
        return render_template('IT_p.html', username=session['username'])
    return redirect(url_for('login'))



@app.route("/password", methods=['GET', 'POST'])
def password():
    if not session.get('username'):
        return redirect(url_for('login'))
    user = User.query.get(session['username'])
    
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = "temporary_password" # Replace this with actual password generation
        hashed_password = generate_password_hash(new_password, method='sha256')
        user_to_update = User.query.filter_by(email=email).first()

        if user_to_update:
            user_to_update.password = hashed_password
            db.session.commit()
            flash(f'Password reset for {email}.  New password is: {new_password}', 'success')
            return redirect(url_for('password'))
        else:
            flash('Email not found') 
    return render_template('pass.html')  



@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
      db.create_all()
    app.run(debug=True)