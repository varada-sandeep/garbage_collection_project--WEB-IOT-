from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    flash,
    session,
)
import json
import os
from datetime import datetime
from functools import wraps
from config import APP_CONFIG, DATA_CONFIG, ALERT_THRESHOLDS, AUTH_CONFIG

app = Flask(__name__)
app.secret_key = APP_CONFIG["SECRET_KEY"]

# Data file paths
DATA_DIR = os.environ.get("DATA_DIR", DATA_CONFIG["DATA_DIR"])
WORKERS_FILE = os.path.join(DATA_DIR, DATA_CONFIG["WORKERS_FILE"])
ALERTS_FILE = os.path.join(DATA_DIR, DATA_CONFIG["ALERTS_FILE"])
ASSIGNMENTS_FILE = os.path.join(DATA_DIR, DATA_CONFIG["ASSIGNMENTS_FILE"])
# Create data directory if it doesn't exist
BINS_FILE = os.path.join(DATA_DIR, DATA_CONFIG["BINS_FILE"])
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# Initialize data files if they don't exist
def initialize_json_file(file_path, initial_data):
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(initial_data, f)


# Initialize workers.json
initialize_json_file(WORKERS_FILE, {"workers": []})

# Initialize alerts.json
initialize_json_file(ALERTS_FILE, {"alerts": []})

# Initialize assignments.json
initialize_json_file(ASSIGNMENTS_FILE, {"assignments": []})


# Helper functions to read and write JSON data
def read_json(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is corrupted, return an empty structure
        if file_path == WORKERS_FILE:
            return {"workers": []}
        elif file_path == ALERTS_FILE:
            return {"alerts": []}
        elif file_path == ASSIGNMENTS_FILE:
            return {"assignments": []}
        return {}


def write_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


# Add current datetime to all templates
@app.context_processor
def inject_now():
    return {"now": datetime.now()}


# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            flash("Please log in first.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route("/")
@login_required
def dashboard():
    alerts = read_json(ALERTS_FILE)["alerts"]
    workers = read_json(WORKERS_FILE)["workers"]
    assignments = read_json(ASSIGNMENTS_FILE)["assignments"]

    # Count alerts by severity
    alert_counts = {
        "low": sum(
            1
            for alert in alerts
            if alert["severity"] == "low" and alert["status"] == "active"
        ),
        "moderate": sum(
            1
            for alert in alerts
            if alert["severity"] == "moderate" and alert["status"] == "active"
        ),
        "high": sum(
            1
            for alert in alerts
            if alert["severity"] == "high" and alert["status"] == "active"
        ),
    }

    # Count workers by status
    worker_counts = {
        "available": sum(1 for worker in workers if worker["status"] == "available"),
        "assigned": sum(1 for worker in workers if worker["status"] == "assigned"),
        "on_leave": sum(1 for worker in workers if worker["status"] == "on_leave"),
    }

    # Prepare config for template
    template_config = {
        "DASHBOARD_REFRESH_INTERVAL": APP_CONFIG.get(
            "DASHBOARD_REFRESH_INTERVAL", 30000
        )
    }

    return render_template(
        "dashboard.html",
        alert_counts=alert_counts,
        worker_counts=worker_counts,
        active_alerts=sorted(
            [a for a in alerts if a["status"] == "active"],
            key=lambda x: {"high": 0, "moderate": 1, "low": 2}[x["severity"]],
        ),
        config=template_config,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Use credentials from config file
        # In a real application, you would use a proper authentication system
        if (
            username == AUTH_CONFIG["ADMIN_USERNAME"]
            and password == AUTH_CONFIG["ADMIN_PASSWORD"]
        ):
            session["logged_in"] = True
            session["username"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/workers")
@login_required
def workers():
    workers_data = read_json(WORKERS_FILE)
    return render_template("workers.html", workers=workers_data["workers"])


@app.route("/workers/add", methods=["POST"])
@login_required
def add_worker():
    workers_data = read_json(WORKERS_FILE)

    new_worker = {
        "id": request.form.get("worker_id"),
        "name": request.form.get("name"),
        "phone": request.form.get("phone"),
        "status": "available",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Check if worker ID already exists
    if any(worker["id"] == new_worker["id"] for worker in workers_data["workers"]):
        flash("Worker ID already exists.", "danger")
    else:
        workers_data["workers"].append(new_worker)
        write_json(WORKERS_FILE, workers_data)
        flash("Worker added successfully.", "success")

    return redirect(url_for("workers"))


@app.route("/workers/delete/<worker_id>")
@login_required
def delete_worker(worker_id):
    workers_data = read_json(WORKERS_FILE)
    assignments_data = read_json(ASSIGNMENTS_FILE)

    # Remove worker from workers.json
    workers_data["workers"] = [
        w for w in workers_data["workers"] if w["id"] != worker_id
    ]

    # Remove any assignments for this worker
    assignments_data["assignments"] = [
        a for a in assignments_data["assignments"] if a["worker_id"] != worker_id
    ]

    write_json(WORKERS_FILE, workers_data)
    write_json(ASSIGNMENTS_FILE, assignments_data)

    flash("Worker deleted successfully.", "success")
    return redirect(url_for("workers"))


@app.route("/workers/status/<worker_id>/<status>")
@login_required
def change_worker_status(worker_id, status):
    if status not in ["available", "on_leave"]:
        flash("Invalid status.", "danger")
        return redirect(url_for("workers"))

    workers_data = read_json(WORKERS_FILE)
    assignments_data = read_json(ASSIGNMENTS_FILE)

    # Update worker status
    for worker in workers_data["workers"]:
        if worker["id"] == worker_id:
            worker["status"] = status

            # If worker is put on leave, remove any assignments
            if status == "on_leave":
                assignments_data["assignments"] = [
                    a
                    for a in assignments_data["assignments"]
                    if a["worker_id"] != worker_id
                ]
                write_json(ASSIGNMENTS_FILE, assignments_data)

            break

    write_json(WORKERS_FILE, workers_data)
    flash(f"Worker status changed to {status}.", "success")
    return redirect(url_for("workers"))


@app.route("/alerts")
@login_required
def alerts():
    alerts_data = read_json(ALERTS_FILE)
    workers_data = read_json(WORKERS_FILE)
    assignments_data = read_json(ASSIGNMENTS_FILE)
    bins_data = read_json(BINS_FILE)

    # Get available workers
    available_workers = [
        w for w in workers_data["workers"] if w["status"] == "available"
    ]

    # Get active alerts
    active_alerts = [a for a in alerts_data["alerts"] if a["status"] == "active"]

    # Get assignments for each alert
    for alert in active_alerts:
        bin_info = next(
            (b for b in bins_data["bins"] if b["id"] == alert["bin_id"]), None
        )
        if bin_info:
            alert["address"] = bin_info["address"]
            alert["area"] = bin_info["area"]
        else:
            alert["address"] = "Unknown"
            alert["area"] = "Unknown"
        alert["assignments"] = [
            a for a in assignments_data["assignments"] if a["alert_id"] == alert["id"]
        ]
        alert["assigned_workers"] = []

        for assignment in alert["assignments"]:
            for worker in workers_data["workers"]:
                if worker["id"] == assignment["worker_id"]:
                    alert["assigned_workers"].append(worker)

    return render_template(
        "alerts.html", alerts=active_alerts, available_workers=available_workers
    )


@app.route("/alerts/resolve/<alert_id>")
@login_required
def resolve_alert(alert_id):
    alerts_data = read_json(ALERTS_FILE)
    assignments_data = read_json(ASSIGNMENTS_FILE)
    workers_data = read_json(WORKERS_FILE)

    # Update alert status
    for alert in alerts_data["alerts"]:
        if alert["id"] == alert_id:
            alert["status"] = "resolved"
            alert["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break

    # Free up assigned workers
    assigned_worker_ids = []
    for assignment in assignments_data["assignments"]:
        if assignment["alert_id"] == alert_id:
            assigned_worker_ids.append(assignment["worker_id"])

    # Remove assignments for this alert
    assignments_data["assignments"] = [
        a for a in assignments_data["assignments"] if a["alert_id"] != alert_id
    ]

    # Update worker status to available
    for worker in workers_data["workers"]:
        if worker["id"] in assigned_worker_ids:
            worker["status"] = "available"

    write_json(ALERTS_FILE, alerts_data)
    write_json(ASSIGNMENTS_FILE, assignments_data)
    write_json(WORKERS_FILE, workers_data)

    flash("Alert resolved successfully.", "success")
    return redirect(url_for("alerts"))


@app.route("/alerts/assign", methods=["POST"])
@login_required
def assign_worker():
    alert_id = request.form.get("alert_id")
    worker_id = request.form.get("worker_id")

    if not alert_id or not worker_id:
        flash("Missing alert ID or worker ID.", "danger")
        return redirect(url_for("alerts"))

    alerts_data = read_json(ALERTS_FILE)
    workers_data = read_json(WORKERS_FILE)
    assignments_data = read_json(ASSIGNMENTS_FILE)

    # Check if alert exists and is active
    alert_exists = False
    for alert in alerts_data["alerts"]:
        if alert["id"] == alert_id and alert["status"] == "active":
            alert_exists = True
            break

    if not alert_exists:
        flash("Alert not found or already resolved.", "danger")
        return redirect(url_for("alerts"))

    # Check if worker exists and is available
    worker_available = False
    for worker in workers_data["workers"]:
        if worker["id"] == worker_id and worker["status"] == "available":
            worker_available = True
            worker["status"] = "assigned"
            break

    if not worker_available:
        flash("Worker not found or not available.", "danger")
        return redirect(url_for("alerts"))

    # Create assignment
    new_assignment = {
        "id": f"assign_{len(assignments_data['assignments']) + 1}",
        "alert_id": alert_id,
        "worker_id": worker_id,
        "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    assignments_data["assignments"].append(new_assignment)

    write_json(WORKERS_FILE, workers_data)
    write_json(ASSIGNMENTS_FILE, assignments_data)

    flash("Worker assigned successfully.", "success")
    return redirect(url_for("alerts"))


@app.route("/alerts/unassign/<alert_id>/<worker_id>")
@login_required
def unassign_worker(alert_id, worker_id):
    workers_data = read_json(WORKERS_FILE)
    assignments_data = read_json(ASSIGNMENTS_FILE)

    # Remove assignment
    assignments_data["assignments"] = [
        a
        for a in assignments_data["assignments"]
        if not (a["alert_id"] == alert_id and a["worker_id"] == worker_id)
    ]

    # Update worker status
    for worker in workers_data["workers"]:
        if worker["id"] == worker_id:
            worker["status"] = "available"
            break

    write_json(WORKERS_FILE, workers_data)
    write_json(ASSIGNMENTS_FILE, assignments_data)

    flash("Worker unassigned successfully.", "success")
    return redirect(url_for("alerts"))


# API endpoint for ESP32 to send alert data
@app.route("/api/alert", methods=["POST"])
def receive_alert():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        bin_id = data.get("bin_id")
        fill_level = data.get("fill_level")

        if not bin_id or fill_level is None:
            return jsonify({"error": "Missing bin_id or fill_level"}), 400
        bins_data = read_json(BINS_FILE)
        bin_exists = any(bin["id"] == bin_id for bin in bins_data["bins"])

        if not bin_exists:
            return jsonify({"error": "Bin ID does not exist"}), 404

        # Determine severity based on fill level using thresholds from config
        if 0 <= fill_level <= ALERT_THRESHOLDS["LOW"]:
            severity = "low"
        elif ALERT_THRESHOLDS["LOW"] < fill_level <= ALERT_THRESHOLDS["MODERATE"]:
            severity = "moderate"
        else:
            severity = "high"

        alerts_data = read_json(ALERTS_FILE)

        # Check if this bin already has an active alert
        existing_alert = None
        for alert in alerts_data["alerts"]:
            if alert["bin_id"] == bin_id and alert["status"] == "active":
                existing_alert = alert
                break

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existing_alert:
            # Update existing alert
            existing_alert["fill_level"] = fill_level
            existing_alert["severity"] = severity
            existing_alert["updated_at"] = timestamp
            response_message = "Alert updated"
        else:
            # Create new alert
            new_alert = {
                "id": f"alert_{len(alerts_data['alerts']) + 1}",
                "bin_id": bin_id,
                "fill_level": fill_level,
                "severity": severity,
                "status": "active",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            alerts_data["alerts"].append(new_alert)
            response_message = "New alert created"

        write_json(ALERTS_FILE, alerts_data)

        return jsonify({"message": response_message, "severity": severity}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/bins")
@login_required
def bins():
    bins_data = read_json(BINS_FILE)
    return render_template("bins.html", bins=bins_data["bins"])


@app.route("/bins/add", methods=["POST"])
@login_required
def add_bin():
    bins_data = read_json(BINS_FILE)

    new_bin = {
        "id": request.form.get("bin_id"),
        "address": request.form.get("address"),
        "area": request.form.get("area"),
        "capacity": int(request.form.get("capacity", 100)),
        "last_emptied": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Check if bin ID already exists
    if any(bin["id"] == new_bin["id"] for bin in bins_data["bins"]):
        flash("Bin ID already exists.", "danger")
    else:
        bins_data["bins"].append(new_bin)
        write_json(BINS_FILE, bins_data)
        flash("Bin added successfully.", "success")

    return redirect(url_for("bins"))


@app.route("/bins/edit/<bin_id>", methods=["POST"])
@login_required
def edit_bin(bin_id):
    bins_data = read_json(BINS_FILE)

    for bin in bins_data["bins"]:
        if bin["id"] == bin_id:
            bin["address"] = request.form.get("address")
            bin["area"] = request.form.get("area")
            bin["capacity"] = int(request.form.get("capacity", 100))
            break

    write_json(BINS_FILE, bins_data)
    flash("Bin updated successfully.", "success")
    return redirect(url_for("bins"))


@app.route("/bins/delete/<bin_id>")
@login_required
def delete_bin(bin_id):
    bins_data = read_json(BINS_FILE)
    alerts_data = read_json(ALERTS_FILE)

    # Remove bin
    bins_data["bins"] = [b for b in bins_data["bins"] if b["id"] != bin_id]

    # Remove associated alerts
    alerts_data["alerts"] = [a for a in alerts_data["alerts"] if a["bin_id"] != bin_id]

    write_json(BINS_FILE, bins_data)
    write_json(ALERTS_FILE, alerts_data)

    flash("Bin deleted successfully.", "success")
    return redirect(url_for("bins"))


if __name__ == "__main__":
    app.run(debug=APP_CONFIG["DEBUG"], host=APP_CONFIG["HOST"], port=APP_CONFIG["PORT"])
