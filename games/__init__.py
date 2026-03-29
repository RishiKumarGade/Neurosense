"""
Games module — handles auth, dashboard, and all brain-training game routes.
"""
from __future__ import annotations
import os
import secrets
from datetime import datetime
from typing import Dict, Any

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, jsonify, abort, current_app
)

games_bp = Blueprint(
    'games',
    __name__,
    template_folder='templates',   # games/templates/
)

# ── Helpers (injected from app.py via current_app) ────────────────────────────

def _login_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'email' not in session:
            if request.path.startswith(('/save_score', '/get_game', '/get_progress')):
                return jsonify({'error': 'Not logged in', 'code': 401}), 401
            return redirect(url_for('games.login'))
        return view_func(*args, **kwargs)
    return wrapper

def _check_csrf():
    token = session.get('csrf_token', '')
    form_token = request.form.get('csrf_token', '')
    if not token or token != form_token:
        abort(403)

# ── Auth ──────────────────────────────────────────────────────────────────────

@games_bp.route('/')
def home():
    if 'email' in session:
        return redirect(url_for('games.dashboard'))
    return render_template('auth/pre-neurosense.html')

@games_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'email' in session:
        return redirect(url_for('games.dashboard'))
    message = ''
    if request.method == 'POST':
        _check_csrf()
        from app import _find_user, _create_user, _valid_email, _valid_password
        fullname  = request.form.get('fullname', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')
        if not all([fullname, email, password1, password2]):
            message = 'All fields are required.'
        elif not _valid_email(email):
            message = 'Please enter a valid email address.'
        elif not _valid_password(password1):
            message = 'Password must be at least 6 characters.'
        elif password1 != password2:
            message = 'Passwords do not match.'
        elif _find_user(email):
            message = 'Email already registered.'
        else:
            _create_user(fullname, email, password1)
            session['email'] = email
            session['name']  = fullname
            return redirect(url_for('games.dashboard'))
    return render_template('auth/Signup.html', message=message)

@games_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('games.dashboard'))
    message = ''
    if request.method == 'POST':
        _check_csrf()
        from app import _find_user, _check_pw, _valid_email
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not _valid_email(email):
            message = 'Please enter a valid email address.'
        else:
            user = _find_user(email)
            if not user:
                message = 'Email not found.'
            elif not _check_pw(password, user['password']):
                message = 'Incorrect password.'
            else:
                session['email'] = email
                session['name']  = user.get('name', email)
                return redirect(url_for('games.dashboard'))
    return render_template('auth/neurosense_login.html', message=message)

@games_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('games.home'))

# ── Dashboard ─────────────────────────────────────────────────────────────────

@games_bp.route('/dashboard')
@_login_required
def dashboard():
    return render_template('dashboard/index.html', name=session.get('name', ''))

@games_bp.route('/games')
@_login_required
def games_hub():
    return render_template('dashboard/games.html')

@games_bp.route('/progress')
@_login_required
def progress_page():
    return redirect(url_for('games.cognitive_dashboard'))

@games_bp.route('/cognitive-dashboard')
@_login_required
def cognitive_dashboard():
    return render_template('dashboard/cognitive-dashboard.html')

# ── Game pages ────────────────────────────────────────────────────────────────

CATEGORY_MAPPING = {
    'focus-training':   'FocusTraining',
    'logic-puzzles':    'LogicPuzzles',
    'memory-challenge': 'MemoryChallenge',
    'number-sense':     'NumberSense',
    'speed-processing': 'SpeedProcessing',
    'word-games':       'WordGames',
}

_RESERVED = {
    'dashboard', 'games', 'progress', 'cognitive-dashboard', 'login',
    'signup', 'logout', 'save_score', 'get_game_history', 'get_progress',
    'health', 'privacy', 'terms', 'contact', 'mri', 'mri-predict',
    'favicon.ico', 'static',
}

@games_bp.route('/<category>')
@_login_required
def category_page(category: str):
    if category in _RESERVED:
        abort(404)
    mapped = CATEGORY_MAPPING.get(category)
    if not mapped:
        abort(404)
    return render_template(f'games/{mapped}/{mapped}.html')

@games_bp.route('/<category>/<game_name>')
@_login_required
def game_page(category: str, game_name: str):
    if category in _RESERVED:
        abort(404)
    mapped = CATEGORY_MAPPING.get(category)
    if not mapped:
        abort(404)
    name = game_name.replace('..', '').replace('/', '')
    if not name.endswith('.html'):
        name += '.html'
    try:
        return render_template(f'games/{mapped}/{name}')
    except Exception:
        abort(404)

# ── Score API ─────────────────────────────────────────────────────────────────

GAME_MAX_SCORES = {
    'attention-anchor': 100, 'FocusTraining-DistractionDrift': 200,
    'FocusTraining-SilentSignal': 500, 'FocusTraining-Stroop': 200,
    'FocusTraining-TargetLock': 500,
    'Logic Grid': 100, 'Pattern Forge': 100, 'Reason Path': 100,
    'Rule Breaker': 100, 'Sequence Solver': 100,
    '3 Word Recall': 100, 'Echo Recall': 200, 'Memory Card Game': 1000,
    'Memory Map': 100, 'Story Snapback': 100,
    'Math Reflex': 200, 'Pattern Numbers': 200, 'Quick Count': 200,
    'Trail Making': 1000, 'Value Shift': 200,
    'Flash Respond': 200, 'Instant Shift': 1500, 'Rapid Choice': 2000,
    'Rule Dash': 2000, 'Speed Sort': 2000,
    'Visual-NameThatObject': 100,
}

# 6 categories worth 5 games each (target values are /100 per category and /600 overall)
DOMAIN_MAP = {
    'Focus Training':   ['attention-anchor','FocusTraining-DistractionDrift','FocusTraining-SilentSignal','FocusTraining-Stroop','FocusTraining-TargetLock'],
    'Logic Puzzles':    ['Logic Grid','Pattern Forge','Reason Path','Rule Breaker','Sequence Solver'],
    'Memory Challenge': ['3 Word Recall','Echo Recall','Memory Card Game','Memory Map','Story Snapback'],
    'Number Sense':     ['Math Reflex','Pattern Numbers','Quick Count','Trail Making','Value Shift'],
    'Speed Processing': ['Flash Respond','Instant Shift','Rapid Choice','Rule Dash','Speed Sort'],
    'Word Games':       ['Visual-NameThatObject'],
}

# Games with fixed rounds that must be completed entirely
ROUND_BASED_GAMES = {
    'Logic Grid', 'Reason Path', 'Rule Breaker', 'Sequence Solver',
    '3 Word Recall', 'Echo Recall', 'Memory Card Game', 'Memory Map',
    'Trail Making', 'Quick Count', 'Pattern Numbers', 'Math Reflex',
    'Flash Respond', 'Instant Shift', 'Rapid Choice', 'Rule Dash', 'Speed Sort',
    'attention-anchor', 'FocusTraining-DistractionDrift', 'FocusTraining-SilentSignal',
    'FocusTraining-Stroop', 'FocusTraining-TargetLock',
    'Visual-NameThatObject',
}

@games_bp.route('/save_score', methods=['POST'])
@_login_required
def save_score():
    from app import _save_score_doc, _mongo_ok
    try:
        data: Dict[str, Any] = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400
    game_name     = data.get('game_name')
    score         = data.get('score')
    time_taken_ms = data.get('time_taken_ms')
    rounds_played = data.get('rounds_played')
    total_rounds  = data.get('total_rounds')
    extra         = data.get('extra')
    if not isinstance(game_name, str) or not game_name.strip():
        return jsonify({'error': 'game_name required'}), 400
    if not isinstance(score, (int, float)):
        return jsonify({'error': 'score must be numeric'}), 400

    # Enforce full game completion for round-based games
    game_key = game_name.strip()
    if game_key in ROUND_BASED_GAMES:
        if not isinstance(rounds_played, (int, float)):
            return jsonify({'error': 'rounds_played required for round-based games and must be numeric.'}), 400

        if not isinstance(total_rounds, (int, float)):
            return jsonify({'error': 'total_rounds required for round-based games and must be numeric.'}), 400

        if total_rounds <= 0:
            return jsonify({'error': 'total_rounds must be greater than 0.'}), 400

        if rounds_played < total_rounds:
            return jsonify({'error': 'Incomplete game. Must complete all rounds to save score.'}), 400

        if rounds_played > total_rounds:
            rounds_played = total_rounds

    raw_score = float(score)

    total_possible = None
    for key in ('total_possible', 'total_possible_performance', 'max_possible', 'max_performance'):
        if isinstance(data.get(key), (int, float)) and data.get(key) > 0:
            total_possible = float(data.get(key))
            break

    normalized = None
    # Priority 1: Use total_possible if provided (games with calculated scores like Trail Making)
    if total_possible and total_possible > 0:
        normalized = raw_score / total_possible * 20.0
    # Priority 2: Use game max scores table
    else:
        max_raw = GAME_MAX_SCORES.get(game_name.strip(), None)
        if max_raw and max_raw > 0:
            normalized = raw_score / max_raw * 20.0
        # Priority 3: Percentage score (0-100) → normalize to 0-20
        elif 0 <= raw_score <= 100:
            normalized = raw_score / 100.0 * 20.0
        else:
            normalized = raw_score  # fallback: use as-is and clamp

    normalized = round(min(20.0, max(0.0, normalized)), 1)
    time_taken_ms = float(time_taken_ms) if isinstance(time_taken_ms, (int, float)) and time_taken_ms > 0 else None
    doc = {
        'game_name': game_name.strip(),
        'score': normalized,
        'raw_score': raw_score,
        'time_taken_ms': time_taken_ms,
        'rounds_played': rounds_played,
        'total_rounds': total_rounds if isinstance(total_rounds, (int, float)) else None,
        'total_possible': total_possible,
        'extra': extra if isinstance(extra, dict) else None,
        'played_at': datetime.now(),
    }
    _save_score_doc(session['email'], doc)
    return jsonify({'message': 'Score saved', 'mode': 'db' if _mongo_ok else 'local',
                    'score': normalized, 'raw_score': raw_score, 'max_score': 20}), 200

@games_bp.route('/reset_progress', methods=['POST'])
@_login_required
def reset_progress():
    from app import _ensure_mongo, users_col, game_history_col
    email = session['email']
    if _ensure_mongo():
        user = users_col.find_one({'email': email})
        if user:
            deleted = game_history_col.delete_many({'user_id': user['_id']})
            return jsonify({'message': f'Progress reset. {deleted.deleted_count} records deleted.'}), 200
        return jsonify({'error': 'User not found'}), 404
    session.pop('game_history', None)
    session.modified = True
    return jsonify({'message': 'Progress reset (local mode).'}), 200

@games_bp.route('/get_game_history')
@_login_required
def get_game_history():
    from app import _get_history
    return jsonify({'history': _get_history(session['email'])}), 200

@games_bp.route('/get_progress')
@_login_required
def get_progress():
    from app import _get_history
    history = _get_history(session['email'])
    progress: Dict[str, Any] = {}
    for h in sorted(history, key=lambda x: x.get('played_at', '')):
        g = h['game_name']
        entry = progress.setdefault(g, {
            'scores': [], 'dates': [], 'total_games': 0,
            'best_score': 0.0, 'average_score': 0.0,
            'avg_time_ms': None, '_times': [],
        })
        entry['scores'].append(float(h['score']))
        if h.get('time_taken_ms'):
            entry['_times'].append(float(h['time_taken_ms']))
        try:
            dt = datetime.fromisoformat(h['played_at']) if isinstance(h['played_at'], str) else h['played_at']
            entry['dates'].append(dt.strftime('%m/%d'))
        except Exception:
            entry['dates'].append('')
        entry['total_games'] += 1
        entry['best_score'] = max(entry['best_score'], float(h['score']))
    for entry in progress.values():
        s = entry['scores']
        entry['average_score'] = round(sum(s) / len(s), 1) if s else 0.0
        t = entry.pop('_times')
        entry['avg_time_ms'] = round(sum(t) / len(t)) if t else None

    category_totals = {}
    for category, games in DOMAIN_MAP.items():
        category_score = 0.0
        for game in games:
            if game in progress:
                category_score += float(progress[game].get('best_score', 0.0))
        category_totals[category] = round(min(100.0, max(0.0, category_score)), 1)

    overall_total = round(min(600.0, max(0.0, sum(category_totals.values()))), 1)

    return jsonify({
        'progress': progress,
        'summary': {
            'categories': category_totals,
            'overall_score': overall_total,
            'max_overall': 600.0,
        }
    }), 200

@games_bp.route('/health')
def health():
    from app import _mongo_ok
    return jsonify({'status': 'ok', 'db': 'mongo' if _mongo_ok else 'local',
                    'logged_in': 'email' in session,
                    'user': session.get('email')}), 200
