from flask import Flask, redirect, url_for, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import sys
from werkzeug.exceptions import NotFound, BadRequest, TooManyRequests
import re

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Configure logging
def setup_logging():
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

# Ensure the database exists
ensure_database_exists()

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define Question model
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    nickname = db.Column(db.String(100), nullable=False, default='anon')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    answer = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'nickname': self.nickname,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'answer': self.answer,
            'answered_at': self.answered_at.strftime('%Y-%m-%d %H:%M:%S') if self.answered_at else None
        }

# Create database tables
def setup_database_tables():
    app.logger.info("Setting up database tables")
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {str(e)}", exc_info=True)
            raise

# Initialize database tables
setup_database_tables()

@app.route("/")
def index():
    username = "John" 
    intro = """Hi there! I'm John, and this is my personal Q&A site. I've created this space to interact with friends, colleagues, and anyone interested in connecting.

Feel free to ask me anything you're curious about - whether it's about my work, hobbies, opinions, or just something you'd like my perspective on. I'll do my best to answer your questions!
"""
    try:
        # Get page number from query parameters, default to 1
        page = request.args.get('page', 1, type=int)
        
        # Validate page number
        if page < 1:
            app.logger.warning(f"Invalid page number requested: {page}")
            return redirect(url_for('index', page=1))
            
        per_page = 10
        
        app.logger.debug(f"Fetching questions for page {page} with {per_page} per page")
        
        # Get questions with pagination
        questions_pagination = Question.query.order_by(Question.created_at.desc()).paginate(
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
            pagination=questions_pagination
        )
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return render_template('500.html'), 500

@app.route("/submit-question", methods=["POST"])
def submit_question():
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
            
        # Create new question
        new_question = Question(content=question_content, nickname=nickname)
        
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

# Error handlers
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

if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Get host from environment variable or default to 127.0.0.1
    host = os.environ.get('HOST', '127.0.0.1')
    
    app.logger.info(f"Starting application on {host}:{port}")
    app.run(host=host, port=port, debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true')