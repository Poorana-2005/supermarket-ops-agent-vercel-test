from agents import function_tool
from .db import tx, connect, get_product
from .billing import add_item, edit_item, remove_item, show_draft, set_payment, finalize
from .artifacts import create_invoice, create_analysis_deck
from typing import Optional

@function_tool
def receive_stock(
    sku: str,
    quantity: float,
    cost_price: Optional[float] = None
) -> str:
    """Receive inventory for an existing SKU. Optionally update the cost price."""

    if quantity <= 0:
        return "Quantity must be positive."

    if cost_price is not None and cost_price < 0:
        return "Cost price cannot be negative."

    with tx() as c:
        p = c.execute(
            "SELECT * FROM products WHERE lower(sku)=lower(?)",
            (sku,)
        ).fetchone()

        if not p:
            return "SKU not found. Use stock query first."

        new_quantity = p["quantity"] + quantity

        if cost_price is not None:
            c.execute(
                """
                UPDATE products
                SET quantity = quantity + ?,
                    cost_price = ?
                WHERE id = ?
                """,
                (quantity, cost_price, p["id"])
            )

            return (
                f"Received {quantity:g} {p['unit']} of {p['name']}. "
                f"New stock: {new_quantity:g} {p['unit']}. "
                f"Cost price updated to Rs {cost_price:.2f} per {p['unit']}."
            )

        else:
            c.execute(
                """
                UPDATE products
                SET quantity = quantity + ?
                WHERE id = ?
                """,
                (quantity, p["id"])
            )

            return (
                f"Received {quantity:g} {p['unit']} of {p['name']}. "
                f"New stock: {new_quantity:g} {p['unit']}. "
                f"Cost price remains Rs {p['cost_price']:.2f} per {p['unit']}."
            )

@function_tool
def add_new_product(sku: str, name: str, unit: str, cost_price: float, sell_price: float,
                    mrp: float, quantity: float, reorder_level: float, gst_rate: float, hsn: str):
    """Add a product to the store master. Selling price must be between cost and MRP."""
    if sell_price < cost_price:return "Refused: selling price cannot be below cost price."
    if sell_price > mrp: return "Refused: selling price cannot exceed mrp."
    if quantity < 0 or reorder_level < 0 or gst_rate < 0: return "Invalid quantity/reorder/GST."
    with tx() as c:
        try:
            c.execute("""INSERT INTO products
                (sku,name,unit,cost_price,sell_price,mrp,quantity,reorder_level,gst_rate,hsn)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (sku,name,unit,cost_price,sell_price,mrp,quantity,reorder_level,gst_rate,hsn))
        except Exception as e:
            return f"Could not add product: {e}"
    return f"Added {name} ({sku}) with {quantity} {unit} in stock."

@function_tool
def check_stock(query: str = "") -> str:
    """Check exact product stock or list the stock master."""
    conn=connect()
    try:
        if query:
            rows=conn.execute("""SELECT * FROM products WHERE lower(sku)=lower(?) OR lower(name) LIKE '%'||lower(?)||'%'""",(query,query)).fetchall()
        else:
            rows=conn.execute("SELECT * FROM products ORDER BY name").fetchall()
        if not rows: return "No matching product."
        return "\n".join(f"{r['sku']} | {r['name']} | "f"{r['quantity']} {r['unit']} | "f"cost ₹{r['cost_price']:.2f} | "f"sell ₹{r['sell_price']:.2f} | "f"MRP ₹{r['mrp']:.2f} | "f"GST {r['gst_rate']}% | "f"HSN {r['hsn']}"for r in rows)
    finally: conn.close()

@function_tool
def low_stock(request: str = "") -> str:
    """Show products at or below their reorder level. The request parameter can be left empty."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE quantity <= reorder_level ORDER BY quantity"
        ).fetchall()

        if not rows:
            return "No low-stock items."

        return "\n".join(
            f"{r['sku']} | {r['name']} | {r['quantity']} {r['unit']} left | "
            f"reorder at {r['reorder_level']}"
            for r in rows
        )
    finally:
        conn.close()

@function_tool
def add_bill_item(chat_id: str, sku: str, quantity: float) -> str:
    """Add an item to the current multi-turn draft bill. Does not decrement stock."""
    try: return str(add_item(chat_id,sku,quantity))
    except Exception as e: return f"Bill item not added: {e}"

@function_tool
def edit_bill_item(chat_id: str, sku: str, quantity: float) -> str:
    """Change the quantity of an existing draft bill item."""
    try: return str(edit_item(chat_id,sku,quantity))
    except Exception as e: return f"Bill edit failed: {e}"

@function_tool
def remove_bill_item(chat_id: str, sku: str) -> str:
    """Remove an item from the current draft only; inventory is unchanged."""
    try: return str(remove_item(chat_id,sku))
    except Exception as e: return f"Bill removal failed: {e}"

@function_tool
def show_current_bill(chat_id: str) -> str:
    """Show the current draft bill with GST breakdown. Stock is not decremented."""
    return str(show_draft(chat_id))

@function_tool
def set_bill_payment(chat_id: str, payment_mode: str, payment_reference: str = "") -> str:
    """Set Cash/UPI/Card and reference on the current draft."""
    try: return str(set_payment(chat_id,payment_mode,payment_reference))
    except Exception as e: return f"Payment setup failed: {e}"

@function_tool
def finalize_current_bill(chat_id: str) -> str:
    """Finalize the current bill. Rechecks stock and cost inside one database transaction."""
    try:
        sale=finalize(chat_id)
        return f"FINALIZED {sale['bill_no']} | total ₹{sale['grand_total']:.2f} | {sale['payment_mode']} | reference {sale['payment_reference']}"
    except Exception as e:
        return f"FINALIZE REFUSED: {e}"

@function_tool
def get_customer_balance(name: str) -> str:
    """Get a customer's khata balance."""
    conn=connect()
    try:
        r=conn.execute("SELECT * FROM customers WHERE lower(name)=lower(?)",(name,)).fetchone()
        if not r: return f"No khata account exists for {name}."
        return f"{r['name']} balance: ₹{r['balance']:.2f}"
    finally: conn.close()

@function_tool
def add_credit(name: str, amount: float, note: str = "") -> str:
    """Put a positive amount on a customer's khata."""
    if amount<=0: return "Amount must be positive."
    with tx() as c:
        c.execute("INSERT OR IGNORE INTO customers(name,balance) VALUES(?,0)",(name,))
        r=c.execute("SELECT id,balance FROM customers WHERE lower(name)=lower(?)",(name,)).fetchone()
        c.execute("UPDATE customers SET balance=balance+? WHERE id=?",(amount,r["id"]))
        c.execute("INSERT INTO khata_transactions(customer_id,kind,amount,note) VALUES(?,?,?,?)",(r["id"],"CREDIT",amount,note))
        new=r["balance"]+amount
    return f"Added ₹{amount:.2f} credit for {name}. Balance: ₹{new:.2f}"

@function_tool
def settle_credit(name: str, amount: float, note: str = "") -> str:
    """Record a customer's khata payment; refuses nonexistent accounts and overpayment."""
    if amount<=0: return "Amount must be positive."
    with tx() as c:
        r=c.execute("SELECT id,balance FROM customers WHERE lower(name)=lower(?)",(name,)).fetchone()
        if not r: return f"Refused: no khata account exists for {name}."
        if amount > r["balance"] + 0.0001: return f"Refused: payment ₹{amount:.2f} exceeds balance ₹{r['balance']:.2f}."
        c.execute("UPDATE customers SET balance=balance-? WHERE id=?",(amount,r["id"]))
        c.execute("INSERT INTO khata_transactions(customer_id,kind,amount,note) VALUES(?,?,?,?)",(r["id"],"PAYMENT",amount,note))
        new=r["balance"]-amount
    return f"{name} paid ₹{amount:.2f}. Balance: ₹{new:.2f}"

@function_tool
def daily_close(date_yyyy_mm_dd: str = "") -> str:
    """Return today's daily close by default, using finalized sales only.If the user asks for today's close, today's sales, or daily close withouta date, call this tool with date_yyyy_mm_dd="".Only ask for a date when the user explicitly provides a different date."""
    conn=connect()
    try:
        where="date(created_at)=date('now','localtime')" if not date_yyyy_mm_dd else "date(created_at)=?"
        args=() if not date_yyyy_mm_dd else (date_yyyy_mm_dd,)
        s=conn.execute(f"SELECT COALESCE(SUM(grand_total),0) total,COALESCE(SUM(total_tax),0) tax,COUNT(*) bills FROM sales WHERE {where}",args).fetchone()
        pays=conn.execute(f"SELECT payment_mode,COALESCE(SUM(grand_total),0) total FROM sales WHERE {where} GROUP BY payment_mode",args).fetchall()
        top=conn.execute(f"""SELECT name,SUM(qty) qty FROM sale_items si JOIN sales s ON s.id=si.sale_id
                             WHERE {where} GROUP BY name ORDER BY qty DESC LIMIT 5""",args).fetchall()
        return str({"total":s["total"],"tax":s["tax"],"bills":s["bills"],
                    "payments":{p["payment_mode"]:p["total"] for p in pays},
                    "top_items":[dict(x) for x in top]})
    finally: conn.close()

@function_tool
def create_pdf_invoice(bill_no: str) -> str:
    """Create a real GST-style PDF invoice for an already finalized bill."""
    conn=connect()
    try:
        sale=conn.execute("SELECT * FROM sales WHERE bill_no=?",(bill_no,)).fetchone()
        if not sale: return "Bill not found."
        items=conn.execute("SELECT * FROM sale_items WHERE sale_id=?",(sale["id"],)).fetchall()
        data=dict(sale); data["items"]=[dict(x) for x in items]
    finally: conn.close()
    return "FILE_CREATED:"+create_invoice(data)

@function_tool
def create_pptx_analysis(date_yyyy_mm_dd: str = "") -> str:
    """Create a real PPTX analysis deck with a revenue chart and operational insights."""
    conn = connect()
    try:
        if not date_yyyy_mm_dd:
            where = """date(created_at) >= date('now','localtime','-6 days')
                       AND date(created_at) <= date('now','localtime')"""
            args = ()
        else:
            where = "date(created_at)=?"
            args = (date_yyyy_mm_dd,)

        daily_rows = conn.execute(f"""
            SELECT date(created_at) day,
                   COALESCE(SUM(grand_total), 0) revenue
            FROM sales
            WHERE {where}
            GROUP BY date(created_at)
            ORDER BY day
        """, args).fetchall()

        daily_map = {
            row["day"]: float(row["revenue"])
            for row in daily_rows
        }

        from datetime import date, timedelta

        today = date.today()
        daily = []

        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.isoformat()

            daily.append({
                "day": day_str,
                "revenue": daily_map.get(day_str, 0)
            })

        top = conn.execute(f"""
            SELECT si.name, SUM(si.qty) qty
            FROM sale_items si
            JOIN sales s ON s.id=si.sale_id
            WHERE {where}
            GROUP BY si.name
            ORDER BY qty DESC
            LIMIT 5
        """, args).fetchall()

        s = conn.execute(f"""
            SELECT COALESCE(SUM(grand_total), 0) total,
                   COALESCE(SUM(total_tax), 0) tax
            FROM sales
            WHERE {where}
        """, args).fetchone()

        pays = conn.execute(f"""
            SELECT payment_mode,
                   COALESCE(SUM(grand_total), 0) total
            FROM sales
            WHERE {where}
            GROUP BY payment_mode
        """, args).fetchall()

        low = conn.execute("""
            SELECT COUNT(*) n
            FROM products
            WHERE quantity <= reorder_level
        """).fetchone()

        summary = {
            "daily": [dict(x) for x in daily],
            "top_items": [dict(x) for x in top],
            "total": s["total"],
            "tax": s["tax"],
            "payments": {
                p["payment_mode"]: p["total"]
                for p in pays
            },
            "low_stock_count": low["n"]
        }

    finally:
        conn.close()

    return "FILE_CREATED:" + create_analysis_deck(summary)

@function_tool
def set_owner_preference(owner_key: str, key: str, value: str) -> str:
    """Persist an owner preference across /new and bot restarts."""
    allowed={"default_payment","default_product","shop_name"}
    if key not in allowed: return "Unsupported preference."
    with tx() as c:
        c.execute("""INSERT INTO preferences(owner_key,pref_key,pref_value) VALUES(?,?,?)
                     ON CONFLICT(owner_key,pref_key) DO UPDATE SET pref_value=excluded.pref_value""",
                  (owner_key,key,value))
    return f"Saved preference {key}={value}."

@function_tool
def get_owner_preferences(owner_key: str) -> str:
    """Read persisted owner preferences."""
    conn=connect()
    try:
        rows=conn.execute("SELECT pref_key,pref_value FROM preferences WHERE owner_key=?",(owner_key,)).fetchall()
        return str({r["pref_key"]:r["pref_value"] for r in rows})
    finally: conn.close()
