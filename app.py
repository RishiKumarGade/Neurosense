"""
NeuroSense — main entry point.
Registers the games and mri blueprints, handles shared DB/auth helpers.

Run:  python app.py
"""
from __future__ import annotations
import os
import re
import secrets
import hashlib
from datetime import datetime
from typing import Dict, Any

# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    import bcrypt
    _bcrypt_ok = True
except ImportError:
    _bcrypt_ok = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, session, request, jsonify

try:
    from flask_cors import CORS
    _cors_ok = True
except ImportError:
    _cors_ok = False

try:
    from flask_session import Session
    _fsession_ok = True
except ImportError:
    _fsession_ok = False

# ── MongoDB ───────────────────────────────────────────────────────────────────
_mongo_client  = None
_mongo_ok      = False
users_col      = None
game_history_col = None

def _try_mongo():
    global _mongo_ok, users_col, game_history_col, _mongo_client
    mongo_url = os.environ.get('MONGO_URL', '')
    if not mongo_url:
        return
    try:
        from pymongo import MongoClient
        import certifi, ssl
        _mongo_client = MongoClient(
            mongo_url,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=15000,
        )
        _mongo_client.admin.command('ping')
        db = _mongo_client['neurosense_db']
        users_col        = db['users']
        game_history_col = db['game_history']
        _mongo_ok = True
        print('[DB] MongoDB connected.')
    except Exception as e:
        print(f'[DB] MongoDB unavailable — running in local session mode. ({e})')

_try_mongo()

def _ensure_mongo() -> bool:
    global _mongo_ok
    if _mongo_ok:
        try:
            _mongo_client.admin.command('ping')
            return True
        except Exception:
            _mongo_ok = False
            _try_mongo()
    return _mongo_ok

# ── Auth helpers ──────────────────────────────────────────────────────────────
def _hash_pw(pw: str) -> bytes:
    if _bcrypt_ok:
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())
    return hashlib.sha256(pw.encode()).hexdigest().encode()

def _check_pw(pw: str, hashed) -> bool:
    if _bcrypt_ok:
        try:
            return bcrypt.checkpw(pw.encode(), hashed)
        except Exception:
            pass
    return hashlib.sha256(pw.encode()).hexdigest().encode() == hashed

def _valid_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def _valid_password(pw: str) -> bool:
    return len(pw) >= 6

_local_users: Dict[str, Dict] = {}

def _find_user(email: str):
    if _ensure_mongo():
        return users_col.find_one({'email': email})
    return _local_users.get(email)

def _create_user(fullname: str, email: str, password: str):
    if _ensure_mongo():
        users_col.insert_one({
            'name': fullname, 'email': email,
            'password': _hash_pw(password), 'created_at': datetime.now(),
        })
    else:
        _local_users[email] = {
            'name': fullname, 'email': email, 'password': _hash_pw(password),
        }

# ── Score helpers ─────────────────────────────────────────────────────────────
def _save_score_doc(email: str, doc: Dict):
    if _ensure_mongo():
        user = users_col.find_one({'email': email})
        if not user:
            return
        doc['user_id'] = user['_id']
        game_history_col.insert_one(doc)
    else:
        history = session.setdefault('game_history', [])
        doc['played_at'] = doc['played_at'].isoformat()
        history.append(doc)
        session.modified = True

def _get_history(email: str):
    if _ensure_mongo():
        user = users_col.find_one({'email': email})
        if not user:
            return []
        docs = list(game_history_col.find(
            {'user_id': user['_id']}, {'_id': 0, 'user_id': 0}
        ).sort('played_at', -1))
        for h in docs:
            if isinstance(h.get('played_at'), datetime):
                h['played_at'] = h['played_at'].isoformat()
        return docs
    return list(reversed(session.get('game_history', [])))

# ── App factory ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('NEUROSENSE_SECRET') or secrets.token_hex(32)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

if _fsession_ok:
    app.config['SESSION_TYPE']     = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), '.flask_sessions')
    app.config['SESSION_PERMANENT'] = False
    Session(app)

if _cors_ok:
    CORS(app, resources={r'/save_score': {'origins': os.environ.get('ALLOWED_ORIGIN', '*')}})

# ── CSRF context processor ────────────────────────────────────────────────────
@app.context_processor
def inject_csrf():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return {'csrf_token': session['csrf_token']}

# ── Register blueprints ───────────────────────────────────────────────────────
from games import games_bp   # noqa: E402
from mri   import mri_bp     # noqa: E402

app.register_blueprint(games_bp)
app.register_blueprint(mri_bp)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port  = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
