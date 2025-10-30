# School Portal (Admin/Teacher/Student)

A simple colorful Flask app with three dashboards:
- Admin: manage users (create teacher/student, list, delete)
- Teacher: enter marks and attendance for students (auto total, average, grade)
- Student: view result

## Requirements
- Python 3.10+

## Setup
```bash
pip install -r requirements.txt
```

## Run
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

## Login
- Admin: `admin` / `admin123`
- Create teacher/student accounts from the Admin dashboard.

## Notes
- Data is stored in `data.json` in the project root.
- Grades: A+ (>=90), A (>=80), B (>=70), C (>=60), D (>=50), else F.
- Attendance is stored as percentage.
