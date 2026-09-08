# KiranaOps — Supermarket Ops Agent

**Telegram Bot:** `@KiranaOpsSupermarketBot`

KiranaOps is a Telegram-first AI agent for operating a small Indian kirana store. It supports inventory management, multi-turn billing, GST calculations, payments, khata tracking, daily operations, PDF invoices, PPTX analysis, and durable owner preferences.

## Demo Video

[Watch the 4–5 minute demo](https://drive.google.com/file/d/1iOyGiAmuJD_5eJRS2X0d9bS9j3Yh8wkd/view?usp=sharing)

The demonstration covers:

* Stock receiving
* Multi-item bill creation and editing
* Oversell protection
* Khata credit and settlement
* PDF GST invoice generation
* Weekly PPTX analysis deck generation
* Durable owner preferences across `/new`

---

## Features

### Inventory

* Receive stock and update cost price
* Add new products
* Check current stock
* Identify low-stock products
* Prevent destructive inventory deletion

### Billing

* Multi-turn draft bills
* Add, edit, and remove bill items
* Stock remains unchanged while a bill is a draft
* Stock is decremented only after final confirmation
* Atomic stock recheck during finalization
* Below-cost sale protection
* Oversell protection

### GST & Payments

* Per-item GST calculation
* HSN support
* CGST + SGST split
* GST rounded to 2 decimal places
* Cash, UPI, and Card payment support
* Payment reference tracking

### Khata

* Customer balance lookup
* Credit management
* Partial/full settlement
* Protection against nonexistent accounts and overpayment

### Reports & Artifacts

* Daily close with revenue, GST, payment split, and top products
* Real PDF GST-style invoices
* Real PowerPoint analysis decks
* Revenue charts
* Top-selling products
* GST collected
* Payment mix
* Low-stock SKU count
* Store-health insights

### Durable Memory

* Owner preferences are stored separately from conversation history
* `/new` clears conversational history without deleting store data or preferences

---

## Agent Harness

KiranaOps uses the **OpenAI Agents SDK** as its agent harness with a Groq OpenAI-compatible model.

The system is **agent-first rather than a hardcoded command/regex router**.

The agent receives the shopkeeper's natural-language request, reasons about what information or action is required, selects the appropriate typed Python tool, observes the result, and continues until the task is complete or clarification is required.

### Control Loop

```text
Shopkeeper message
        ↓
Agent reasoning
        ↓
Typed business tool
        ↓
SQLite / artifact result
        ↓
Agent reasoning
        ↓
Shopkeeper response
```

Business-critical rules are enforced inside the tools and database transactions rather than relying only on the model's instructions.

---

## Tool / Skill Surface

### Inventory

```text
receive_stock
add_new_product
check_stock
low_stock
```

### Billing

```text
add_bill_item
edit_bill_item
remove_bill_item
show_current_bill
set_bill_payment
finalize_current_bill
```

### Khata

```text
get_customer_balance
add_credit
settle_credit
```

### Operations & Artifacts

```text
daily_close
create_pdf_invoice
create_pptx_analysis
```

### Owner Memory

```text
set_owner_preference
get_owner_preferences
```

---

## Safety & Business Guardrails

The agent is backed by database-level checks for important store operations.

### Grounding

The agent does not invent:

* Product prices
* Stock quantities
* GST rates
* HSN codes
* Customer balances
* Sales totals
* Payment information

These values are retrieved from the SQLite-backed business tools.

### Oversell Protection

During bill finalization, stock is rechecked inside a database write transaction immediately before inventory is decremented.

This prevents a bill from selling more inventory than is actually available.

### Below-Cost Protection

Sales below the stored cost price are rejected at the business-tool layer.

### Atomic Finalization

Bill finalization atomically:

1. Validates the bill
2. Rechecks stock
3. Creates the sale
4. Decrements inventory
5. Removes the draft

This prevents partial finalization.

### Idempotency

Telegram update IDs are persisted in the database so duplicate updates can be ignored.

### Khata Protection

Khata settlement rejects:

* Nonexistent customer accounts
* Settlements larger than the outstanding balance

---

## Multi-Turn Bills

Bills are maintained as persistent drafts.

A shopkeeper can:

```text
Add 2 atta
Add 1 salt
Change atta quantity to 3
Remove salt
Show current bill
```

Inventory is **not changed while editing the draft**.

Stock is decremented only after explicit confirmation and successful finalization.

---

## GST & PDF Invoices

The system calculates GST per bill line using the product's stored GST slab.

For intra-state sales:

```text
GST
 ├── CGST
 └── SGST
```

The generated PDF invoice includes:

* Product name
* HSN
* Quantity
* Rate
* Taxable value
* CGST
* SGST
* Total GST
* Payment mode
* Payment reference
* Grand total

The invoice is generated as a real PDF artifact and sent through Telegram.

---

## PPTX Analysis Deck

The agent can generate a real PowerPoint analysis deck on request.

The deck includes:

* 7-day revenue chart
* Top-selling products
* GST collected
* Payment mix
* Low-stock SKU count
* Store-health insights

The revenue visualization is generated from actual store data rather than static placeholder charts.

---

## Demo Flow

The recording demonstrates the complete agent workflow:

```text
Receive stock
      ↓
Create multi-item bill
      ↓
Edit bill
      ↓
Attempt oversell
      ↓
Khata credit → balance → settlement
      ↓
Generate PDF invoice
      ↓
Generate PPTX analysis deck
      ↓
Save owner preference
      ↓
/new
      ↓
Retrieve remembered preference
```

---

## Setup

### 1. Create Telegram Bot

Create a Telegram bot using BotFather and obtain the bot token.

### 2. Configure Groq

Obtain a Groq API key.

### 3. Configure Environment Variables

Copy:

```bash
.env.example
```

to:

```bash
.env
```

and configure the required environment variables.

**Never commit `.env` or API keys to GitHub.**

### 4. Create Virtual Environment

```bash
python -m venv .venv
```

Activate it and install dependencies:

```bash
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
python seed.py
```

### 6. Run the Bot

```bash
python run.py
```

The Telegram bot runs using polling.

---

## Deployment

The application is implemented as a Telegram polling application and can run on a long-lived Python worker or VM:

```bash
python run.py
```

A publicly hosted always-on instance is **not currently provided**.

For the submitted demo, the bot can be run locally with the configured Telegram and Groq credentials.

---

## Repository

* Repository is private.
* Required reviewers are invited as GitHub collaborators.
* Secrets and `.env` files are excluded from Git.
* Git history contains the project's development progression.

## Project Structure

```text
supermarket-ops-agent/
│
├── app/
│   ├── agent.py
│   ├── bot.py
│   ├── config.py
│   ├── db.py
│   └── tools.py
│
├── run.py
├── seed.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Telegram Bot

**Bot:** `@KiranaOpsSupermarketBot`

Run locally with:

```bash
python run.py
```
