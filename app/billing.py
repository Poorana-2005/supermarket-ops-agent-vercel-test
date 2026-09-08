from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from .db import tx, connect

TWOPLACES = Decimal("0.01")

def money(v):
    return Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def gst_split(taxable, gst_rate):
    taxable = money(taxable)
    rate = Decimal(str(gst_rate))
    total = money(taxable * rate / Decimal("100"))
    cgst = money(total / Decimal("2"))
    sgst = money(total - cgst)
    return cgst, sgst

def _ensure_draft(c, chat_id):
    c.execute("""INSERT OR IGNORE INTO draft_bills(chat_id)
                VALUES (?)""", (str(chat_id),))

def add_item(chat_id, sku, qty):
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    with tx() as c:
        _ensure_draft(c, chat_id)
        p = c.execute("SELECT * FROM products WHERE lower(sku)=lower(?) OR lower(name)=lower(?)",
                      (sku, sku)).fetchone()
        if not p:
            raise ValueError("Product not found in stock master.")
        if float(p["sell_price"]) < float(p["cost_price"]):
            raise ValueError(f"Sale blocked: {p['name']} is configured below cost.")
        current = c.execute("SELECT qty FROM draft_items WHERE chat_id=? AND sku=?",
                            (str(chat_id), p["sku"])).fetchone()
        new_qty = qty + (float(current["qty"]) if current else 0)
        if new_qty > float(p["quantity"]):
            raise ValueError(f"Oversell blocked: only {p['quantity']} {p['unit']} of {p['name']} available.")
        c.execute("""INSERT INTO draft_items(chat_id,sku,qty) VALUES(?,?,?)
                     ON CONFLICT(chat_id,sku) DO UPDATE SET qty=excluded.qty""",
                  (str(chat_id), p["sku"], new_qty))
        c.execute("UPDATE draft_bills SET updated_at=CURRENT_TIMESTAMP WHERE chat_id=?", (str(chat_id),))
        return draft(c, chat_id)

def edit_item(chat_id, sku, qty):
    if qty <= 0:
        raise ValueError("Use remove_bill_item to remove an item.")
    with tx() as c:
        _ensure_draft(c, chat_id)
        p = c.execute("SELECT * FROM products WHERE lower(sku)=lower(?) OR lower(name)=lower(?)",
                      (sku, sku)).fetchone()
        if not p:
            raise ValueError("Product not found.")
        if qty > float(p["quantity"]):
            raise ValueError(f"Oversell blocked: only {p['quantity']} {p['unit']} available.")
        c.execute("""INSERT INTO draft_items(chat_id,sku,qty) VALUES(?,?,?)
                     ON CONFLICT(chat_id,sku) DO UPDATE SET qty=excluded.qty""",
                  (str(chat_id), p["sku"], qty))
        return draft(c, chat_id)

def remove_item(chat_id, sku):
    with tx() as c:
        c.execute("DELETE FROM draft_items WHERE chat_id=? AND sku=?", (str(chat_id), sku))
        return draft(c, chat_id)

def set_payment(chat_id, mode, reference):
    mode = mode.upper()
    if mode not in {"CASH","UPI","CARD"}:
        raise ValueError("Payment mode must be Cash, UPI, or Card.")
    if mode in {"UPI","CARD"} and not reference.strip():
        raise ValueError(f"{mode} requires a payment reference.")
    with tx() as c:
        _ensure_draft(c, chat_id)
        c.execute("UPDATE draft_bills SET payment_mode=?, payment_reference=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?",
                  (mode, reference.strip() or "CASH", str(chat_id)))
        return draft(c, chat_id)

def draft(c, chat_id):
    d = c.execute("SELECT * FROM draft_bills WHERE chat_id=?", (str(chat_id),)).fetchone()
    if not d:
        return {"items": [], "payment_mode": None, "payment_reference": None, "subtotal": 0, "cgst": 0, "sgst": 0, "total_tax": 0, "grand_total": 0}
    rows = c.execute("""SELECT di.qty,p.* FROM draft_items di JOIN products p ON p.sku=di.sku
                        WHERE di.chat_id=? ORDER BY p.name""", (str(chat_id),)).fetchall()
    items=[]; subtotal=Decimal("0"); cgst_total=Decimal("0"); sgst_total=Decimal("0")
    for r in rows:
        taxable = money(float(r["sell_price"]) * float(r["qty"]))
        cgst, sgst = gst_split(taxable, r["gst_rate"])
        line_total = money(taxable + cgst + sgst)
        subtotal += taxable; cgst_total += cgst; sgst_total += sgst
        items.append({
            "sku": r["sku"], "name": r["name"], "hsn": r["hsn"], "unit": r["unit"],
            "qty": float(r["qty"]), "rate": float(r["sell_price"]), "cost_price": float(r["cost_price"]),
            "taxable_value": float(taxable), "gst_rate": float(r["gst_rate"]),
            "cgst": float(cgst), "sgst": float(sgst), "line_total": float(line_total)
        })
    total_tax = money(cgst_total + sgst_total)
    grand = money(subtotal + total_tax)
    return {"items": items, "payment_mode": d["payment_mode"], "payment_reference": d["payment_reference"],
            "subtotal": float(money(subtotal)), "cgst": float(money(cgst_total)),
            "sgst": float(money(sgst_total)), "total_tax": float(total_tax), "grand_total": float(grand)}

def show_draft(chat_id):
    conn = connect()
    try:
        return draft(conn, chat_id)
    finally:
        conn.close()

def finalize(chat_id):
    with tx() as c:
        d = c.execute("SELECT * FROM draft_bills WHERE chat_id=?", (str(chat_id),)).fetchone()
        if not d:
            raise ValueError("No draft bill exists.")
        if d["payment_mode"] not in {"CASH","UPI","CARD"}:
            raise ValueError("Payment mode is required before finalizing.")
        if d["payment_mode"] in {"UPI","CARD"} and not d["payment_reference"]:
            raise ValueError("Payment reference is required before finalizing.")

        rows = c.execute("""SELECT di.qty,p.* FROM draft_items di JOIN products p ON p.sku=di.sku
                            WHERE di.chat_id=? ORDER BY p.name""", (str(chat_id),)).fetchall()
        if not rows:
            raise ValueError("Draft bill is empty.")

        subtotal=Decimal("0"); cgst_total=Decimal("0"); sgst_total=Decimal("0"); prepared=[]
        for r in rows:
            qty=Decimal(str(r["qty"]))
            # Critical recheck occurs inside BEGIN IMMEDIATE transaction.
            if qty > Decimal(str(r["quantity"])):
                raise ValueError(f"Oversell blocked at commit: {r['name']} has only {r['quantity']} available.")
            if Decimal(str(r["sell_price"])) < Decimal(str(r["cost_price"])):
                raise ValueError(f"Sale refused: {r['name']} cannot be sold below cost.")
            if Decimal(str(r["sell_price"])) > Decimal(str(r["mrp"])):
                raise ValueError(f"Sale refused: {r['name']} selling price exceeds MRP.")
            taxable=money(Decimal(str(r["sell_price"])) * qty)
            cgst,sgst=gst_split(taxable,r["gst_rate"])
            line_total=money(taxable+cgst+sgst)
            subtotal += taxable; cgst_total += cgst; sgst_total += sgst
            prepared.append((r,qty,taxable,cgst,sgst,line_total))

        total_tax=money(cgst_total+sgst_total)
        grand=money(subtotal+total_tax)
        bill_no="INV-"+datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

        cursor=c.execute("""INSERT INTO sales
            (bill_no,chat_id,subtotal,cgst,sgst,total_tax,grand_total,payment_mode,payment_reference)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (bill_no,str(chat_id),float(money(subtotal)),float(money(cgst_total)),float(money(sgst_total)),
             float(total_tax),float(grand),d["payment_mode"],d["payment_reference"] or "CASH"))
        sale_id=cursor.lastrowid

        for r,qty,taxable,cgst,sgst,line_total in prepared:
            c.execute("""INSERT INTO sale_items
                (sale_id,product_id,sku,name,hsn,unit,qty,rate,cost_price,taxable_value,gst_rate,cgst,sgst,line_total)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sale_id,r["id"],r["sku"],r["name"],r["hsn"],r["unit"],float(qty),float(r["sell_price"]),
                 float(r["cost_price"]),float(taxable),float(r["gst_rate"]),float(cgst),float(sgst),float(line_total)))
            c.execute("UPDATE products SET quantity=quantity-? WHERE id=?", (float(qty),r["id"]))

        # Draft and sale are committed atomically. A retried finalize cannot double-decrement stock.
        c.execute("DELETE FROM draft_items WHERE chat_id=?", (str(chat_id),))
        c.execute("DELETE FROM draft_bills WHERE chat_id=?", (str(chat_id),))
        return get_sale(c, bill_no)

def get_sale(c, bill_no):
    s=c.execute("SELECT * FROM sales WHERE bill_no=?", (bill_no,)).fetchone()
    if not s:
        return None
    items=c.execute("SELECT * FROM sale_items WHERE sale_id=?", (s["id"],)).fetchall()
    out=dict(s); out["items"]=[dict(x) for x in items]
    return out
