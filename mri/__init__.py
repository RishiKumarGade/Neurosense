"""
MRI module — handles MRI scan upload and cognitive impairment prediction.
Model lives in mri/ml/models/mri_model.pt
"""
from __future__ import annotations
import os
import io
import json

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

mri_bp = Blueprint(
    'mri',
    __name__,
    template_folder='templates',   # mri/templates/
)

# ── Model paths ───────────────────────────────────────────────────────────────
_MODULE_DIR    = os.path.dirname(__file__)
_MODEL_PATH    = os.environ.get(
    'MRI_MODEL_PATH',
    os.path.join(_MODULE_DIR, 'ml', 'models', 'mri_model.pt')
)
_CLASSES_PATH  = _MODEL_PATH.replace('.pt', '_classes.json')

# ── Lazy model loader ─────────────────────────────────────────────────────────
_torch      = None
_transforms = None
_model      = None
MRI_CLASSES = ['Mild Impairment', 'Moderate Impairment', 'No Impairment', 'Very Mild Impairment']

def _load_torch():
    global _torch, _transforms
    if _torch is None:
        import torch
        from torchvision import transforms
        _torch      = torch
        _transforms = transforms
    return _torch, _transforms

def _load_model():
    global _model, MRI_CLASSES
    if _model is None:
        torch, _ = _load_torch()
        if os.path.exists(_MODEL_PATH):
            _model = torch.load(_MODEL_PATH, map_location='cpu', weights_only=False)
            _model.eval()
            if os.path.exists(_CLASSES_PATH):
                with open(_CLASSES_PATH) as f:
                    idx_map = json.load(f)
                MRI_CLASSES = [idx_map[str(i)] for i in range(len(idx_map))]
    return _model

def _login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('games.login'))
        return f(*args, **kwargs)
    return wrapper

# ── Routes ────────────────────────────────────────────────────────────────────

@mri_bp.route('/mri')
@_login_required
def mri_page():
    return render_template('mri/mri_detection.html')

@mri_bp.route('/mri-predict', methods=['POST'])
@_login_required
def mri_predict():
    try:
        import numpy as np
    except ImportError:
        return jsonify({'error': 'numpy not installed. Run: pip install numpy torch torchvision Pillow'}), 503

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({'error': 'Empty file'}), 400

    try:
        torch, transforms = _load_torch()
        model = _load_model()
        if model is None:
            return jsonify({'error': f'Model not found at {_MODEL_PATH}'}), 503

        from PIL import Image
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        img    = Image.open(io.BytesIO(file.read())).convert('RGB')
        tensor = preprocess(img).unsqueeze(0)

        with torch.no_grad():
            probs = torch.softmax(model(tensor)[0], dim=0).numpy()

        pred_idx   = int(np.argmax(probs))
        pred_class = MRI_CLASSES[pred_idx]
        confidence = float(probs[pred_idx]) * 100
        all_scores = {MRI_CLASSES[i]: round(float(probs[i]) * 100, 2) for i in range(len(MRI_CLASSES))}

        return jsonify({
            'prediction': pred_class,
            'confidence': round(confidence, 2),
            'all_scores': all_scores,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
