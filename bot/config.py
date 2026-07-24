import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "").strip()
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID", "").strip()

raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in raw_admin_ids.split(",") if x.strip().isdigit()]

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "database.sqlite"))
VOICES_DIR = os.getenv("VOICES_DIR", str(BASE_DIR / "data" / "voices"))

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)
