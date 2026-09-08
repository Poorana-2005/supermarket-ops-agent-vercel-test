import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data/kirana.db"))
SESSION_DB_PATH = Path(os.getenv("SESSION_DB_PATH", BASE_DIR / "data/sessions.db"))
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", BASE_DIR / "artifacts"))

if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/kirana.db")
    SESSION_DB_PATH = Path("/tmp/sessions.db")
    ARTIFACT_DIR = Path("/tmp/artifacts")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SESSION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SHOP_NAME = os.getenv("SHOP_NAME", "KiranaOps Demo Store")
SHOP_GSTIN = os.getenv("SHOP_GSTIN", "33ABCDE1234F1Z5")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
