import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Disaster Backend is running!"
    @app.route('/predict', methods=['POST'])
def predict():
    # your prediction code
    return jsonify({"result": "success"})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
DB_FILE = os.path.join(DATA_DIR, 'incidents.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _load():
    if not os.path.exists(DB_FILE):
        return {"reports": []}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"reports": []}

def _save(data):
    tmp = DB_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(tmp, DB_FILE)

def _now():
    return datetime.utcnow().isoformat() + 'Z'

@app.route('/uploads/<path:name>')
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)

@app.route('/api/incidents', methods=['GET'])
def list_incidents():
    data = _load()
    category = request.args.get('category')
    status = request.args.get('status')
    active = request.args.get('active')
    device = request.args.get('reportedByDeviceId')
    res = data["reports"]
    if category:
        res = [r for r in res if r.get('category') == category]
    if status:
        res = [r for r in res if r.get('status') == status]
    if active == '1':
        res = [r for r in res if r.get('status') != 'Resolved']
    if device:
        res = [r for r in res if r.get('reportedByDeviceId') == device]
    res.sort(key=lambda r: r.get('createdAt',''), reverse=True)
    return jsonify({"reports": res})

@app.route('/api/incidents', methods=['POST'])
def create_incident():
    data = _load()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category') or 'Other'
    department = request.form.get('department') or None
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    device = request.form.get('reportedByDeviceId')
    image = request.files.get('image')
    image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, name)
        image.save(path)
        image_url = f"/uploads/{name}"
    loc = None
    try:
        if lat and lng:
            loc = {"lat": float(lat), "lng": float(lng)}
    except Exception:
        loc = None
    r = {
        "id": uuid.uuid4().hex,
        "title": title,
        "description": description,
        "category": category,
        "department": department,
        "location": loc,
        "imageUrl": image_url,
        "status": "Reported",
        "createdAt": _now(),
        "updatedAt": _now(),
        "reportedByDeviceId": device,
    }
    data["reports"].append(r)
    _save(data)
    return jsonify(r), 201

@app.route('/api/incidents/<id>', methods=['PATCH'])
def update_incident(id):
    data = _load()
    body = request.get_json(force=True, silent=True) or {}
    for r in data["reports"]:
        if r.get('id') == id:
            if 'status' in body:
                r['status'] = body['status']
            if 'department' in body:
                r['department'] = body['department'] or None
            r['updatedAt'] = _now()
            _save(data)
            return jsonify(r)
    return jsonify({"error": "not_found"}), 404

@app.route('/api/incidents/<id>', methods=['DELETE'])
def delete_incident(id):
    data = _load()
    before = len(data["reports"])
    data["reports"] = [r for r in data["reports"] if r.get('id') != id]
    _save(data)
    return jsonify({"deleted": before - len(data["reports"])})

@app.route('/api/analytics/monthly', methods=['GET'])
def monthly():
    data = _load()
    now = datetime.utcnow()
    m = now.month
    y = now.year
    cats = ["Fire","Flood","Accident","Electricity","Medical","Other"]
    counts = {c: 0 for c in cats}
    for r in data["reports"]:
        try:
            d = datetime.fromisoformat(r.get('createdAt','').replace('Z',''))
            if d.month == m and d.year == y:
                c = r.get('category') or 'Other'
                if c not in counts:
                    counts[c] = 0
                counts[c] += 1
        except Exception:
            continue
    return jsonify({"month": m, "year": y, "counts": counts})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)


