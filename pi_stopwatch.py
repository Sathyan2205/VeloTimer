import time
import tm1637
from gpiozero import Buzzer
from gpiozero import Button
import csv
from datetime import datetime
import sqlite3
import requests
import threading
import os

# ── State pushed to webpage ───────────────────────────────────
state = {
    "running": False,
    "finished": False,
    "elapsed_ms": 0,
    "laps": [],
    "waiting_set_no": False,
    "keypress": None
}

def push_loop():
    while True:
        try:
            requests.post("http://localhost:3000/state", json=state, timeout=0.05)
        except:
            pass
        time.sleep(0.1)

threading.Thread(target=push_loop, daemon=True).start()

# ── Hardware setup ────────────────────────────────────────────
button = None
while button is None:
    try:
        button = Button(16, bounce_time=0.05)
    except Exception as e:
        print("GPIO busy, retrying in 3 seconds...", e)
        time.sleep(3)

buzzer  = Buzzer(4)
display = tm1637.TM1637(clk=17, dio=27)

def fmt(ms):
    cs = int(ms / 10)
    m  = cs // 6000
    s  = (cs % 6000) // 100
    c  = cs % 100
    return f"{m:02d}:{s:02d}.{c:02d}"

def get_keypress():
    """Read and clear keypress from serve.py"""
    try:
        r = requests.get("http://localhost:3000/keypress", timeout=0.05)
        data = r.json()
        key = data.get("key")
        if key:
            requests.post("http://localhost:3000/keypress",
                         json={"key": None}, timeout=0.05)
        return key
    except:
        return None

# ═══════════════════════════════════════════════════
# MAIN SESSION LOOP — runs forever until Pi turns off
# ═══════════════════════════════════════════════════
while True:

    # ── Reset everything for new session ─────────────
    state["running"]        = False
    state["finished"]       = False
    state["elapsed_ms"]     = 0
    state["laps"]           = []
    state["waiting_set_no"] = False
    state["keypress"]       = None

    # ── Reset athlete and setno on serve.py ──────────
    try:
        requests.post("http://localhost:3000/athlete",
                      json={"athlete_id": None, "athlete_name": ""}, timeout=1)
        requests.post("http://localhost:3000/setno",
                      json={"set_no": None}, timeout=1)
        requests.post("http://localhost:3000/keypress",
                      json={"key": None}, timeout=1)
    except:
        pass

    # ── Wait for athlete selection from webpage ───────
    print("Waiting for athlete selection on webpage...")
    athno    = None
    ath_name = ""
    while athno is None:
        try:
            r    = requests.get("http://localhost:3000/athlete", timeout=1)
            data = r.json()
            if data.get("athlete_id"):
                athno    = data["athlete_id"]
                ath_name = data.get("athlete_name", "")
                print("Athlete selected:", ath_name)
        except:
            pass
        time.sleep(0.5)

    # ── Setup for this session ────────────────────────
    today    = datetime.today()
    now      = str(today)
    fields   = ["Athlete Number", "Total Time"]
    ath      = str(athno)
    filename = now + "_" + "athlete_" + ath + ".csv"

    # ── Countdown ─────────────────────────────────────
    for i in range(10, -1, -1):
        if i == 10:
            display.number(i)
            buzzer.on()
            time.sleep(1)
            buzzer.off()
        elif i > 3 and i < 10:
            display.number(i)
            time.sleep(1)
        elif i <= 3 and i >= 1:
            buzzer.on()
            time.sleep(0.1)
            display.number(i)
            buzzer.off()
            time.sleep(0.9)
        elif i == 0:
            display.number(i)
            buzzer.on()
            time.sleep(1)
            buzzer.off()

    # ── Stopwatch variables ───────────────────────────
    start_time    = time.monotonic()
    s_running     = True
    elapsed_time  = 0
    lap_time      = 0
    laps          = []
    x             = elapsed_time
    elapsed_times = []
    total_time    = 0
    session_done  = False
    pause_pressed = False  # ← flag set by GPIO button

    # ── GPIO button: sets flag, main loop handles it ──
    def toggle_pause():
        global pause_pressed
        pause_pressed = True
        print("Button pressed")

    button.when_pressed = toggle_pause
    state["running"] = True
    time.sleep(1)

    print("Stopwatch running. Use webpage keyboard or GPIO button.")

    # ── Main stopwatch loop ───────────────────────────
    while not session_done:

        # ── Handle pause flag from GPIO button ────────
        if pause_pressed:
            pause_pressed = False
            s_running = not s_running
            if not s_running:
                start_time = time.monotonic() - elapsed_time
            else:
                start_time = time.monotonic() - elapsed_time
            print("Running:", s_running)

        # ── Handle keypress from webpage ──────────────
        key = get_keypress()

        if key == "q":
            laps.append(lap_time)
            elapsed_times.append(elapsed_time)
            state["laps"].append({
                "lap_no":   len(laps),
                "lap_time": fmt(int(lap_time * 1000)),
                "lap_ms":   int(lap_time * 1000)
            })
            total_time              = elapsed_time
            state["finished"]       = False
            state["running"]        = False
            state["waiting_set_no"] = True
            session_done = True

        elif key == "l":
            lap_no = len(laps) + 1
            laps.append(lap_time)
            elapsed_times.append(elapsed_time)
            state["laps"].append({
                "lap_no":   lap_no,
                "lap_time": fmt(int(lap_time * 1000)),
                "lap_ms":   int(lap_time * 1000)
            })
            x = elapsed_time
            print(f"Lap {lap_no}: {fmt(int(lap_time*1000))}")

        elif key == "r":
            start_time    = time.monotonic()
            elapsed_time  = 0
            s_running     = True
            state["elapsed_ms"] = 0
            state["laps"]       = []
            laps          = []
            elapsed_times = []
            x             = 0

        elif key == "space":
            pause_pressed = True

        if s_running and not session_done:
            elapsed_time = time.monotonic() - start_time
            lap_time     = elapsed_time - x

        state["elapsed_ms"] = int(elapsed_time * 1000)
        state["running"]    = s_running

        display.number(int(elapsed_time * 100))
        time.sleep(0.01)

    # ── Wait for set number from webpage ─────────────
    print("Waiting for set number from webpage...")
    set_no = None
    while set_no is None:
        try:
            r    = requests.get("http://localhost:3000/setno", timeout=1)
            data = r.json()
            if data.get("set_no"):
                set_no = data["set_no"]
                print("Set number received:", set_no)
        except:
            pass
        time.sleep(0.5)

    # ── Save to SQLite ────────────────────────────────
    conn = sqlite3.connect("Training.db")
    cur  = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS trials(Date_of_Trials TEXT DEFAULT CURRENT_DATE, Athlete_ID INTEGER, Set_No INTEGER, Lap_No INTEGER, Lap_Time REAL, Elapsed_Time REAL, Total_Time REAL, PRIMARY KEY(Date_of_Trials,Athlete_ID,Set_No,Lap_No))")
    for i in range(len(laps)):
        cur.execute("INSERT INTO trials(Athlete_ID,Set_No,Lap_No,Lap_Time,Elapsed_Time,Total_Time) VALUES(?,?,?,?,?,?)",
                    (athno, set_no, i+1, laps[i], elapsed_times[i], total_time))
    conn.commit()
    conn.close()

    # ── Upload to cloud ───────────────────────────────
    records = [{"lap_no":i+1,"lap_time":laps[i],"elapsed_time":elapsed_times[i]} for i in range(len(laps))]
    data    = {"athlete":athno,"set_no":set_no,"total_time":total_time,"laps":records}
    try:
        response = requests.post("http://35.200.234.247:8000/upload", json=data)
        print(response.json())
    except Exception as e:
        print("Upload error:", e)

    # ── Save CSV ──────────────────────────────────────
    for i in range(len(laps)):
        fields.append("Lap"+str(i+1))
    csvlist = [athno, total_time] + laps
    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fields)
        writer.writerow(csvlist)

    # ── Tell webpage session is fully done ────────────
    state["finished"]       = True
    state["waiting_set_no"] = False

    print("Session done! Looping back to athlete selection...")
    time.sleep(3)

    # Loop back to top — new session begins
