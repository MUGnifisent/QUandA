from flask import Flask, redirect, url_for, render_template, request, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import sys
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import NotFound, BadRequest, TooManyRequests
import re
from functools import wraps

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Set a secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_change_in_production')

###################
# LOGGING SETUP
###################

def setup_logging():
    """Configure application logging"""
    # Set log level from environment variable or default to INFO
    log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Configure Flask app logger
    app.logger.setLevel(log_level)
    
    if not app.logger.handlers:
        # Add console handler if no handlers exist
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
        
        # Log to file if LOG_FILE environment variable is set
        log_file = os.environ.get('LOG_FILE')
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            app.logger.addHandler(file_handler)
            app.logger.info(f"Logging to file: {log_file}")

    app.logger.info(f"Logging initialized with level: {log_level_name}")

# Call setup_logging right away
setup_logging()

###################
# DATABASE SETUP
###################

# Database configuration from environment variables
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'quanda')

# Construct SQLAlchemy connection string using components
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

app.logger.info(f"Database configuration: Host={DB_HOST}, Port={DB_PORT}, DB={DB_NAME}")

# Create and ensure the database exists
def ensure_database_exists():
    """Check if database exists and create it if it doesn't"""
    app.logger.info(f"Ensuring database '{DB_NAME}' exists")
    
    try:
        # Try connecting to the postgres database first
        app.logger.debug("Connecting to 'postgres' database to check if target database exists")
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Check if our database exists
        cursor = conn.cursor()
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            app.logger.info(f"Database '{DB_NAME}' does not exist, creating...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            app.logger.info(f"Database '{DB_NAME}' created successfully")
        else:
            app.logger.info(f"Database '{DB_NAME}' already exists")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        raise

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

###################
# MODELS
###################

class Question(db.Model):
    """Question model for storing user questions and admin answers"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    nickname = db.Column(db.String(100), nullable=False, default='anon')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    answer = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)
    is_approved = db.Column(db.Boolean, nullable=False, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'nickname': self.nickname,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'answer': self.answer,
            'answered_at': self.answered_at.strftime('%Y-%m-%d %H:%M:%S') if self.answered_at else None,
            'is_approved': self.is_approved
        }

class Admin(db.Model):
    """Admin model for user authentication and profile information"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    introduction = db.Column(db.Text, nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'introduction': self.introduction
        }

class Setting(db.Model):
    """Setting model for storing site-wide configuration"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.String(200), nullable=False)
    
    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
        
    @classmethod
    def set(cls, key, value):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

###################
# DATABASE INIT
###################

def setup_database_tables():
    """Create all database tables if they don't exist"""
    app.logger.info("Setting up database tables")
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {str(e)}", exc_info=True)
            raise

def initialize_admin():
    """Initialize the admin user if it doesn't exist"""
    app.logger.info("Checking for admin user")
    with app.app_context():
        try:
            admin = Admin.query.filter_by(username='admin').first()
            if not admin:
                app.logger.info("Creating default admin user")
                admin = Admin(
                    username='admin',
                    display_name='John Quanda',
                    introduction="Hi there! I'm John Quanda, and this is my personal Q&A site. I've created this space to interact with friends, colleagues, and anyone interested in connecting.\n\nFeel free to ask me anything you're curious about - whether it's about my work, hobbies, opinions, or just something you'd like my perspective on. I'll do my best to answer your questions!"
                )
                admin.set_password('admin')
                db.session.add(admin)
                
                # Set default moderation setting
                moderation = Setting(key='moderation_enabled', value='false')
                db.session.add(moderation)
                
                db.session.commit()
                app.logger.info("Default admin user created")
            else:
                app.logger.info("Admin user already exists")
        except Exception as e:
            app.logger.error(f"Error initializing admin user: {str(e)}", exc_info=True)
            raise

# Initialize database
ensure_database_exists()
setup_database_tables()
initialize_admin()

###################
# DECORATORS
###################

def admin_required(f):
    """Decorator to require admin login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

###################
# PUBLIC ROUTES
###################

@app.route("/")
def index():
    """Homepage showing introduction and paginated questions"""
    try:
        # Get admin info
        admin = Admin.query.first()
        username = admin.display_name if admin else "John"
        intro = admin.introduction if admin else """Hi there! I'm John, and this is my personal Q&A site. I've created this space to interact with friends, colleagues, and anyone interested in connecting.\n\nFeel free to ask me anything you're curious about - whether it's about my work, hobbies, opinions, or just something you'd like my perspective on. I'll do my best to answer your questions!"""
        
        # Get page number from query parameters, default to 1
        page = request.args.get('page', 1, type=int)
        
        # Validate page number
        if page < 1:
            app.logger.warning(f"Invalid page number requested: {page}")
            return redirect(url_for('index', page=1))
            
        per_page = 10
        
        app.logger.debug(f"Fetching questions for page {page} with {per_page} per page")
        
        # Check if moderation is enabled
        moderation_enabled = Setting.get('moderation_enabled', 'false') == 'true'
        
        # Get questions with pagination, filtered if moderation is enabled
        query = Question.query
        if moderation_enabled:
            query = query.filter_by(is_approved=True)
            
        questions_pagination = query.order_by(Question.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # If page exceeds max pages, redirect to last page
        if page > 1 and not questions_pagination.items:
            last_page = max(1, questions_pagination.pages)
            app.logger.warning(f"Page {page} requested but only {last_page} pages exist")
            return redirect(url_for('index', page=last_page))
        
        app.logger.debug(f"Found {len(questions_pagination.items)} questions for page {page}")
        
        return render_template(
            'index.html', 
            user=username, 
            introduction=intro,
            questions=questions_pagination.items,
            pagination=questions_pagination,
            admin_name=username
        )
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return render_template('500.html'), 500

@app.route("/submit-question", methods=["POST"])
def submit_question():
    """Handle new question submissions"""
    try:
        # Get form data
        question_content = request.form.get('question', '').strip()
        nickname = request.form.get('nickname', 'anon').strip()
        
        # Input validation
        if not question_content:
            app.logger.warning("Attempted to submit empty question")
            return redirect(url_for('index'))
        
        # Basic content limits to prevent abuse
        if len(question_content) > 2000:
            app.logger.warning(f"Question too long ({len(question_content)} chars) from {request.remote_addr}")
            return render_template('error.html', 
                                  error_title="Question Too Long", 
                                  error_message="Your question exceeds the maximum length. Please keep questions under 2000 characters."), 400
        
        # Sanitize nickname (prevent HTML/JS injection)
        nickname = re.sub(r'[<>\'";]', '', nickname)[:50]  # Limit nickname length
        if not nickname:
            nickname = 'anon'
        
        app.logger.info(f"New question from '{nickname}': {question_content[:30]}...")
        
        # Check if moderation is enabled
        moderation_enabled = Setting.get('moderation_enabled', 'false') == 'true'
        is_approved = not moderation_enabled
            
        # Create new question
        new_question = Question(
            content=question_content, 
            nickname=nickname,
            is_approved=is_approved
        )
        
        try:
            # Add to database
            db.session.add(new_question)
            db.session.commit()
            app.logger.info(f"Question saved with ID: {new_question.id}")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving question: {str(e)}", exc_info=True)
            return render_template('500.html'), 500
        
        # Redirect back to home page
        return redirect(url_for('index'))
    
    except Exception as e:
        app.logger.error(f"Unexpected error in submit_question: {str(e)}", exc_info=True)
        return render_template('500.html'), 500

###################
# ADMIN ROUTES
###################

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page"""
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            session['admin_id'] = admin.id
            app.logger.info(f"Admin login successful: {username}")
            return redirect(url_for('admin_dashboard'))
        else:
            app.logger.warning(f"Failed admin login attempt: {username}")
            return render_template('admin_login.html', error="Invalid credentials")
    
    return render_template('admin_login.html')

@app.route("/admin/logout")
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    return redirect(url_for('index'))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin dashboard showing overview and quick actions"""
    admin = Admin.query.get(session['admin_id'])
    
    # Get settings
    moderation_enabled = Setting.get('moderation_enabled', 'false') == 'true'
    
    # Get pending questions count
    pending_count = 0
    if moderation_enabled:
        pending_count = Question.query.filter_by(is_approved=False).count()
    
    # Get unanswered questions count
    unanswered_count = Question.query.filter_by(answer=None).count()
    
    # Get total questions count
    total_count = Question.query.count()
    
    return render_template(
        'admin/dashboard.html', 
        admin=admin,
        moderation_enabled=moderation_enabled,
        pending_count=pending_count,
        unanswered_count=unanswered_count,
        total_count=total_count,
        Question=Question  # Pass Question model for dashboard queries
    )

@app.route("/admin/profile", methods=["GET", "POST"])
@admin_required
def admin_profile():
    """Admin profile editing"""
    admin = Admin.query.get(session['admin_id'])
    
    if request.method == "POST":
        display_name = request.form.get('display_name', '').strip()
        introduction = request.form.get('introduction', '').strip()
        
        if display_name:
            admin.display_name = display_name
        
        if introduction:
            admin.introduction = introduction
            
        db.session.commit()
        app.logger.info(f"Admin profile updated: {admin.username}")
        return redirect(url_for('admin_profile'))
    
    return render_template('admin/profile.html', admin=admin)

@app.route("/admin/credentials", methods=["GET", "POST"])
@admin_required
def admin_credentials():
    """Admin credentials (username/password) editing"""
    admin = Admin.query.get(session['admin_id'])
    
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validate current password
        if not admin.check_password(current_password):
            return render_template('admin/credentials.html', admin=admin, error="Current password is incorrect")
        
        # Update username if provided
        if username and username != admin.username:
            # Check if username already exists
            existing = Admin.query.filter_by(username=username).first()
            if existing and existing.id != admin.id:
                return render_template('admin/credentials.html', admin=admin, error="Username already exists")
            
            admin.username = username
        
        # Update password if provided
        if new_password:
            if new_password != confirm_password:
                return render_template('admin/credentials.html', admin=admin, error="New passwords don't match")
            
            admin.set_password(new_password)
        
        db.session.commit()
        app.logger.info(f"Admin credentials updated: {admin.username}")
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/credentials.html', admin=admin)

@app.route("/admin/questions")
@admin_required
def admin_questions():
    """Admin questions list with filtering and pagination"""
    admin = Admin.query.get(session['admin_id'])  # Get admin object
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    filter_type = request.args.get('filter', 'all')
    
    # Build query based on filter
    query = Question.query
    
    if filter_type == 'unanswered':
        query = query.filter_by(answer=None)
    elif filter_type == 'answered':
        query = query.filter(Question.answer != None)
    elif filter_type == 'pending':
        query = query.filter_by(is_approved=False)
    
    # Get paginated questions
    questions_pagination = query.order_by(Question.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template(
        'admin/questions.html',
        admin=admin,  # Pass admin to template
        questions=questions_pagination.items,
        pagination=questions_pagination,
        filter_type=filter_type
    )

@app.route("/admin/question/<int:question_id>", methods=["GET", "POST"])
@admin_required
def admin_question_edit(question_id):
    """Admin edit/answer individual question"""
    admin = Admin.query.get(session['admin_id'])  # Get admin object
    question = Question.query.get_or_404(question_id)
    
    if request.method == "POST":
        action = request.form.get('action', '')
        
        if action == 'answer':
            answer_text = request.form.get('answer', '').strip()
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            db.session.commit()
            app.logger.info(f"Question {question_id} answered")
            
        elif action == 'edit':
            content = request.form.get('content', '').strip()
            nickname = request.form.get('nickname', '').strip()
            
            # Update fields
            question.content = content
            question.nickname = nickname
            db.session.commit()
            app.logger.info(f"Question {question_id} edited")
            
        elif action == 'delete':
            db.session.delete(question)
            db.session.commit()
            app.logger.info(f"Question {question_id} deleted")
            return redirect(url_for('admin_questions'))
            
        elif action == 'approve':
            question.is_approved = True
            db.session.commit()
            app.logger.info(f"Question {question_id} approved")
            
        elif action == 'reject':
            db.session.delete(question)
            db.session.commit()
            app.logger.info(f"Question {question_id} rejected and deleted")
            return redirect(url_for('admin_questions'))
    
    return render_template('admin/question_edit.html', question=question, admin=admin)  # Pass admin to template

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    """Admin site settings"""
    admin = Admin.query.get(session['admin_id'])  # Get admin object
    
    if request.method == "POST":
        moderation_enabled = request.form.get('moderation_enabled', 'false')
        
        # Update moderation setting
        Setting.set('moderation_enabled', moderation_enabled)
        app.logger.info(f"Moderation setting updated: {moderation_enabled}")
        
        return redirect(url_for('admin_settings'))
    
    # Get current settings
    moderation_enabled = Setting.get('moderation_enabled', 'false') == 'true'
    
    return render_template('admin/settings.html', moderation_enabled=moderation_enabled, admin=admin)  # Pass admin to template

@app.route("/admin/delete-all-questions", methods=["POST"])
@admin_required
def admin_delete_all_questions():
    """Delete all questions after confirmation"""
    confirmation = request.form.get('confirmation', '').strip()
    
    if confirmation == 'DELETE ALL QUESTIONS':
        try:
            # Delete all questions
            Question.query.delete()
            db.session.commit()
            app.logger.warning(f"All questions deleted by admin {session['admin_id']}")
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting all questions: {str(e)}", exc_info=True)
            return render_template('500.html'), 500
    else:
        return redirect(url_for('admin_settings'))

###################
# API ROUTES
###################

@app.route("/api/questions/<int:question_id>/approve", methods=["POST"])
@admin_required
def api_approve_question(question_id):
    """API endpoint to approve a question"""
    question = Question.query.get_or_404(question_id)
    question.is_approved = True
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/questions/<int:question_id>/delete", methods=["POST"])
@admin_required
def api_delete_question(question_id):
    """API endpoint to delete a question"""
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return jsonify({"success": True})

###################
# ERROR HANDLERS
###################

@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f"404 error: {request.path} - IP: {request.remote_addr}")
    return render_template('404.html', 
                          requested_path=request.path), 404

@app.errorhandler(400)
def bad_request(e):
    app.logger.warning(f"400 error: {request.path} - IP: {request.remote_addr}")
    return render_template('error.html', 
                          error_title="Bad Request", 
                          error_message="The server could not understand your request."), 400

@app.errorhandler(403)
def forbidden(e):
    app.logger.warning(f"403 error: {request.path} - IP: {request.remote_addr}")
    return render_template('error.html', 
                          error_title="Forbidden", 
                          error_message="You don't have permission to access this resource."), 403

@app.errorhandler(429)
def too_many_requests(e):
    app.logger.warning(f"429 error: Rate limit exceeded - IP: {request.remote_addr}")
    return render_template('error.html', 
                          error_title="Too Many Requests", 
                          error_message="You've made too many requests. Please try again later."), 429

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 error: {str(e)} - IP: {request.remote_addr}", exc_info=True)
    return render_template('500.html'), 500

# Catch-all route for undefined paths
@app.route('/<path:undefined_path>')
def undefined_route(undefined_path):
    app.logger.warning(f"Attempted to access undefined route: /{undefined_path} - IP: {request.remote_addr}")
    return render_template('404.html',
                          requested_path=f"/{undefined_path}"), 404

###################
# APP ENTRY POINT
###################

if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Get host from environment variable or default to 127.0.0.1
    host = os.environ.get('HOST', '127.0.0.1')
    
    app.logger.info(f"Starting application on {host}:{port}")
    app.run(host=host, port=port, debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true')