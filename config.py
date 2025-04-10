"""
Configuration settings for the Garbage Collection Management System.
"""
import os
# Flask application configuration
APP_CONFIG = {
    "DEBUG": os.environ.get("DEBUG", "True").lower() == "true",
    "SECRET_KEY": os.environ.get("SECRET_KEY", "garbage_collection_app_secret_key"),
    "HOST": "0.0.0.0",
    "PORT": int(os.environ.get("PORT", 5000)),
}

# Data file paths
DATA_CONFIG = {
    "DATA_DIR": "data",
    "WORKERS_FILE": "workers.json",
    "ALERTS_FILE": "alerts.json",
    "ASSIGNMENTS_FILE": "assignments.json",
    "BINS_FILE": "bins.json",
}

# Alert severity thresholds (in percentage)
ALERT_THRESHOLDS = {
    "LOW": 30,  # 0-30% fill level
    "MODERATE": 70,  # 31-70% fill level
    # Above 70% is considered HIGH
}

# Admin credentials (use a proper auth system in production)
AUTH_CONFIG = {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "admin123"}

# Dashboard auto-refresh interval (in milliseconds)
DASHBOARD_REFRESH_INTERVAL = 30000  # 30 seconds
