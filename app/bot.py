import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from .config import TELEGRAM_BOT_TOKEN
from .agent import run_agent
from .db import tx

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("KiranaOps ready. Try: stock, bill 2 atta + 1 salt, low stock, or Ramesh balance.")

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Conversation memory can be cleared by removing the session history file/table;
    # durable store DB remains untouched. SQLiteSession exposes clear_session().
    from .agent import session_for
    session=session_for(update.effective_chat.id)
    await session.clear_session()
    await update.message.reply_text("New conversation. Store stock, khata and preferences are unchanged.")

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    update_id = str(update.update_id)

    with tx() as c:
        exists = c.execute(
            "SELECT 1 FROM processed_updates WHERE update_id=?",
            (update_id,)
        ).fetchone()

        if exists:
            return

        c.execute(
            "INSERT INTO processed_updates(update_id) VALUES(?)",
            (update_id,)
        )

    try:
        answer = await run_agent(
            update.effective_chat.id,
            update.message.text
        )

        # Handle artifact created by the tool.
        if answer.startswith("FILE_CREATED:"):
            path = answer.split("FILE_CREATED:", 1)[1].strip()

            with open(path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(path)
                )

        # Handle cases where the model mentions the generated file path
        # instead of returning the FILE_CREATED marker directly.
        elif "Weekly analysis deck updated:" in answer and "Path" in answer:
            import re

            match = re.search(
                r'Path\*\*:\s*`([^`]+\.pptx)`',
                answer
            )

            if match:
                path = match.group(1)

                with open(path, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        filename=os.path.basename(path)
                    )
            else:
                await update.message.reply_text(answer)

        else:
            await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(
            f"Agent error: {e}"
        )
def build_app():
    app=Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("new",new_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))
    return app
