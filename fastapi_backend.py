from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
import psycopg2
import psycopg2.extras
import hashlib
import secrets
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return psycopg2.connect(
        host="34.47.249.18",
        database="Cycling",
        user="postgres",
        password="Hashlog_123",
        port="5432"
    )

active_tokens = {}
security = HTTPBearer()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return active_tokens[token]

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]+$')

def init_db():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     SERIAL PRIMARY KEY,
            athlete_id  INTEGER REFERENCES athletes(Athlete_ID),
            username    TEXT UNIQUE NOT NULL,
            email       TEXT,
            phone       TEXT,
            password    TEXT NOT NULL
        )
    """)
    # Add columns if upgrading from older schema
    for col, coltype in [("username","TEXT"), ("phone","TEXT")]:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {coltype}")
        except:
            pass
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print("init_db error:", e)

# ── EXISTING ROUTES ────────────────────────────────────────────
@app.get("/")
def home():
    return {"Server Running"}

@app.get("/portal")
def portal():
    return FileResponse("athlete_portal.html")

@app.get("/athletes")
def athletes():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT Athlete_ID, Athlete_Name FROM athletes ORDER BY Athlete_Name")
    rows = cur.fetchall()
    conn.close()
    return rows

@app.post("/upload")
def upload(data: dict):
    conn = get_db()
    cur  = conn.cursor()
    athlete    = data["athlete"]
    set_no     = data["set_no"]
    total_time = data["total_time"]
    laps       = data["laps"]
    for lap in laps:
        cur.execute("""
            INSERT INTO trials(Athlete_ID, Set_No, Lap_No, Lap_Time, Elapsed_Time, Total_Time)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (athlete, set_no, lap["lap_no"], lap["lap_time"], lap["elapsed_time"], total_time))
    conn.commit()
    conn.close()
    return {"stored"}

# ── AUTH ROUTES ────────────────────────────────────────────────
@app.post("/register")
def register(data: dict):
    name     = data.get("name", "").strip()
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    phone    = data.get("phone", "").strip()
    password = data.get("password", "")
    dob      = data.get("dob", "")

    if not name or not username or not password:
        raise HTTPException(status_code=400, detail="Name, username and password are required")

    if not USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, and underscores")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    cur.execute(
        "INSERT INTO athletes(Athlete_Name, Athlete_DOB) VALUES(%s, %s) RETURNING Athlete_ID",
        (name, dob if dob else None)
    )
    athlete_id = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO users(athlete_id, username, email, phone, password) VALUES(%s, %s, %s, %s, %s)",
        (athlete_id, username, email if email else None, phone if phone else None, hash_password(password))
    )

    conn.commit()
    conn.close()
    return {"success": True, "message": "Account created successfully"}

@app.post("/login")
def login(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.user_id, u.athlete_id, u.password, u.username, u.email, u.phone, a.Athlete_Name
        FROM users u
        JOIN athletes a ON u.athlete_id = a.Athlete_ID
        WHERE LOWER(u.username) = LOWER(%s)
    """, (username,))
    user = cur.fetchone()
    conn.close()

    if not user or user["password"] != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_hex(32)
    active_tokens[token] = user["athlete_id"]

    return {
        "token":        token,
        "athlete_id":   user["athlete_id"],
        "athlete_name": user["athlete_name"],
        "username":     user["username"]
    }

@app.post("/logout")
def logout(athlete_id: int = Depends(verify_token),
           credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    active_tokens.pop(token, None)
    return {"success": True}

# ── PROFILE ROUTES ─────────────────────────────────────────────
@app.get("/profile")
def get_profile(athlete_id: int = Depends(verify_token)):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT a.Athlete_Name, a.Athlete_DOB, u.username, u.email, u.phone
        FROM athletes a
        JOIN users u ON u.athlete_id = a.Athlete_ID
        WHERE a.Athlete_ID = %s
    """, (athlete_id,))
    profile = cur.fetchone()
    conn.close()
    return dict(profile)

@app.put("/profile")
def update_profile(data: dict, athlete_id: int = Depends(verify_token)):
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE users SET email = %s, phone = %s WHERE athlete_id = %s",
        (email if email else None, phone if phone else None, athlete_id)
    )
    conn.commit()
    conn.close()
    return {"success": True}

# ── DASHBOARD ROUTES ───────────────────────────────────────────
@app.get("/dashboard")
def dashboard(athlete_id: int = Depends(verify_token)):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT Athlete_Name, Athlete_DOB FROM athletes WHERE Athlete_ID = %s", (athlete_id,))
    athlete = cur.fetchone()

    cur.execute("""
        SELECT Date_of_Trials, Set_No, Lap_No, Lap_Time, Elapsed_Time, Total_Time
        FROM trials
        WHERE Athlete_ID = %s
        ORDER BY Date_of_Trials DESC, Set_No ASC, Lap_No ASC
    """, (athlete_id,))
    trials = cur.fetchall()
    conn.close()

    # Group by date, then by set within date
    dates = {}
    for t in trials:
        date_key = str(t["date_of_trials"])
        if date_key not in dates:
            dates[date_key] = {}
        set_key = t["set_no"]
        if set_key not in dates[date_key]:
            dates[date_key][set_key] = {
                "set_no":     t["set_no"],
                "total_time": t["total_time"],
                "laps":       []
            }
        dates[date_key][set_key]["laps"].append({
            "lap_no":       t["lap_no"],
            "lap_time":     round(t["lap_time"], 3),
            "elapsed_time": round(t["elapsed_time"], 3)
        })

    # Convert to sorted list structure: [{date, sets:[...]}]
    dates_list = []
    for date_key in sorted(dates.keys(), reverse=True):
        sets_list = [dates[date_key][k] for k in sorted(dates[date_key].keys())]
        dates_list.append({"date": date_key, "sets": sets_list})

    all_laps = [l["lap_time"] for d in dates_list for s in d["sets"] for l in s["laps"]]
    all_sessions_count = sum(len(d["sets"]) for d in dates_list)

    stats = {
        "total_sessions": all_sessions_count,
        "total_laps":     len(all_laps),
        "best_lap":       round(min(all_laps), 3) if all_laps else 0,
        "avg_lap":        round(sum(all_laps)/len(all_laps), 3) if all_laps else 0,
        "total_time":     round(sum(s["total_time"] for d in dates_list for s in d["sets"]), 1)
    }

    return {
        "athlete": dict(athlete),
        "stats":   stats,
        "dates":   dates_list
    }

@app.delete("/session")
def delete_session(data: dict, athlete_id: int = Depends(verify_token)):
    date   = data.get("date")
    set_no = data.get("set_no")

    if not date or set_no is None:
        raise HTTPException(status_code=400, detail="date and set_no required")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        DELETE FROM trials
        WHERE Athlete_ID = %s AND Date_of_Trials = %s AND Set_No = %s
    """, (athlete_id, date, set_no))
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/manual-entry")
def manual_entry(data: dict, athlete_id: int = Depends(verify_token)):
    date   = data.get("date")
    set_no = data.get("set_no")
    laps   = data.get("laps", [])

    if not date or set_no is None or not laps:
        raise HTTPException(status_code=400, detail="date, set_no, and laps are required")

    conn = get_db()
    cur  = conn.cursor()

    # Check if this date+set already exists for this athlete
    cur.execute(
        "SELECT 1 FROM trials WHERE Athlete_ID=%s AND Date_of_Trials=%s AND Set_No=%s LIMIT 1",
        (athlete_id, date, set_no)
    )
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="A session already exists for this date and set number")

    elapsed = 0
    total_time = sum(l["lap_time"] for l in laps)
    for i, lap in enumerate(laps):
        elapsed += lap["lap_time"]
        cur.execute("""
            INSERT INTO trials(Date_of_Trials, Athlete_ID, Set_No, Lap_No, Lap_Time, Elapsed_Time, Total_Time)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
        """, (date, athlete_id, set_no, i+1, lap["lap_time"], elapsed, total_time))

    conn.commit()
    conn.close()
    return {"success": True}
