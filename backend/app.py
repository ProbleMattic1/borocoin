
import os
import json
import hashlib
import datetime
import time
import hmac
from typing import Optional, List, Literal, Dict
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import sqlite3
import jwt
import io

try:
    import qrcode
except Exception:
    qrcode = None

JWT_ALG = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
DB_PATH = os.getenv("DB_PATH", "rewards.db")

app = FastAPI(title="Township Rewards (Starter Kit)", version="0.3.0 (easy wins)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="backend/templates")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

def db():
    return sqlite3.connect(DB_PATH)

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",",":"))

def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        display_name TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        balance INTEGER NOT NULL DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        ts TEXT NOT NULL,
        ttype TEXT NOT NULL, -- EARN, REDEEM, ISSUE, ADJUST, EXPIRE
        user_id TEXT,
        merchant_id TEXT,
        amount INTEGER NOT NULL,
        prev_hash TEXT,
        thash TEXT NOT NULL,
        note TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS merchants (
        id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS anchors (
        ymd TEXT PRIMARY KEY,
        merkle_root TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        atype TEXT NOT NULL,
        merchant_id TEXT,
        user_id TEXT,
        detail TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    # Add merchant caps columns if missing
    for col, default in [
        ("rate_limit_per_minute", 60),
        ("daily_earn_cap", 100000),
        ("daily_redeem_cap", 100000),
    ]:
        try:
            cur.execute(f"ALTER TABLE merchants ADD COLUMN {col} INTEGER DEFAULT {default}")
        except Exception:
            pass
    # Default settings
    if not cur.execute("SELECT 1 FROM settings WHERE key='expiry_days'").fetchone():
        cur.execute("INSERT INTO settings(key,value) VALUES('expiry_days','0')")
    con.commit()
    con.close()

def seed_demo():
    con = db(); cur = con.cursor()
    existing = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        users = [
            ("admin", "admin", "Program Admin"),
            ("user1", "user", "Alex Johnson"),
            ("user2", "user", "Sam Rivera"),
        ]
        cur.executemany("INSERT INTO users(id, role, display_name) VALUES(?,?,?)", users)
        cur.executemany("INSERT INTO accounts(id, kind, balance) VALUES(?,?,0)",
                        [(u[0], "user") for u in users if u[1]=="user"])
        merchants = [
            ("merchant1", "Sunny Cafe"),
            ("merchant2", "Hillsborough Books")
        ]
        cur.executemany("INSERT INTO merchants(id, display_name) VALUES(?,?)", merchants)
        cur.executemany("INSERT INTO accounts(id, kind, balance) VALUES(?, 'merchant', 0)",
                        [(m[0],) for m in merchants])
        cur.execute("INSERT OR IGNORE INTO accounts(id, kind, balance) VALUES('system', 'system', 0)")
        con.commit()
    con.close()

def hash_tx(payload: dict, prev_hash: Optional[str]) -> str:
    body = {"payload": payload, "prev_hash": prev_hash or ""}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()

def merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return ""
    layer = [bytes.fromhex(h) for h in hashes]
    import hashlib as _h
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i+1] if i+1 < len(layer) else left
            nxt.append(_h.sha256(left + right).digest())
        layer = nxt
    return layer[0].hex()

def get_last_tx_hash(cur) -> Optional[str]:
    r = cur.execute("SELECT thash FROM transactions ORDER BY ts DESC, ROWID DESC LIMIT 1").fetchone()
    return r[0] if r else None

def require_auth(authorization: Optional[str], roles: Optional[List[str]]=None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ",1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    if roles and payload.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return payload

@app.on_event("startup")
def _startup():
    init_db()
    seed_demo()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/auth/login")
def login(body: dict):
    identity = body.get("identity")
    con = db(); cur = con.cursor()
    role = None; display_name = None
    r = cur.execute("SELECT id, role, display_name FROM users WHERE id = ?", (identity,)).fetchone()
    if r:
        role = r[1]; display_name = r[2]
    else:
        r2 = cur.execute("SELECT id, display_name FROM merchants WHERE id = ?", (identity,)).fetchone()
        if r2: role = "merchant"; display_name = r2[1]
    con.close()
    if not role:
        raise HTTPException(status_code=404, detail="Unknown identity")
    token = jwt.encode({"sub": identity, "role": role, "name": display_name}, JWT_SECRET, algorithm=JWT_ALG)
    return {"token": token, "role": role, "name": display_name}

@app.get("/me")
def me(authorization: Optional[str] = Header(None)):
    payload = require_auth(authorization, roles=None)
    return payload

@app.get("/balance/{account_id}")
def get_balance(account_id: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=None)
    con = db(); cur = con.cursor()
    r = cur.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
    con.close()
    if not r: raise HTTPException(status_code=404, detail="Unknown account")
    return {"account_id": account_id, "balance": r[0]}

@app.get("/transactions")
def list_txs(limit: int = 50, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=None)
    con = db(); cur = con.cursor()
    rows = cur.execute("""
        SELECT id, ts, ttype, user_id, merchant_id, amount, prev_hash, thash, note
        FROM transactions ORDER BY ts DESC, ROWID DESC LIMIT ?
    """, (limit,)).fetchall()
    data = []
    for row in rows:
        data.append({
            "id": row[0], "ts": row[1], "ttype": row[2], "user_id": row[3], "merchant_id": row[4],
            "amount": row[5], "prev_hash": row[6], "thash": row[7], "note": row[8]
        })
    con.close()
    return {"transactions": data}

# ---------- Limits & simple fraud ----------
def merchant_limits(cur, merchant_id: str) -> Dict[str,int]:
    r = cur.execute("""
        SELECT rate_limit_per_minute, daily_earn_cap, daily_redeem_cap FROM merchants WHERE id=?
    """, (merchant_id,)).fetchone()
    if not r:
        return {"rate": 60, "earn_cap": 100000, "redeem_cap": 100000}
    return {"rate": r[0] or 60, "earn_cap": r[1] or 100000, "redeem_cap": r[2] or 100000}

def check_rate_and_caps(cur, mid: Optional[str], ttype: str, amount: int):
    if not mid:
        return
    lim = merchant_limits(cur, mid)
    # per-minute rate
    since = (datetime.datetime.utcnow() - datetime.timedelta(seconds=60)).isoformat()
    cnt = cur.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE merchant_id = ? AND ts >= ?
    """, (mid, since)).fetchone()[0]
    if cnt >= lim["rate"]:
        cur.execute("INSERT INTO alerts(ts, atype, merchant_id, detail) VALUES(?,?,?,?)",
                    (datetime.datetime.utcnow().isoformat(), "RATE_LIMIT", mid, f">= {lim['rate']} tx/min"))
        raise HTTPException(status_code=429, detail="Rate limit exceeded for merchant")
    # Daily caps
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    if ttype == "REDEEM":
        s = cur.execute("""
            SELECT COALESCE(SUM(amount),0) FROM transactions
            WHERE merchant_id=? AND ttype='REDEEM' AND DATE(ts)=?
        """, (mid, today)).fetchone()[0]
        if s + amount > lim["redeem_cap"]:
            cur.execute("INSERT INTO alerts(ts, atype, merchant_id, detail) VALUES(?,?,?,?)",
                        (datetime.datetime.utcnow().isoformat(), "REDEEM_CAP", mid, f"cap {lim['redeem_cap']}"))
            raise HTTPException(status_code=429, detail="Daily redeem cap exceeded")
    if ttype == "EARN":
        s = cur.execute("""
            SELECT COALESCE(SUM(amount),0) FROM transactions
            WHERE merchant_id=? AND ttype='EARN' AND DATE(ts)=?
        """, (mid, today)).fetchone()[0]
        if s + amount > lim["earn_cap"]:
            cur.execute("INSERT INTO alerts(ts, atype, merchant_id, detail) VALUES(?,?,?,?)",
                        (datetime.datetime.utcnow().isoformat(), "EARN_CAP", mid, f"cap {lim['earn_cap']}"))
            raise HTTPException(status_code=429, detail="Daily earn cap exceeded")

def fraud_checks(cur, ttype: str, user_id: Optional[str], merchant_id: Optional[str]):
    if ttype != "REDEEM" or not user_id or not merchant_id:
        return
    since = (datetime.datetime.utcnow() - datetime.timedelta(seconds=60)).isoformat()
    cnt = cur.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE ttype='REDEEM' AND user_id=? AND merchant_id=? AND ts >= ?
    """, (user_id, merchant_id, since)).fetchone()[0]
    if cnt >= 5:
        cur.execute("INSERT INTO alerts(ts, atype, merchant_id, user_id, detail) VALUES(?,?,?,?,?)",
                    (datetime.datetime.utcnow().isoformat(), "RAPID_REDEEMS", merchant_id, user_id, f"{cnt} in 60s"))

# ---------- Core tx apply ----------
def apply_tx(cur, ttype: Literal["EARN","REDEEM","ISSUE","ADJUST","EXPIRE"], user_id: Optional[str],
             merchant_id: Optional[str], amount: int, note: Optional[str]):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # verify accounts exist
    if user_id:
        r = cur.execute("SELECT balance FROM accounts WHERE id=? AND kind='user'", (user_id,)).fetchone()
        if not r: raise HTTPException(status_code=404, detail="Unknown user account")
    if merchant_id:
        r = cur.execute("SELECT balance FROM accounts WHERE id=? AND kind='merchant'", (merchant_id,)).fetchone()
        if not r: raise HTTPException(status_code=404, detail="Unknown merchant account")

    check_rate_and_caps(cur, merchant_id, ttype, amount)

    ts = datetime.datetime.utcnow().isoformat()
    prev = get_last_tx_hash(cur)
    payload = {"ts": ts, "ttype": ttype, "user_id": user_id, "merchant_id": merchant_id, "amount": amount, "note": note}
    th = hash_tx(payload, prev)
    tid = th[:16]

    if ttype == "EARN":
        cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, user_id))
    elif ttype == "REDEEM":
        bal = cur.execute("SELECT balance FROM accounts WHERE id=?", (user_id,)).fetchone()[0]
        if bal < amount:
            raise HTTPException(status_code=400, detail="Insufficient user balance")
        cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, user_id))
        cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, merchant_id))
    elif ttype == "ISSUE":
        cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, user_id))
    elif ttype == "EXPIRE":
        bal = cur.execute("SELECT balance FROM accounts WHERE id=?", (user_id,)).fetchone()[0]
        if bal < amount:
            amount = bal
        if amount > 0:
            cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, user_id))
        else:
            return {"id": tid, "hash": th, "note": "no-op"}
    elif ttype == "ADJUST":
        pass

    cur.execute("""
        INSERT INTO transactions(id, ts, ttype, user_id, merchant_id, amount, prev_hash, thash, note)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (tid, ts, ttype, user_id, merchant_id, amount, prev, th, note))

    fraud_checks(cur, ttype, user_id, merchant_id)

    return {"id": tid, "hash": th}

# ---------- Business endpoints ----------
@app.post("/earn")
def earn(body: dict, authorization: Optional[str] = Header(None)):
    auth = require_auth(authorization, roles=["merchant","admin"])
    user_id = body.get("user_id")
    amount = int(body.get("amount", 0))
    note = body.get("note")
    mid = auth.get("sub") if auth.get("role") == "merchant" else None
    con = db(); cur = con.cursor()
    try:
        res = apply_tx(cur, "EARN", user_id=user_id, merchant_id=mid, amount=amount, note=note)
        con.commit()
        return {"status": "ok", "tx": res}
    finally:
        con.close()

@app.post("/redeem")
def redeem(body: dict, authorization: Optional[str] = Header(None)):
    auth = require_auth(authorization, roles=["merchant","admin"])
    user_id = body.get("user_id")
    amount = int(body.get("amount", 0))
    note = body.get("note")
    mid = auth.get("sub") if auth.get("role") == "merchant" else None
    con = db(); cur = con.cursor()
    try:
        res = apply_tx(cur, "REDEEM", user_id=user_id, merchant_id=mid, amount=amount, note=note)
        con.commit()
        return {"status": "ok", "tx": res}
    finally:
        con.close()

@app.post("/admin/issue")
def admin_issue(body: dict, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    user_id = body.get("user_id")
    amount = int(body.get("amount", 0))
    note = body.get("note")
    con = db(); cur = con.cursor()
    try:
        res = apply_tx(cur, "ISSUE", user_id=user_id, merchant_id=None, amount=amount, note=note)
        con.commit()
        return {"status": "ok", "tx": res}
    finally:
        con.close()

@app.get("/merchant/balance")
def merchant_balance(authorization: Optional[str] = Header(None)):
    auth = require_auth(authorization, roles=["merchant","admin"])
    mid = auth.get("sub") if auth.get("role") == "merchant" else None
    if not mid:
        raise HTTPException(status_code=400, detail="Merchant only")
    con = db(); cur = con.cursor()
    r = cur.execute("SELECT balance FROM accounts WHERE id=?", (mid,)).fetchone()
    con.close()
    if not r: raise HTTPException(status_code=404, detail="Unknown merchant account")
    return {"merchant_id": mid, "balance": r[0]}

@app.get("/anchor/daily")
def anchor_daily(date: Optional[str] = None, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    ymd = date or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    con = db(); cur = con.cursor()
    rows = cur.execute("""
        SELECT thash FROM transactions
        WHERE DATE(ts) = ?
        ORDER BY ts ASC, ROWID ASC
    """, (ymd,)).fetchall()
    hashes = [r[0] for r in rows]
    root = merkle_root(hashes)
    cur.execute("INSERT OR REPLACE INTO anchors(ymd, merkle_root, created_at) VALUES(?,?,?)",
                (ymd, root, datetime.datetime.utcnow().isoformat()))
    con.commit(); con.close()
    return {"date": ymd, "merkle_root": root, "tx_count": len(hashes)}

# ---------- QR support ----------
def make_user_qr_payload(uid: str, ttl_seconds: int = 300) -> dict:
    now = int(time.time())
    exp = now + ttl_seconds
    nonce = os.urandom(8).hex()
    data = {"uid": uid, "exp": exp, "nonce": nonce}
    msg = canonical(data).encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    data["sig"] = sig
    return data

def verify_user_qr_payload(data: dict) -> bool:
    try:
        sig = data.get("sig")
        check = data.copy(); check.pop("sig", None)
        msg = canonical(check).encode("utf-8")
        exp_ok = int(check.get("exp", 0)) >= int(time.time())
        good_sig = hmac.new(JWT_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest() == sig
        return exp_ok and good_sig
    except Exception:
        return False

@app.get("/qr/user/{uid}")
def user_qr_json(uid: str, ttl: int = 300, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=None)
    payload = make_user_qr_payload(uid, ttl_seconds=ttl)
    return {"payload": payload, "canonical": canonical(payload)}

@app.get("/qr/user/{uid}.png")
def user_qr_png(uid: str, ttl: int = 300, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=None)
    if qrcode is None:
        raise HTTPException(status_code=500, detail="qrcode library not installed")
    payload = make_user_qr_payload(uid, ttl_seconds=ttl)
    text = "boro://user?d=" + canonical(payload)
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.post("/qr/verify")
def qr_verify(body: dict, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["merchant","admin"])
    try:
        raw = body.get("d")
        data = json.loads(raw) if isinstance(raw, str) else body.get("payload")
        ok = verify_user_qr_payload(data)
        return {"ok": ok, "uid": data.get("uid") if ok else None}
    except Exception:
        return {"ok": False, "uid": None}

# ---------- Admin settings, caps, settlement, expiry ----------
@app.get("/admin/settings")
def get_settings(authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    con = db(); cur = con.cursor()
    rows = cur.execute("SELECT key, value FROM settings").fetchall()
    con.close()
    return {k:v for k,v in rows}

@app.post("/admin/settings")
def set_settings(body: dict, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    con = db(); cur = con.cursor()
    for k, v in body.items():
        cur.execute("INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))
    con.commit(); con.close()
    return {"status": "ok"}

@app.post("/admin/merchant/config")
def set_merchant_config(body: dict, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    mid = body.get("merchant_id")
    rate = int(body.get("rate_limit_per_minute", 60))
    ecap = int(body.get("daily_earn_cap", 100000))
    rcap = int(body.get("daily_redeem_cap", 100000))
    con = db(); cur = con.cursor()
    r = cur.execute("SELECT 1 FROM merchants WHERE id=?", (mid,)).fetchone()
    if not r: raise HTTPException(status_code=404, detail="Unknown merchant")
    cur.execute("""UPDATE merchants SET rate_limit_per_minute=?, daily_earn_cap=?, daily_redeem_cap=? WHERE id=?""",
                (rate, ecap, rcap, mid))
    con.commit(); con.close()
    return {"status":"ok"}

@app.get("/admin/settlement.csv")
def settlement_csv(date_from: str, date_to: str, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    con = db(); cur = con.cursor()
    rows = cur.execute("""
        SELECT m.id, m.display_name,
               COALESCE(SUM(CASE WHEN t.ttype='REDEEM' THEN t.amount ELSE 0 END),0) as redeemed_total,
               COUNT(CASE WHEN t.ttype='REDEEM' THEN 1 END) as redeem_count
        FROM merchants m
        LEFT JOIN transactions t ON m.id = t.merchant_id AND DATE(t.ts) BETWEEN ? AND ?
        GROUP BY m.id, m.display_name
        ORDER BY redeemed_total DESC
    """, (date_from, date_to)).fetchall()
    con.close()
    lines = ["merchant_id,merchant_name,redeemed_total,redeem_count"]
    for r in rows:
        lines.append(f"{r[0]},{str(r[1]).replace(',',' ')},{r[2]},{r[3]}")
    csv = "\n".join(lines)
    return PlainTextResponse(csv, media_type="text/csv")

def fifo_expirable_amount_for_user(cur, uid: str, cutoff_iso: str) -> int:
    earns = cur.execute("""
        SELECT ts, amount FROM transactions
        WHERE user_id=? AND ttype IN ('EARN','ISSUE') ORDER BY ts ASC, ROWID ASC
    """, (uid,)).fetchall()
    redeems = cur.execute("""
        SELECT ts, amount FROM transactions
        WHERE user_id=? AND ttype='REDEEM' ORDER BY ts ASC, ROWID ASC
    """, (uid,)).fetchall()
    lots = [{"ts": e[0], "remaining": e[1]} for e in earns]
    for ts_r, amt_r in redeems:
        need = amt_r
        for lot in lots:
            if need == 0: break
            take = min(lot["remaining"], need)
            lot["remaining"] -= take
            need -= take
    expirable = 0
    for lot in lots:
        if lot["ts"] <= cutoff_iso:
            expirable += max(lot["remaining"], 0)
    return expirable

@app.post("/admin/expire/run")
def run_expiry(authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    con = db(); cur = con.cursor()
    days = int(cur.execute("SELECT value FROM settings WHERE key='expiry_days'").fetchone()[0])
    if days <= 0:
        con.close()
        return {"status":"disabled"}
    cutoff_dt = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    cutoff_iso = cutoff_dt.isoformat()
    users = cur.execute("SELECT id FROM accounts WHERE kind='user'").fetchall()
    summary = {}
    for (uid,) in users:
        amt = fifo_expirable_amount_for_user(cur, uid, cutoff_iso)
        if amt > 0:
            res = apply_tx(cur, "EXPIRE", user_id=uid, merchant_id=None, amount=amt, note=f"expiry>{days}d")
            summary[uid] = amt
    con.commit(); con.close()
    return {"status":"ok", "cutoff": cutoff_iso, "expired": summary}

@app.get("/admin/alerts")
def list_alerts(limit: int = 50, authorization: Optional[str] = Header(None)):
    require_auth(authorization, roles=["admin"])
    con = db(); cur = con.cursor()
    rows = cur.execute("SELECT ts, atype, merchant_id, user_id, detail FROM alerts ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return {"alerts": [{"ts":r[0],"type":r[1],"merchant_id":r[2],"user_id":r[3],"detail":r[4]} for r in rows]}
