# NeuroSense

Brain training platform with cognitive games and MRI-based impairment detection.

## Quick Start

### 1. Setup (run once)

```bash
python setup.py
```

This creates a `venv/` and installs all dependencies including PyTorch (CPU).

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your MongoDB URL if you have one (optional)
```

### 3. Run

```bash
# Mac / Linux
./run.sh

# Windows
run.bat

# Or directly
python app.py
```

App runs at **http://127.0.0.1:5000**

---

## Manual Install (without setup.py)

```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Install deps
pip install Flask pymongo bcrypt flask-cors flask-session certifi python-dotenv numpy Pillow

# PyTorch CPU (recommended — smaller download)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

---

## Features

- 6 brain training game categories (30 games)
- Cognitive progress dashboard with charts
- MRI scan analysis — upload a brain MRI to detect impairment stage
- MongoDB persistence (falls back to local sessions if unavailable)

## MRI Analysis

The model file (`ml/models/mri_model.pt`) must be present for MRI analysis to work.  
Classes: `No Impairment`, `Very Mild Impairment`, `Mild Impairment`, `Moderate Impairment`

## Environment Variables

| Variable            | Default                  | Description                     |
| ------------------- | ------------------------ | ------------------------------- |
| `MONGO_URL`         | _(none)_                 | MongoDB Atlas connection string |
| `NEUROSENSE_SECRET` | _(random)_               | Flask session secret key        |
| `PORT`              | `5000`                   | Port to run on                  |
| `FLASK_DEBUG`       | `false`                  | Enable debug mode               |
| `MRI_MODEL_PATH`    | `ml/models/mri_model.pt` | Path to model file              |
