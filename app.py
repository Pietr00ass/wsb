# app.py
import os
from datetime import datetime, timedelta
from io import BytesIO

from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
from flask_mail import Mail, Message
import face_recognition
from functools import wraps

# ----- Configuration -----
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///auth.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Mail settings (example using Gmail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# ----- Models -----
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    totp_secret = db.Column(db.String(16), nullable=False)
    sms_code = db.Column(db.String(6), nullable=True)
    sms_code_expiry = db.Column(db.DateTime, nullable=True)
    face_encoding = db.Column(db.PickleType, nullable=True)
    roles = db.relationship('Role', secondary=user_roles, backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ----- Login loader -----
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----- RBAC decorator -----
def roles_required(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            user_roles = {r.name for r in current_user.roles}
            if not any(role in user_roles for role in role_names):
                flash('Brak uprawnień do tej strony.', 'danger')
                return redirect(url_for('protected'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ----- Routes (GUI) -----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        method = request.form.get('2fa_method', 'totp')
        if User.query.filter_by(username=username).first():
            flash('Użytkownik już istnieje.', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, email=email, totp_secret=pyotp.random_base32())
        user.set_password(password)
        face_img = request.files.get('face_image')
        if face_img:
            img = face_img.read()
            encs = face_recognition.face_encodings(face_recognition.load_image_file(BytesIO(img)))
            if encs:
                user.face_encoding = encs[0]
        role = Role.query.filter_by(name='user').first() or Role(name='user')
        db.session.add(role)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        flash('Zarejestrowano! Zaloguj się.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        method = request.form.get('2fa_method', 'totp')
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Nieprawidłowe dane.', 'danger')
            return redirect(url_for('login'))
        session['pre_2fa_user'] = user.id
        session['2fa_method'] = method
        if method == 'totp':
            return redirect(url_for('verify_2fa'))
        code = pyotp.random_base32()[:6]
        user.sms_code = code
        user.sms_code_expiry = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()
        if method == 'email':
            msg = Message('Kod logowania', recipients=[user.email])
            msg.body = f'Twój kod: {code}'
            mail.send(msg)
        flash('Kod 2FA wysłany.', 'info')
        return redirect(url_for('verify_2fa'))
    return render_template('login.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    if request.method == 'POST':
        code = request.form['code']
        user = User.query.get(session.get('pre_2fa_user'))
        method = session.get('2fa_method')
        if (method == 'totp' and not pyotp.TOTP(user.totp_secret).verify(code)) or            (method != 'totp' and (user.sms_code != code or datetime.utcnow() > user.sms_code_expiry)):
            flash('Nieprawidłowy lub wygasły kod.', 'danger')
            return redirect(url_for('verify_2fa'))
        session.pop('pre_2fa_user', None)
        session.pop('2fa_method', None)
        login_user(user)
        flash('Zalogowano pomyślnie!', 'success')
        return redirect(url_for('protected'))
    return render_template('verify_2fa.html')

@app.route('/verify-face', methods=['GET', 'POST'])
@login_required
def verify_face():
    if request.method == 'POST':
        face_img = request.files.get('face_image')
        img = face_img.read()
        encs = face_recognition.face_encodings(face_recognition.load_image_file(BytesIO(img)))
        if not encs or not face_recognition.compare_faces([current_user.face_encoding], encs[0])[0]:
            flash('Weryfikacja biometryczna nie powiodła się.', 'danger')
            return redirect(url_for('verify_face'))
        flash('Biometria OK.', 'success')
        return redirect(url_for('protected'))
    return render_template('verify_face.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Wylogowano.', 'info')
    return redirect(url_for('login'))

@app.route('/protected')
@login_required
def protected():
    return render_template('protected.html')

@app.route('/admin')
@roles_required('admin')
def admin_panel():
    return render_template('admin.html')

if __name__ == '__main__':
    db.create_all()
    for rn in ['user', 'admin']:
        if not Role.query.filter_by(name=rn).first():
            db.session.add(Role(name=rn))
    db.session.commit()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))