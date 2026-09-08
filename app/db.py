import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    cost_price REAL NOT NULL CHECK(cost_price >= 0),
    sell_price REAL NOT NULL CHECK(sell_price >= 0),
    mrp REAL NOT NULL CHECK(mrp >= 0),
    quantity REAL NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    reorder_level REAL NOT NULL DEFAULT 0 CHECK(reorder_level >= 0),
    gst_rate REAL NOT NULL DEFAULT 0 CHECK(gst_rate >= 0),
    hsn TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    balance REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS khata_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('CREDIT','PAYMENT')),
    amount REAL NOT NULL CHECK(amount > 0),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no TEXT UNIQUE NOT NULL,
    chat_id TEXT NOT NULL,
    subtotal REAL NOT NULL,
    cgst REAL NOT NULL,
    sgst REAL NOT NULL,
    total_tax REAL NOT NULL,
    grand_total REAL NOT NULL,
    payment_mode TEXT NOT NULL,
    payment_reference TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    hsn TEXT NOT NULL,
    unit TEXT NOT NULL,
    qty REAL NOT NULL,
    rate REAL NOT NULL,
    cost_price REAL NOT NULL,
    taxable_value REAL NOT NULL,
    gst_rate REAL NOT NULL,
    cgst REAL NOT NULL,
    sgst REAL NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS preferences (
    owner_key TEXT NOT NULL,
    pref_key TEXT NOT NULL,
    pref_value TEXT NOT NULL,
    PRIMARY KEY(owner_key, pref_key)
);

CREATE TABLE IF NOT EXISTS draft_bills (
    chat_id TEXT PRIMARY KEY,
    payment_mode TEXT,
    payment_reference TEXT,
    finalized INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS draft_items (
    chat_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    qty REAL NOT NULL CHECK(qty > 0),
    PRIMARY KEY(chat_id, sku),
    FOREIGN KEY(chat_id) REFERENCES draft_bills(chat_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS processed_updates (
    update_id TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SEED = [
    ("ATTA5", "Aashirvaad Atta 5kg", "packet", 210, 245, 245, 20, 5, 5, "11010000"),
    ("SALT1", "Tata Salt 1kg", "packet", 22, 28, 28, 20, 5, 5, "25010010"),
    ("BUTTER100", "Amul Butter 100g", "packet", 48, 58, 58, 15, 12, 12, "04051000"),
    ("OIL1", "Fortune Sunflower Oil 1L", "litre", 105, 125, 125, 15, 5, 5, "15121910"),
    ("MAGGI70", "Maggi 70g", "packet", 12, 15, 15, 30, 12, 12, "19023000"),
    ("PARLEG", "Parle-G", "packet", 8, 10, 10, 30, 12, 12, "19053100"),
    ("SURF1", "Surf Excel", "packet", 95, 115, 115, 10, 18, 18, "34029019"),
    ("SUGAR", "Loose Sugar", "kg", 38, 45, 45, 10, 0, 5, "17019990"),
    ("RICE", "Loose Rice", "kg", 48, 60, 60, 10, 0, 5, "10063090"),
    ("DAL", "Loose Dal", "kg", 85, 100, 100, 10, 0, 5, "07134000"),
]

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@contextmanager
def tx():
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with tx() as c:
        c.executescript(SCHEMA)
        for row in SEED:
            c.execute("""INSERT OR IGNORE INTO products
                (sku,name,unit,cost_price,sell_price,mrp,quantity,reorder_level,gst_rate,hsn)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", row)

def get_product(sku_or_name):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE lower(sku)=lower(?) OR lower(name)=lower(?)",
            (sku_or_name, sku_or_name)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def list_products():
    conn = connect()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM products ORDER BY name")]
    finally:
        conn.close()
