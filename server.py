import sys
import os
import json
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Import bottle
try:
    from bottle import route, run, request, response, post, options
except ImportError as e:
    import traceback
    traceback.print_exc()
    print(f"Import error: {e}")
    print("Bottle framework is not installed. Please run: pip install bottle")
    sys.exit(1)

# Configuration
GMAIL_USER = 'vortexcoder433@gmail.com'
GMAIL_PASS = 'yqqmkumgqdgvtcgt' # Google App Password
DB_FILE = 'users.json'

# In-memory storage for unverified registration requests
# Format: { email: { 'username': u, 'password': p, 'code': c, 'expires': t } }
pending_verifications = {}

# CORS Helper
def enable_cors(fn):
    def wrapper(*args, **kwargs):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
        if request.method == 'OPTIONS':
            return
        return fn(*args, **kwargs)
    return wrapper

def send_verification_email(to_email, code, username):
    """Sends a verification email with the 6-digit OTP code using Gmail SMTP"""
    subject = "VortexCoder System - Verification Code"
    body = f"""Hello, {username}!

Welcome to the VortexCoder operator directory.
Your 6-digit authentication key code is:

👉  {code}  👈

This code is valid for 10 minutes. Please enter it on the website to confirm your uplink.

Best regards,
VortexCoder System Security
"""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = to_email

    try:
        # Connect to Gmail SMTP SSL server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, [to_email], msg.as_string())
        server.quit()
        print(f"SMTP: Successfully sent verification code to {to_email}")
        return True
    except Exception as e:
        print(f"SMTP Error: Failed to send email to {to_email}. Error: {e}")
        return False

def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_user(username, email, password):
    users = load_users()
    users[email] = {
        'username': username,
        'password': password,  # In production, use hashing like bcrypt!
        'created_at': datetime.now().isoformat()
    }
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)

@options('/api/register')
@options('/api/verify')
@options('/api/login')
@enable_cors
def setup_options():
    return {}

@post('/api/register')
@enable_cors
def register():
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            response.status = 400
            return {'success': False, 'message': 'Missing fields'}

        # Check if user already exists
        users = load_users()
        if email in users:
            response.status = 400
            return {'success': False, 'message': 'User already registered'}

        # Generate a 6-digit random code
        code = f"{random.randint(100000, 999999)}"
        expires = datetime.now() + timedelta(minutes=10)

        # Store in memory
        pending_verifications[email] = {
            'username': username,
            'password': password,
            'code': code,
            'expires': expires
        }

        # Send email
        email_sent = send_verification_email(email, code, username)
        if not email_sent:
            response.status = 500
            return {'success': False, 'message': 'Failed to send verification email'}

        return {'success': True, 'message': 'Verification code sent to your email'}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

@post('/api/verify')
@enable_cors
def verify():
    try:
        data = request.json
        email = data.get('email')
        code = data.get('code')

        if not email or not code:
            response.status = 400
            return {'success': False, 'message': 'Missing email or code'}

        pending = pending_verifications.get(email)
        if not pending:
            response.status = 404
            return {'success': False, 'message': 'Verification request not found'}

        # Check expiration
        if datetime.now() > pending['expires']:
            pending_verifications.pop(email, None)
            response.status = 400
            return {'success': False, 'message': 'Code has expired. Please sign up again'}

        # Compare codes
        if pending['code'] != code:
            response.status = 400
            return {'success': False, 'message': 'Invalid verification code'}

        # Register user into database
        save_user(pending['username'], email, pending['password'])
        
        # Clear pending
        pending_verifications.pop(email, None)
        return {'success': True, 'message': 'Verification successful. Account created'}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

@post('/api/login')
@enable_cors
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            response.status = 400
            return {'success': False, 'message': 'Missing email or password'}

        users = load_users()
        user = users.get(email)
        if not user or user['password'] != password:
            response.status = 401
            return {'success': False, 'message': 'Invalid email or password'}

        return {'success': True, 'username': user['username'], 'message': 'Login successful'}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

if __name__ == '__main__':
    print("*" * 50)
    print(" VortexCoder Authentication Server is running!")
    print(" Running over Bottle Web Server...")
    print("*" * 50)
    port = int(os.environ.get('PORT', 5000))
    run(host='0.0.0.0', port=port)
