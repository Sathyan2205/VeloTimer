from flask import Flask, send_file, jsonify, request, Response
import requests

app = Flask(__name__)
CLOUD = "http://35.200.234.247:8000"

timer_state  = {"elapsed_ms":0,"running":False,"finished":False,"laps":[],"waiting_set_no":False}
athlete_data = {"athlete_id":None,"athlete_name":""}
setno_data   = {"set_no":None}
keypress     = {"key":None}

def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route("/")
def home():
    return send_file("velotimer.html")

@app.route("/athletes")
def athletes():
    res = requests.get(CLOUD+"/athletes")
    return cors(jsonify(res.json()))

@app.route("/upload", methods=["POST","OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        return cors(Response())
    res = requests.post(CLOUD+"/upload", json=request.get_json())
    return cors(jsonify(res.json()))

@app.route("/state", methods=["GET"])
def get_state():
    return cors(jsonify(timer_state))

@app.route("/state", methods=["POST","OPTIONS"])
def post_state():
    if request.method == "OPTIONS":
        return cors(Response())
    global timer_state
    timer_state = request.get_json()
    return cors(jsonify({"ok":True}))

@app.route("/athlete", methods=["GET"])
def get_athlete():
    return cors(jsonify(athlete_data))

@app.route("/athlete", methods=["POST","OPTIONS"])
def post_athlete():
    if request.method == "OPTIONS":
        return cors(Response())
    global athlete_data
    athlete_data = request.get_json()
    return cors(jsonify({"ok":True}))

@app.route("/setno", methods=["GET"])
def get_setno():
    return cors(jsonify(setno_data))

@app.route("/setno", methods=["POST","OPTIONS"])
def post_setno():
    if request.method == "OPTIONS":
        return cors(Response())
    global setno_data
    setno_data = request.get_json()
    return cors(jsonify({"ok":True}))

@app.route("/keypress", methods=["GET"])
def get_keypress():
    return cors(jsonify(keypress))

@app.route("/keypress", methods=["POST","OPTIONS"])
def post_keypress():
    if request.method == "OPTIONS":
        return cors(Response())
    global keypress
    keypress = request.get_json()
    return cors(jsonify({"ok":True}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
