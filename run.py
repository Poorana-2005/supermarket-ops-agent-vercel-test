from app.bot import build_app
from app.db import init_db
from app.config import TELEGRAM_BOT_TOKEN

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env")
    init_db()
    build_app().run_polling()
