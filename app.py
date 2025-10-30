import json
import os
from typing import Dict, Any, List
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def ensure_data_file() -> None:
	if not os.path.exists(DATA_FILE):
		seed = {
			"users": {
				"admin": {
					"password": "admin123",
					"role": "admin",
					"full_name": "Administrator"
				}
			},
			"students": {},
			"teachers": {},
			"results": {}
		}
		with open(DATA_FILE, "w", encoding="utf-8") as f:
			json.dump(seed, f, indent=2)


def read_db() -> Dict[str, Any]:
	ensure_data_file()
	with open(DATA_FILE, "r", encoding="utf-8") as f:
		return json.load(f)


def write_db(data: Dict[str, Any]) -> None:
	with open(DATA_FILE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2)


def current_user() -> Dict[str, Any] | None:
	username = session.get("username")
	if not username:
		return None
	db = read_db()
	return db["users"].get(username)


def login_required(role: str | None = None):
	def decorator(view_func):
		def wrapped(*args, **kwargs):
			user = current_user()
			if not user:
				flash("Please log in.", "warning")
				return redirect(url_for("login"))
			if role and user.get("role") != role:
				flash("Unauthorized.", "danger")
				return redirect(url_for("login"))
			return view_func(*args, **kwargs)
		wrapped.__name__ = view_func.__name__
		return wrapped
	return decorator


@app.route("/")
def index():
	user = current_user()
	if not user:
		return redirect(url_for("login"))
	role = user.get("role")
	if role == "admin":
		return redirect(url_for("admin_dashboard"))
	if role == "teacher":
		return redirect(url_for("teacher_dashboard"))
	if role == "student":
		return redirect(url_for("student_dashboard"))
	return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		username = request.form.get("username", "").strip()
		password = request.form.get("password", "")
		db = read_db()
		user = db["users"].get(username)
		if user and user.get("password") == password:
			session["username"] = username
			flash("Logged in successfully.", "success")
			return redirect(url_for("index"))
		flash("Invalid credentials.", "danger")
	return render_template("login.html")


@app.route("/logout")
def logout():
	session.clear()
	flash("Logged out.", "info")
	return redirect(url_for("login"))


# Admin routes
@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
	db = read_db()
	teachers = [u for u, info in db["users"].items() if info.get("role") == "teacher"]
	students = [u for u, info in db["users"].items() if info.get("role") == "student"]
	return render_template("dashboard_admin.html", teachers=teachers, students=students)


@app.route("/admin/users")
@login_required(role="admin")
def admin_users():
	db = read_db()
	users = db["users"]
	return render_template("users.html", users=users)


@app.route("/admin/create", methods=["GET", "POST"])
@login_required(role="admin")
def admin_create_user():
	if request.method == "POST":
		username = request.form.get("username", "").strip()
		password = request.form.get("password", "")
		role = request.form.get("role")
		full_name = request.form.get("full_name", "").strip()
		if not username or not password or role not in ("teacher", "student"):
			flash("Please provide username, password, and valid role.", "warning")
			return redirect(url_for("admin_create_user"))
		db = read_db()
		if username in db["users"]:
			flash("User already exists.", "danger")
			return redirect(url_for("admin_create_user"))
		db["users"][username] = {
			"password": password,
			"role": role,
			"full_name": full_name or username
		}
		if role == "teacher":
			db["teachers"][username] = {"full_name": full_name or username}
		if role == "student":
			db["students"][username] = {"full_name": full_name or username}
		write_db(db)
		flash("User created.", "success")
		return redirect(url_for("admin_users"))
	return render_template("create_user.html")


@app.route("/admin/delete/<username>")
@login_required(role="admin")
def admin_delete_user(username: str):
	db = read_db()
	if username == "admin":
		flash("Cannot delete admin.", "danger")
		return redirect(url_for("admin_users"))
	user = db["users"].pop(username, None)
	if user:
		if user.get("role") == "teacher":
			db["teachers"].pop(username, None)
		elif user.get("role") == "student":
			db["students"].pop(username, None)
			# also remove their results
			to_delete: List[str] = []
			for result_id, result in db["results"].items():
				if result.get("student_id") == username:
					to_delete.append(result_id)
			for rid in to_delete:
				db["results"].pop(rid, None)
		write_db(db)
		flash("User deleted.", "info")
	else:
		flash("User not found.", "warning")
	return redirect(url_for("admin_users"))


# Teacher routes
@app.route("/teacher")
@login_required(role="teacher")
def teacher_dashboard():
	db = read_db()
	students = db["students"]
	return render_template("dashboard_teacher.html", students=students)


@app.route("/teacher/enter", methods=["GET", "POST"])
@login_required(role="teacher")
def teacher_enter_marks():
	db = read_db()
	students = db["students"]
	if request.method == "POST":
		student_id = request.form.get("student_id")
		attendance = request.form.get("attendance", "0").strip()
		subjects_raw = request.form.getlist("subject[]")
		marks_raw = request.form.getlist("mark[]")
		if student_id not in students:
			flash("Select a valid student.", "warning")
			return redirect(url_for("teacher_enter_marks"))
		try:
			attendance_val = float(attendance)
		except ValueError:
			attendance_val = 0.0
		subjects: List[Dict[str, Any]] = []
		total = 0.0
		for s, m in zip(subjects_raw, marks_raw):
			name = s.strip()
			if not name:
				continue
			try:
				mark_val = float(m)
			except ValueError:
				mark_val = 0.0
			if mark_val < 0:
				mark_val = 0.0
			if mark_val > 100:
				mark_val = 100.0
			subjects.append({"name": name, "mark": mark_val})
			total += mark_val
		average = (total / len(subjects)) if subjects else 0.0
		if average >= 90:
			grade = "A+"
		elif average >= 80:
			grade = "A"
		elif average >= 70:
			grade = "B"
		elif average >= 60:
			grade = "C"
		elif average >= 50:
			grade = "D"
		else:
			grade = "F"
		result_id = f"{student_id}"
		db["results"][result_id] = {
			"student_id": student_id,
			"subjects": subjects,
			"total": round(total, 2),
			"average": round(average, 2),
			"grade": grade,
			"attendance": round(attendance_val, 2)
		}
		write_db(db)
		flash("Result saved.", "success")
		return redirect(url_for("teacher_dashboard"))
	return render_template("enter_marks.html", students=students)


# Student routes
@app.route("/student")
@login_required(role="student")
def student_dashboard():
	user = current_user()
	db = read_db()
	result = db["results"].get(user["full_name"])  # likely none if full_name != username
	# Use username key for results instead, align above storage: result_id == student_id (username)
	result = db["results"].get(session.get("username"))
	return render_template("dashboard_student.html", result=result)


@app.template_filter("pct")
def pct(value: float) -> str:
	try:
		return f"{float(value):.2f}%"
	except Exception:
		return "0.00%"


if __name__ == "__main__":
	ensure_data_file()
	app.run(host="0.0.0.0", port=5000, debug=True)
