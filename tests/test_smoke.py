import os, tempfile
os.environ["DB_PATH"]=tempfile.mktemp(suffix=".db")
from app.db import init_db
from app.billing import add_item, set_payment, show_draft, finalize

def test_bill_flow():
    init_db()
    add_item("chat1","ATTA5",1)
    add_item("chat1","SALT1",2)
    d=show_draft("chat1")
    assert d["grand_total"] > d["subtotal"]
    set_payment("chat1","UPI","TEST-REF")
    sale=finalize("chat1")
    assert sale["bill_no"].startswith("INV-")
    assert sale["payment_mode"]=="UPI"
