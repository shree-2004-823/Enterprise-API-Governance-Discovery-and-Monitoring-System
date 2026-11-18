"""Configuration. Defaults match a fresh XAMPP install (root, no password, port 3306).
Override with environment variables or a local .env file.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "api_management"),
)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Set a strong random SECRET_KEY in the environment or local .env file.")
DEMO_PASSWORD = "Password@123"   # given to the 5 seed users by setup_db.py
