# ==================== config.py ====================
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'inkkeeper-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{BASE_DIR / "data" / "inkkeeper.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / 'data' / 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

    PRINTER_NAME = os.environ.get('PRINTER_NAME', 'InkKeeper_Printer')
    PRINTER_IP = os.environ.get('PRINTER_IP', '')
    PRINTER_CONNECTION = os.environ.get('PRINTER_CONNECTION', 'cups')  # cups / network / script
    PRINT_SCRIPT = os.environ.get('PRINT_SCRIPT', '')

    SCHEDULER_TIMEZONE = os.environ.get('TZ', 'Asia/Shanghai')
    DAILY_RESET_HOUR = int(os.environ.get('DAILY_RESET_HOUR', '0'))

    @staticmethod
    def init_app():
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / 'data').mkdir(parents=True, exist_ok=True)
