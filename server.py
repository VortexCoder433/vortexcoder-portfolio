import sys
import os
import json
from datetime import datetime
from email.mime.text import MIMEText

# Import bottle
try:
    from bottle import route, run, request, response, post, hook, HTTPResponse
except ImportError:
    print("Bottle framework is not installed. Please run: pip install bottle")
    sys.exit(1)

# Configuration
DB_USERS = 'users.json'
DB_STATS = 'stats.json'
ADMIN_USER = 'admin'
ADMIN_PASS = 'VortexAdmin2026'

# CORS Headers Configuration
@hook('before_request')
def handle_options():
    if request.method == 'OPTIONS':
        origin = request.get_header('Origin') or '*'
        headers = {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token',
            'Access-Control-Allow-Credentials': 'true'
        }
        raise HTTPResponse(headers=headers)

@hook('after_request')
def enable_cors():
    origin = request.get_header('Origin') or '*'
    response.set_header('Access-Control-Allow-Origin', origin)
    response.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.set_header('Access-Control-Allow-Headers', 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token')
    response.set_header('Access-Control-Allow-Credentials', 'true')

# Database Helper Functions
def load_users():
    if not os.path.exists(DB_USERS):
        users = {
            'guest': {
                'password': 'password',
                'registeredAt': '24.05.2026 12:00:00',
                'serialNumber': 1,
                'downloads': 3
            }
        }
        save_users(users)
        return users
    try:
        with open(DB_USERS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(DB_USERS, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)

def load_stats():
    if not os.path.exists(DB_STATS):
        stats = {
            'visits_count': 0,
            'visits': []
        }
        save_stats(stats)
        return stats
    try:
        with open(DB_STATS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'visits_count': 0, 'visits': []}

def save_stats(stats):
    with open(DB_STATS, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4)

# Admin Auth Check
def is_admin_logged_in():
    return request.get_cookie('admin_session') == 'active_operator_authorized'

# ----------------- Operator API Routes -----------------

@post('/api/register')
def register():
    try:
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            response.status = 400
            return {'success': False, 'message': 'Missing Callsign or Passkey'}

        users = load_users()
        if username in users:
            response.status = 400
            return {'success': False, 'message': 'Callsign already claimed'}

        # Create new user
        users[username] = {
            'password': password,
            'registeredAt': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'serialNumber': len(users) + 1,
            'downloads': 0
        }
        save_users(users)
        return {'success': True, 'message': 'Credentials generated successfully'}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

@post('/api/login')
def login():
    try:
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            response.status = 400
            return {'success': False, 'message': 'Missing Callsign or Passkey'}

        users = load_users()
        user = users.get(username)

        # Handle legacy user formats or objects
        is_valid = False
        if user:
            if isinstance(user, str):
                is_valid = (user == password)
            else:
                is_valid = (user.get('password') == password)

        if is_valid:
            # Upgrade legacy string entry to object if needed
            if isinstance(user, str):
                users[username] = {
                    'password': password,
                    'registeredAt': '24.05.2026 12:00:00',
                    'serialNumber': list(users.keys()).index(username) + 1,
                    'downloads': 0
                }
                save_users(users)
                user = users[username]

            return {
                'success': True,
                'username': username,
                'serialNumber': user.get('serialNumber', 1),
                'registeredAt': user.get('registeredAt', '-'),
                'downloads': user.get('downloads', 0)
            }

        response.status = 401
        return {'success': False, 'message': 'Invalid signature or passkey'}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

@post('/api/download')
def download():
    try:
        data = request.json or {}
        username = data.get('username', '').strip()

        if not username:
            response.status = 400
            return {'success': False, 'message': 'Missing Callsign'}

        users = load_users()
        if username in users:
            # Upgrade legacy user structure if needed
            if isinstance(users[username], str):
                users[username] = {
                    'password': users[username],
                    'registeredAt': '24.05.2026 12:00:00',
                    'serialNumber': list(users.keys()).index(username) + 1,
                    'downloads': 0
                }
            
            users[username]['downloads'] = users[username].get('downloads', 0) + 1
            save_users(users)
            return {'success': True, 'downloads': users[username]['downloads']}

        response.status = 404
        return {'success': False, 'message': 'Operator not found'}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

@post('/api/telemetry')
def telemetry():
    try:
        data = request.json or {}
        stats = load_stats()
        stats['visits_count'] = stats.get('visits_count', 0) + 1

        visit = {
            'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'device': data.get('device', 'Unknown'),
            'os': data.get('os', 'Unknown'),
            'browser': data.get('browser', 'Unknown'),
            'resolution': data.get('resolution', 'Unknown'),
            'referrer': data.get('referrer', 'Direct')
        }
        # Keep last 1000 logs only to conserve file space
        stats['visits'] = [visit] + stats.get('visits', [])[:999]
        save_stats(stats)
        return {'success': True}
    except Exception as e:
        response.status = 500
        return {'success': False, 'message': f'Server error: {e}'}

# ----------------- Admin API Routes -----------------

@post('/api/admin/login')
def admin_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if username == ADMIN_USER and password == ADMIN_PASS:
        response.set_cookie('admin_session', 'active_operator_authorized', path='/', max_age=86400, httponly=True)
        return {'success': True}
    response.status = 401
    return {'success': False, 'message': 'Access credentials denied'}

@post('/api/admin/logout')
def admin_logout():
    response.set_cookie('admin_session', '', path='/', max_age=0)
    return {'success': True}

@route('/api/admin/stats')
def admin_stats():
    if not is_admin_logged_in():
        response.status = 403
        return {'success': False, 'message': 'Access Denied'}

    users = load_users()
    stats = load_stats()

    devices = {}
    os_map = {}
    browsers = {}

    for v in stats.get('visits', []):
        d = v.get('device', 'Unknown')
        o = v.get('os', 'Unknown')
        b = v.get('browser', 'Unknown')

        devices[d] = devices.get(d, 0) + 1
        os_map[o] = os_map.get(o, 0) + 1
        browsers[b] = browsers.get(b, 0) + 1

    user_list = []
    for name, data in users.items():
        user_list.append({
            'username': name,
            'registeredAt': data.get('registeredAt') if isinstance(data, dict) else '24.05.2026 12:00:00',
            'serialNumber': data.get('serialNumber') if isinstance(data, dict) else 1,
            'downloads': data.get('downloads', 0) if isinstance(data, dict) else 0
        })

    user_list.sort(key=lambda x: x.get('serialNumber', 999))

    return {
        'visits_count': stats.get('visits_count', 0),
        'users': user_list,
        'devices': devices,
        'os': os_map,
        'browsers': browsers,
        'visits': stats.get('visits', [])[:100]
    }

@post('/api/admin/delete_user')
def admin_delete_user():
    if not is_admin_logged_in():
        response.status = 403
        return {'success': False, 'message': 'Access Denied'}

    data = request.json or {}
    username = data.get('username', '').strip()

    if not username or username == 'guest':
        response.status = 400
        return {'success': False, 'message': 'Cannot delete guest or missing username'}

    users = load_users()
    if username in users:
        users.pop(username)
        save_users(users)
        return {'success': True}

    response.status = 404
    return {'success': False, 'message': 'User not found'}

# ----------------- Admin Panel HTML Rendering -----------------

def serve_login():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VortexCoder Admin Console | Sign In</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0813;
            --border-color: rgba(255, 255, 255, 0.08);
            --neon-violet: #a855f7;
            --neon-cyan: #06b6d4;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: relative;
        }
        body::after {
            content: '';
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%);
            background-size: 100% 4px;
            z-index: 10;
            pointer-events: none;
            opacity: 0.15;
        }
        .login-card {
            background: rgba(18, 18, 26, 0.55);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 3rem 2rem;
            width: 380px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 30px rgba(168, 85, 247, 0.1);
            z-index: 5;
        }
        .title {
            font-family: 'Share Tech Mono', monospace;
            font-size: 1.1rem;
            color: var(--neon-cyan);
            letter-spacing: 2px;
            text-align: center;
            margin-bottom: 2rem;
            text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
        }
        .form-group {
            margin-bottom: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        label {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        input {
            background-color: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 0.75rem 1rem;
            color: var(--text-primary);
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        input:focus {
            outline: none;
            border-color: var(--neon-violet);
            box-shadow: 0 0 10px rgba(168, 85, 247, 0.2);
            background-color: rgba(255, 255, 255, 0.05);
        }
        button {
            width: 100%;
            background: linear-gradient(135deg, var(--neon-violet), #ec4899);
            border: none;
            color: white;
            padding: 0.8rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 1rem;
        }
        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 15px rgba(236, 72, 153, 0.4);
        }
        .error-msg {
            color: #f87171;
            font-size: 0.8rem;
            text-align: center;
            margin-top: 1rem;
            font-family: 'Share Tech Mono', monospace;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="title">> ADMIN_CONSOLE_LOGIN_</div>
        <form id="login-form">
            <div class="form-group">
                <label for="username">> OPERATOR:</label>
                <input type="text" id="username" required placeholder="admin">
            </div>
            <div class="form-group">
                <label for="password">> ACCESS_PASSKEY:</label>
                <input type="password" id="password" required placeholder="••••••••">
            </div>
            <button type="submit">ESTABLISH SECURE LINK</button>
            <div class="error-msg" id="error-msg">> ACCESS_DENIED</div>
        </form>
    </div>

    <script>
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorMsg = document.getElementById('error-msg');

            try {
                const res = await fetch('/api/admin/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    window.location.reload();
                } else {
                    errorMsg.style.display = 'block';
                    errorMsg.textContent = '> ACCESS_DENIED: ' + (data.message || 'Invalid keys');
                }
            } catch (err) {
                errorMsg.style.display = 'block';
                errorMsg.textContent = '> NETWORK_EXCEPTION';
            }
        });
    </script>
</body>
</html>"""

def serve_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VortexCoder | Administration Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #07050d;
            --bg-card: rgba(18, 18, 28, 0.45);
            --border-color: rgba(255, 255, 255, 0.08);
            --neon-violet: #a855f7;
            --neon-cyan: #06b6d4;
            --neon-magenta: #ec4899;
            --neon-teal: #10b981;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 2rem;
            position: relative;
        }
        body::after {
            content: '';
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.2) 50%);
            background-size: 100% 4px;
            z-index: 9999;
            pointer-events: none;
            opacity: 0.12;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            z-index: 5;
            position: relative;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }
        .header-title {
            font-family: 'Share Tech Mono', monospace;
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--neon-cyan);
            text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background-color: rgba(239, 68, 68, 0.08);
            border-color: #ef4444;
            color: #ef4444;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
        }
        .btn-delete {
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.75rem;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .card-title {
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            letter-spacing: 1px;
        }
        .card-value {
            font-size: 2.25rem;
            font-weight: 800;
            font-family: 'Share Tech Mono', monospace;
            text-shadow: 0 0 15px rgba(255, 255, 255, 0.1);
        }
        .color-violet { color: var(--neon-violet); text-shadow: 0 0 15px rgba(168, 85, 247, 0.2); }
        .color-cyan { color: var(--neon-cyan); text-shadow: 0 0 15px rgba(6, 182, 212, 0.2); }
        .color-magenta { color: var(--neon-magenta); text-shadow: 0 0 15px rgba(236, 72, 153, 0.2); }

        /* Charts Layout */
        .charts-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .chart-card {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .chart-list {
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }
        .chart-item {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }
        .chart-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            font-family: 'Share Tech Mono', monospace;
        }
        .bar-container {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            overflow: hidden;
        }
        .bar-fill {
            height: 100%;
            width: 0;
            border-radius: 4px;
            transition: width 1s ease-out;
        }
        .fill-violet { background: linear-gradient(90deg, var(--neon-violet), #c084fc); box-shadow: 0 0 8px var(--neon-violet); }
        .fill-cyan { background: linear-gradient(90deg, var(--neon-cyan), #22d3ee); box-shadow: 0 0 8px var(--neon-cyan); }
        .fill-magenta { background: linear-gradient(90deg, var(--neon-magenta), #f472b6); box-shadow: 0 0 8px var(--neon-magenta); }

        /* Tables & Lists */
        .data-section {
            display: grid;
            grid-template-columns: 1.4fr 0.6fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        @media (max-width: 968px) {
            .data-section { grid-template-columns: 1fr; }
        }
        .table-wrapper {
            width: 100%;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: rgba(4, 4, 6, 0.4);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.85rem;
        }
        th, td {
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        th {
            font-family: 'Share Tech Mono', monospace;
            color: var(--text-secondary);
            font-weight: 600;
            background-color: rgba(255, 255, 255, 0.02);
            font-size: 0.75rem;
            letter-spacing: 0.5px;
        }
        tr:last-child td { border: none; }
        .username-cell {
            font-weight: bold;
            color: var(--text-primary);
        }
        .mono-cell {
            font-family: 'Share Tech Mono', monospace;
            color: var(--text-secondary);
        }

        /* Recent Console Logs */
        .log-panel {
            background-color: rgba(4, 4, 6, 0.7);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
            padding: 1rem;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.75rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }
        .log-line {
            color: var(--text-secondary);
        }
        .log-time { color: var(--text-muted); }
        .log-accent { color: var(--neon-cyan); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>
                <span>VORTEXCODER // SECURE_ADMIN_CONSOLE_</span>
            </div>
            <button class="btn" id="btn-logout">LOGOUT_SESSION</button>
        </header>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="card">
                <div class="card-title">> TOTAL_VISITS</div>
                <div class="card-value color-cyan" id="stat-total-visits">0</div>
            </div>
            <div class="card">
                <div class="card-title">> REGISTERED_OPERATORS</div>
                <div class="card-value color-violet" id="stat-total-users">0</div>
            </div>
            <div class="card">
                <div class="card-title">> PROJECT_DOWNLOADS</div>
                <div class="card-value color-magenta" id="stat-total-downloads">0</div>
            </div>
        </div>

        <!-- Charts Grid -->
        <div class="charts-row">
            <div class="card chart-card">
                <div class="card-title">> DEVICE_DISTRIBUTION</div>
                <div class="chart-list" id="chart-devices">
                    <!-- Loaded dynamically -->
                </div>
            </div>
            <div class="card chart-card">
                <div class="card-title">> OS_PLATFORMS</div>
                <div class="chart-list" id="chart-os">
                    <!-- Loaded dynamically -->
                </div>
            </div>
            <div class="card chart-card">
                <div class="card-title">> WEB_BROWSERS</div>
                <div class="chart-list" id="chart-browsers">
                    <!-- Loaded dynamically -->
                </div>
            </div>
        </div>

        <!-- Tables -->
        <div class="data-section">
            <div class="card">
                <div class="card-title" style="margin-bottom: 1rem;">> REGISTERED_USERS_DIRECTORY</div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>CALLSIGN</th>
                                <th>REGISTRATION_DATE</th>
                                <th>SERIAL_NO</th>
                                <th>DOWNLOADS</th>
                                <th style="text-align: right;">ACTION</th>
                            </tr>
                        </thead>
                        <tbody id="users-table-body">
                            <!-- Loaded dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card" style="display: flex; flex-direction: column; gap: 1rem;">
                <div class="card-title">> LIVE_TELEMETRY_LOGS</div>
                <div class="log-panel" id="telemetry-logs">
                    <!-- Loaded dynamically -->
                </div>
            </div>
        </div>
    </div>

    <script>
        async function fetchStats() {
            try {
                const res = await fetch('/api/admin/stats');
                if (res.status === 403) {
                    window.location.reload();
                    return;
                }
                const data = await res.json();
                
                // Set Values
                document.getElementById('stat-total-visits').textContent = data.visits_count;
                document.getElementById('stat-total-users').textContent = data.users.length;
                
                const totalDownloads = data.users.reduce((sum, u) => sum + (u.downloads || 0), 0);
                document.getElementById('stat-total-downloads').textContent = totalDownloads;

                // Render Charts Helper
                function renderChart(containerId, map, themeClass) {
                    const container = document.getElementById(containerId);
                    container.innerHTML = '';
                    
                    const total = Object.values(map).reduce((a, b) => a + b, 0);
                    if (total === 0) {
                        container.innerHTML = '<p style="font-size:0.8rem;color:var(--text-muted)">No telemetry data yet.</p>';
                        return;
                    }

                    // Sort items descending
                    const sorted = Object.entries(map).sort((a,b) => b[1] - a[1]);

                    sorted.forEach(([key, val]) => {
                        const pct = Math.round((val / total) * 100);
                        const item = document.createElement('div');
                        item.className = 'chart-item';
                        item.innerHTML = `
                            <div class="chart-labels">
                                <span>${key}</span>
                                <span>${val} (${pct}%)</span>
                            </div>
                            <div class="bar-container">
                                <div class="bar-fill ${themeClass}" style="width: 0%"></div>
                            </div>
                        `;
                        container.appendChild(item);
                        // Trigger slide transition
                        setTimeout(() => {
                            item.querySelector('.bar-fill').style.width = pct + '%';
                        }, 50);
                    });
                }

                // Render Charts
                renderChart('chart-devices', data.devices, 'fill-cyan');
                renderChart('chart-os', data.os, 'fill-violet');
                renderChart('chart-browsers', data.browsers, 'fill-magenta');

                // Render Table
                const tbody = document.getElementById('users-table-body');
                tbody.innerHTML = '';
                
                data.users.forEach(u => {
                    const tr = document.createElement('tr');
                    const serialFormatted = '#' + String(u.serialNumber || 1).padStart(4, '0');
                    
                    const isGuest = u.username === 'guest';
                    const deleteBtn = isGuest ? '' : `<button class="btn btn-delete" onclick="deleteUser('${u.username}')">DELETE</button>`;

                    tr.innerHTML = `
                        <td class="username-cell">${u.username}</td>
                        <td class="mono-cell">${u.registeredAt}</td>
                        <td class="mono-cell" style="color:var(--neon-cyan); font-weight:bold;">${serialFormatted}</td>
                        <td class="mono-cell">${u.downloads}</td>
                        <td style="text-align: right;">${deleteBtn}</td>
                    `;
                    tbody.appendChild(tr);
                });

                // Render Logs
                const logPanel = document.getElementById('telemetry-logs');
                logPanel.innerHTML = '';
                if (data.visits.length === 0) {
                    logPanel.innerHTML = '<span class="log-line">> Telemetry feed empty.</span>';
                }
                
                data.visits.forEach(v => {
                    const line = document.createElement('div');
                    line.className = 'log-line';
                    line.innerHTML = `
                        <span class="log-time">[${v.timestamp}]</span> 
                        <span class="log-accent">${v.device}</span> / ${v.os} (${v.browser}) 
                        from ${v.referrer} - [${v.resolution}]
                    `;
                    logPanel.appendChild(line);
                });

            } catch (err) {
                console.error(err);
            }
        }

        async function deleteUser(username) {
            if (!confirm(`Are you sure you want to terminate operator credentials for "${username}"?`)) return;
            try {
                const res = await fetch('/api/admin/delete_user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username })
                });
                if (res.ok) {
                    fetchStats();
                } else {
                    const data = await res.json();
                    alert('Delete failed: ' + data.message);
                }
            } catch (e) {
                alert('Connection failure deleting user.');
            }
        }

        document.getElementById('btn-logout').addEventListener('click', async () => {
            await fetch('/api/admin/logout', { method: 'POST' });
            window.location.reload();
        });

        // Initialize
        fetchStats();
    </script>
</body>
</html>"""

@route('/admin')
def admin_page():
    if is_admin_logged_in():
        return serve_dashboard()
    else:
        return serve_login()

if __name__ == '__main__':
    print("*" * 50)
    print(" VortexCoder Analytical & Auth Server is running!")
    print(" Running over Bottle Web Server...")
    print("*" * 50)
    port = int(os.environ.get('PORT', 5000))
    run(host='0.0.0.0', port=port)
