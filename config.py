# config.py
import os
from datetime import timedelta
from os.path import join, dirname, abspath

# Load .env
dotenv_path = join(dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)

# Get project root and instance folder
PROJECT_ROOT = abspath(dirname(__file__))
INSTANCE_FOLDER = join(PROJECT_ROOT, 'instance')

# Ensure instance folder exists
os.makedirs(INSTANCE_FOLDER, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "fallback_secret_key"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{join(INSTANCE_FOLDER, 'smartcareer.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)