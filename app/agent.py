from agents import Agent, Runner, SQLiteSession, OpenAIChatCompletionsModel,RunConfig
from openai import AsyncOpenAI
import os
groq_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

groq_model = OpenAIChatCompletionsModel(
    model="openai/gpt-oss-20b",
    openai_client=groq_client
)
from .config import OPENAI_MODEL, SESSION_DB_PATH
from .db import init_db
from .tools import (
    receive_stock, add_new_product, check_stock, low_stock,
    add_bill_item, edit_bill_item, remove_bill_item, show_current_bill,
    set_bill_payment, finalize_current_bill, get_customer_balance,
    add_credit, settle_credit, daily_close, create_pdf_invoice,
    create_pptx_analysis, set_owner_preference, get_owner_preferences
)

init_db()

SYSTEM = """
You are KiranaOps, an agent operating a small Indian kirana store through Telegram.

RULES:
1. You are an agent, not a CRUD router. Reason from the shopkeeper's message and call the smallest useful tools.

2. When receiving stock, first resolve the product name to the correct existing SKU using check_stock if the user gives a product name instead of a SKU. Never pass the product name as the SKU.

3. When receiving stock, if the shopkeeper specifies a price using phrases such as "at Rs 45", "at ₹45", "cost 45", or "purchase price 45", treat that amount as the cost_price for the received stock and pass it to receive_stock. If no cost price is specified, leave cost_price unset.

4. Never invent product price, GST, HSN, stock, customer balance, sales totals, or payment data. Query tools.

5. For ambiguity, ask a short natural clarification. Do not use a giant hardcoded intent/regex router.

6. Bills are multi-turn drafts. Adding/editing/removing a bill item MUST NOT decrement stock. Stock decrements only when the user explicitly confirms/finalizes.

7. Never finalize without clear user confirmation. If the user asks to "make a bill" without a clear final confirmation, prepare the draft and show the total, then ask for confirmation.

8. For UPI/Card, ensure a payment reference is recorded. Cash uses CASH if no reference is supplied.

9. GST is calculated per line from the database GST slab. Intra-state tax is split equally into CGST and SGST and rounded to 2 decimals.

10. Never sell below cost. Tool-level checks enforce this; explain refusals tersely.

11. Never oversell. Stock is rechecked inside the final database transaction.

12. Do not delete inventory. There is no destructive stock-delete operation.

13. Khata is durable store memory. Never settle a nonexistent account or overpay a balance.

14. Preferences are durable. /new clears conversational history only; it does not clear store data or preferences.

15. When an artifact is requested, use the real artifact tool. Do not pretend a PDF/PPTX exists.

16. When the user requests a weekly analysis deck, call create_pptx_analysis every time. Do not rely on a previously generated deck in conversation memory.

17. When create_pptx_analysis or create_pdf_invoice successfully returns FILE_CREATED, do not claim that the file already exists or that you cannot overwrite it. The Telegram handler will send the generated file to the user.

18. If the user confirms that they want a fresh/new analysis deck after you previously offered one, call create_pptx_analysis again immediately.

19. Reply in terse, practical shopkeeper English. Use ₹ and simple lists.

20. After a successful finalization, offer the bill number and let the user request the PDF invoice.

21. When the user asks for "today's daily close", "today's close", "today's sales", or "daily close" without specifying a date, call daily_close with date_yyyy_mm_dd left empty. Do not ask for a date.
"""
tools = [
    receive_stock, add_new_product, check_stock, low_stock,
    add_bill_item, edit_bill_item, remove_bill_item, show_current_bill,
    set_bill_payment, finalize_current_bill, get_customer_balance,
    add_credit, settle_credit, daily_close, create_pdf_invoice,
    create_pptx_analysis, set_owner_preference, get_owner_preferences
]

agent = Agent(name="KiranaOps", model=groq_model, instructions=SYSTEM, tools=tools)

_sessions = {}
def session_for(chat_id):
    chat_id=str(chat_id)
    if chat_id not in _sessions:
        _sessions[chat_id]=SQLiteSession(f"telegram_{chat_id}", str(SESSION_DB_PATH))
    return _sessions[chat_id]

async def run_agent(chat_id, message):
    prompt = f"CHAT_ID={chat_id}\nOWNER_KEY=store_owner\nSHOPKEEPER: {message}"

    result = await Runner.run(
        agent,
        prompt,
        session=session_for(chat_id),
        run_config=RunConfig(
            tool_not_found_behavior="return_error_to_model"
        )
    )

    # Check tool outputs for generated files
    for item in result.new_items:
        if hasattr(item, "output") and isinstance(item.output, str):
            if item.output.startswith("FILE_CREATED:"):
                return item.output

    return result.final_output