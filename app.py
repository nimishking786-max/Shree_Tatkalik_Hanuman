import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
from functools import wraps
import secrets

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
# Database configuration
if os.environ.get('RENDER'):
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Convert Render's 'postgres://' to 'postgresql+psycopg://' so psycopg3 is used
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        raise ValueError("DATABASE_URL environment variable not set on Render")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temple.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Upload folder configuration
if os.environ.get('RENDER'):
    UPLOAD_DIR = '/opt/render/project/src/persistent/uploads'
else:
    UPLOAD_DIR = 'static/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'user_login'
login_manager.login_message = 'Please log in to access this page.'
# -------------------------------
# Database Models
# -------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user')  # 'admin', 'user', 'darshan_manager'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    bookings = db.relationship('PrasadBooking', backref='user', lazy=True)
    donations = db.relationship('Donation', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'


class PrasadBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    prasad_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    booking_date = db.Column(db.Date, nullable=False)
    special_requests = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(100))
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    anonymous = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class GalleryImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    filename = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_featured = db.Column(db.Boolean, default=False)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    about_visible = db.Column(db.Boolean, default=True)
    prasad_visible = db.Column(db.Boolean, default=True)
    donation_visible = db.Column(db.Boolean, default=True)
    gallery_visible = db.Column(db.Boolean, default=True)
    contact_visible = db.Column(db.Boolean, default=True)
    phone_primary = db.Column(db.String(20), default='+91 98765 43210')
    phone_secondary = db.Column(db.String(20), default='')
    email_primary = db.Column(db.String(120), default='contact@tatkalikhanuman.org')
    email_secondary = db.Column(db.String(120), default='')
    address_line1 = db.Column(db.String(200), default='Hanuman Gali')
    address_line2 = db.Column(db.String(200), default='Ayodhya Nagar')
    city = db.Column(db.String(100), default='Delhi')
    state = db.Column(db.String(100), default='Delhi')
    pincode = db.Column(db.String(10), default='110001')
    google_maps_embed = db.Column(db.Text, default='')
    upi_id = db.Column(db.String(100), default='temple@ybl')
    upi_qr_filename = db.Column(db.String(200), default='')
    bank_name = db.Column(db.String(100), default='State Bank of India')
    bank_account_name = db.Column(db.String(200), default='Shree Tatkalik Hanuman Trust')
    bank_account_number = db.Column(db.String(50), default='123456789012')
    bank_ifsc = db.Column(db.String(20), default='SBIN0001234')
    bank_branch = db.Column(db.String(100), default='Main Branch')
    facebook_url = db.Column(db.String(200), default='#')
    instagram_url = db.Column(db.String(200), default='#')
    youtube_url = db.Column(db.String(200), default='#')
    twitter_url = db.Column(db.String(200), default='')
    morning_open = db.Column(db.String(10), default='06:00')
    morning_close = db.Column(db.String(10), default='12:00')
    evening_open = db.Column(db.String(10), default='16:00')
    evening_close = db.Column(db.String(10), default='21:00')
    mangala_aarti = db.Column(db.String(10), default='06:30')
    bhog_aarti = db.Column(db.String(10), default='12:30')
    sandhya_aarti = db.Column(db.String(10), default='19:00')
    shayan_aarti = db.Column(db.String(10), default='21:00')
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @staticmethod
    def get_settings():
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return settings


class DailyDarshan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    media_type = db.Column(db.String(10), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def get_today_darshan():
        today = datetime.now(timezone.utc).date()
        return DailyDarshan.query.filter_by(date=today).first()


# -------------------------------
# Flask-Login User Loader
# -------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------------------
# Decorators
# -------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def darshan_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('user_login'))
        if current_user.role not in ['admin', 'darshan_manager']:
            flash('Access restricted to Darshan Managers.', 'danger')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def page_visible(page_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            settings = SiteSettings.get_settings()
            if not getattr(settings, f'{page_name}_visible', True):
                flash('This page is currently unavailable.', 'warning')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# -------------------------------
# Context Processors
# -------------------------------
@app.context_processor
def inject_globals():
    try:
        settings = SiteSettings.get_settings()
    except:
        settings = None
    return {
        'settings': settings,
        'get_today_darshan': DailyDarshan.get_today_darshan,
        'now': lambda: datetime.now(timezone.utc)
    }


# -------------------------------
# Public Routes (User Side)
# -------------------------------
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
@page_visible('about')
def about():
    return render_template('about.html')


@app.route('/prasad-booking', methods=['GET', 'POST'])
@login_required
@page_visible('prasad')
def prasad_booking():
    if request.method == 'POST':
        try:
            booking = PrasadBooking(
                user_id=current_user.id,
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form['phone'],
                prasad_type=request.form['prasad_type'],
                quantity=int(request.form['quantity']),
                booking_date=datetime.strptime(request.form['booking_date'], '%Y-%m-%d').date(),
                special_requests=request.form.get('special_requests', '')
            )
            db.session.add(booking)
            db.session.commit()
            flash('Your prasad booking request has been submitted successfully!', 'success')
            return redirect(url_for('prasad_booking'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'danger')
    return render_template('prasad_booking.html')


@app.route('/donation', methods=['GET', 'POST'])
@login_required
@page_visible('donation')
def donation():
    if request.method == 'POST':
        try:
            donation = Donation(
                user_id=current_user.id,
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form['phone'],
                amount=float(request.form['amount']),
                purpose=request.form.get('purpose', 'General Donation'),
                payment_method=request.form['payment_method'],
                transaction_id=request.form.get('transaction_id', ''),
                anonymous=bool(request.form.get('anonymous')),
                message=request.form.get('message', '')
            )
            db.session.add(donation)
            db.session.commit()
            flash('Thank you for your generous donation!', 'success')
            return redirect(url_for('donation'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'danger')
    return render_template('donation.html')


@app.route('/gallery')
@page_visible('gallery')
def gallery():
    images = GalleryImage.query.order_by(GalleryImage.uploaded_at.desc()).all()
    return render_template('gallery.html', images=images)


@app.route('/contact', methods=['GET', 'POST'])
@page_visible('contact')
def contact():
    if request.method == 'POST':
        try:
            message = ContactMessage(
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form.get('phone', ''),
                subject=request.form['subject'],
                message=request.form['message']
            )
            db.session.add(message)
            db.session.commit()
            flash('Your message has been sent. We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'danger')
    return render_template('contact.html')


# -------------------------------
# User Authentication Routes
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'darshan_manager':
            return redirect(url_for('admin_daily_darshan'))
        else:
            return redirect(url_for('user_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form.get('full_name', '')
        phone = request.form.get('phone', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email, full_name=full_name, phone=phone, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('user_login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'darshan_manager':
            return redirect(url_for('admin_daily_darshan'))
        else:
            return redirect(url_for('user_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            if user.role == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            elif user.role == 'darshan_manager':
                return redirect(next_page or url_for('admin_daily_darshan'))
            else:
                return redirect(next_page or url_for('user_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'darshan_manager':
        return redirect(url_for('admin_daily_darshan'))
    bookings = PrasadBooking.query.filter_by(user_id=current_user.id).order_by(PrasadBooking.created_at.desc()).all()
    donations = Donation.query.filter_by(user_id=current_user.id).order_by(Donation.created_at.desc()).all()
    return render_template('user_dashboard.html', bookings=bookings, donations=donations)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', '')
        current_user.phone = request.form.get('phone', '')
        if request.form.get('new_password'):
            if request.form['new_password'] == request.form['confirm_new_password']:
                current_user.set_password(request.form['new_password'])
                flash('Password updated successfully.', 'success')
            else:
                flash('Passwords do not match.', 'danger')
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')


# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# -------------------------------
# Admin Routes
# -------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role == 'darshan_manager':
        return redirect(url_for('admin_daily_darshan'))
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('user_dashboard'))
    context = {
        'bookings_count': PrasadBooking.query.count(),
        'donations_count': Donation.query.count(),
        'donations_total': db.session.query(db.func.sum(Donation.amount)).filter(Donation.status=='completed').scalar() or 0,
        'gallery_count': GalleryImage.query.count(),
        'messages_count': ContactMessage.query.filter_by(is_read=False).count(),
        'recent_bookings': PrasadBooking.query.order_by(PrasadBooking.created_at.desc()).limit(5).all(),
        'recent_donations': Donation.query.order_by(Donation.created_at.desc()).limit(5).all(),
        'recent_messages': ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()
    }
    return render_template('admin/dashboard.html', **context)


@app.route('/admin/donation-chart-data')
@login_required
@admin_required
def donation_chart_data():
    today = datetime.now(timezone.utc).date()
    data = []
    labels = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        total = db.session.query(db.func.sum(Donation.amount)).filter(
            db.func.date(Donation.created_at) == date,
            Donation.status == 'completed'
        ).scalar() or 0
        labels.append(date.strftime('%a'))
        data.append(float(total))
    return {'labels': labels, 'data': data}


@app.route('/admin/gallery')
@login_required
@admin_required
def admin_gallery():
    images = GalleryImage.query.order_by(GalleryImage.uploaded_at.desc()).all()
    return render_template('admin/gallery.html', images=images)


@app.route('/admin/gallery/upload', methods=['POST'])
@login_required
@admin_required
def admin_gallery_upload():
    if 'image' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('admin_gallery'))
    file = request.files['image']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('admin_gallery'))
    if file:
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image = GalleryImage(
            title=request.form.get('title', ''),
            description=request.form.get('description', ''),
            filename=filename,
            category=request.form.get('category', 'temple'),
            is_featured=bool(request.form.get('is_featured'))
        )
        db.session.add(image)
        db.session.commit()
        flash('Image uploaded successfully!', 'success')
    return redirect(url_for('admin_gallery'))


@app.route('/admin/gallery/delete/<int:id>')
@login_required
@admin_required
def admin_gallery_delete(id):
    image = GalleryImage.query.get_or_404(id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
    except:
        pass
    db.session.delete(image)
    db.session.commit()
    flash('Image deleted.', 'success')
    return redirect(url_for('admin_gallery'))


@app.route('/admin/bookings')
@login_required
@admin_required
def admin_bookings():
    bookings = PrasadBooking.query.order_by(PrasadBooking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)


@app.route('/admin/bookings/update/<int:id>/<status>')
@login_required
@admin_required
def admin_booking_update(id, status):
    booking = PrasadBooking.query.get_or_404(id)
    booking.status = status
    db.session.commit()
    flash(f'Booking status updated to {status}.', 'success')
    return redirect(url_for('admin_bookings'))


@app.route('/admin/donations')
@login_required
@admin_required
def admin_donations():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    total = db.session.query(db.func.sum(Donation.amount)).filter(Donation.status=='completed').scalar() or 0
    return render_template('admin/donations.html', donations=donations, total=total)


@app.route('/admin/donations/update/<int:id>/<status>')
@login_required
@admin_required
def admin_donation_update(id, status):
    donation = Donation.query.get_or_404(id)
    donation.status = status
    db.session.commit()
    flash(f'Donation status updated to {status}.', 'success')
    return redirect(url_for('admin_donations'))


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users/add', methods=['POST'])
@login_required
@admin_required
def admin_user_add():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form.get('role', 'user')
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
        return redirect(url_for('admin_users'))
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'danger')
        return redirect(url_for('admin_users'))
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash('User created successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:id>')
@login_required
@admin_required
def admin_user_delete(id):
    if id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/contacts')
@login_required
@admin_required
def admin_contacts():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/contacts.html', messages=messages)


@app.route('/admin/contacts/mark-read/<int:id>')
@login_required
@admin_required
def admin_contact_mark_read(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('admin_contacts'))


@app.route('/admin/contacts/delete/<int:id>')
@login_required
@admin_required
def admin_contact_delete(id):
    msg = ContactMessage.query.get_or_404(id)
    db.session.delete(msg)
    db.session.commit()
    flash('Message deleted.', 'success')
    return redirect(url_for('admin_contacts'))


@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        settings.about_visible = bool(request.form.get('about_visible'))
        settings.prasad_visible = bool(request.form.get('prasad_visible'))
        settings.donation_visible = bool(request.form.get('donation_visible'))
        settings.gallery_visible = bool(request.form.get('gallery_visible'))
        settings.contact_visible = bool(request.form.get('contact_visible'))
        settings.phone_primary = request.form.get('phone_primary', '')
        settings.phone_secondary = request.form.get('phone_secondary', '')
        settings.email_primary = request.form.get('email_primary', '')
        settings.email_secondary = request.form.get('email_secondary', '')
        settings.address_line1 = request.form.get('address_line1', '')
        settings.address_line2 = request.form.get('address_line2', '')
        settings.city = request.form.get('city', '')
        settings.state = request.form.get('state', '')
        settings.pincode = request.form.get('pincode', '')
        settings.google_maps_embed = request.form.get('google_maps_embed', '')
        settings.upi_id = request.form.get('upi_id', '')
        settings.bank_name = request.form.get('bank_name', '')
        settings.bank_account_name = request.form.get('bank_account_name', '')
        settings.bank_account_number = request.form.get('bank_account_number', '')
        settings.bank_ifsc = request.form.get('bank_ifsc', '')
        settings.bank_branch = request.form.get('bank_branch', '')
        settings.facebook_url = request.form.get('facebook_url', '#')
        settings.instagram_url = request.form.get('instagram_url', '#')
        settings.youtube_url = request.form.get('youtube_url', '#')
        settings.twitter_url = request.form.get('twitter_url', '')
        settings.morning_open = request.form.get('morning_open', '06:00')
        settings.morning_close = request.form.get('morning_close', '12:00')
        settings.evening_open = request.form.get('evening_open', '16:00')
        settings.evening_close = request.form.get('evening_close', '21:00')
        settings.mangala_aarti = request.form.get('mangala_aarti', '06:30')
        settings.bhog_aarti = request.form.get('bhog_aarti', '12:30')
        settings.sandhya_aarti = request.form.get('sandhya_aarti', '19:00')
        settings.shayan_aarti = request.form.get('shayan_aarti', '21:00')
        if 'upi_qr' in request.files:
            file = request.files['upi_qr']
            if file and file.filename:
                filename = secure_filename(file.filename)
                name, ext = os.path.splitext(filename)
                filename = f"upi_qr_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                if settings.upi_qr_filename:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], settings.upi_qr_filename))
                    except:
                        pass
                settings.upi_qr_filename = filename
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('admin/settings.html', settings=settings)


@app.route('/admin/daily-darshan', methods=['GET', 'POST'])
@login_required
@darshan_manager_required
def admin_daily_darshan():
    if request.method == 'POST':
        media_type = request.form['media_type']
        caption = request.form.get('caption', '')
        if 'media_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(url_for('admin_daily_darshan'))
        file = request.files['media_file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('admin_daily_darshan'))
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm', 'mov'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            flash('Invalid file type. Allowed: jpg, png, gif, mp4, webm, mov', 'danger')
            return redirect(url_for('admin_daily_darshan'))
        today = datetime.now(timezone.utc).date()
        existing = DailyDarshan.query.filter_by(date=today).first()
        if existing:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], existing.filename))
            except:
                pass
            db.session.delete(existing)
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"darshan_{today.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        darshan = DailyDarshan(date=today, media_type=media_type, filename=filename, caption=caption)
        db.session.add(darshan)
        db.session.commit()
        flash('Daily Darshan uploaded successfully!', 'success')
        return redirect(url_for('admin_daily_darshan'))
    today_darshan = DailyDarshan.get_today_darshan()
    return render_template('admin/daily_darshan.html', darshan=today_darshan)


@app.route('/admin/daily-darshan/delete/<int:id>')
@login_required
@darshan_manager_required
def admin_daily_darshan_delete(id):
    darshan = DailyDarshan.query.get_or_404(id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], darshan.filename))
    except:
        pass
    db.session.delete(darshan)
    db.session.commit()
    flash('Daily Darshan deleted.', 'success')
    return redirect(url_for('admin_daily_darshan'))


# -------------------------------
# Create default admin user if not exists
# -------------------------------
def create_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='Hanuman', email='tatkalikhanumantemple@gmail.com', role='admin', full_name='Administrator')
            admin.set_password('_Hanuman@440_')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: username='admin', password='admin123'")


if __name__ == '__main__':
    create_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)