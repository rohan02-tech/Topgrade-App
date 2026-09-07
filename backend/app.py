"""
app.py
Minimal Flask backend for the TOP GRADE app.

API calls:
  1. GET  /api/courses                     -> list all courses (with lessons)
  2. GET  /api/my-courses/<student_id>      -> a student's enrolled courses + lessons
  3. POST /api/enroll                       -> enroll a student in a course
  4. POST /api/unenroll                     -> unenroll a student from a course
  5. POST /api/chat                         -> chatbot widget reply (no history yet, see chatbot.py)

Run:
  pip install flask flask-cors
  python database/seed.py      (creates the db first)
  python app.py
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os

from chatbot import get_bot_reply

app = Flask(__name__)

# CORS: locked to your frontend's origin in production via the ALLOWED_ORIGIN
# env var (set this on Render once your Netlify URL/custom domain is known).
# Falls back to "*" so local development keeps working out of the box.
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGIN}, r"/media/*": {"origins": ALLOWED_ORIGIN}})

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "topgrade.db")
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@app.route("/api/courses", methods=["GET"])
def get_all_courses():
    """Call 1: returns every course in the catalog, each with its lessons."""
    conn = get_db()
    courses = conn.execute("SELECT * FROM courses").fetchall()

    result = []
    for course in courses:
        lessons = conn.execute(
            "SELECT lesson_number, title, duration, video_path FROM lessons WHERE course_id = ? ORDER BY lesson_number",
            (course["id"],),
        ).fetchall()

        result.append({
            "id": course["id"],
            "title": course["title"],
            "category": course["category"],
            "price": course["price"],
            "duration": course["duration"],
            "description": course["description"],
            "students_enrolled": course["students_enrolled"],
            "lessons": [dict(l) for l in lessons],
        })

    conn.close()
    return jsonify(result)


@app.route("/api/my-courses/<int:student_id>", methods=["GET"])
def get_my_courses(student_id):
    """Call 2: returns the courses a specific student is enrolled in."""
    conn = get_db()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    enrolled = conn.execute("""
        SELECT c.id, c.title, c.category, c.price, c.duration, c.description
        FROM courses c
        JOIN enrollments e ON e.course_id = c.id
        WHERE e.student_id = ? AND e.status = 'approved'
    """, (student_id,)).fetchall()

    courses = []
    for course in enrolled:
        lessons = conn.execute(
            "SELECT lesson_number, title, duration, video_path FROM lessons WHERE course_id = ? ORDER BY lesson_number",
            (course["id"],),
        ).fetchall()
        courses.append({**dict(course), "lessons": [dict(l) for l in lessons]})

    conn.close()
    return jsonify({
        "student": {"id": student["id"], "name": student["name"]},
        "enrolled_courses": courses,
    })


@app.route("/api/enroll", methods=["POST"])
def enroll_student():
    """
    Call 3: enroll a student in a course.
    Body (JSON): { "student_id": 2, "course_id": 2 }

    If the student is already enrolled (approved) in that course, this is a no-op
    and returns the existing enrollment rather than creating a duplicate.
    """
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    course_id = data.get("course_id")

    if student_id is None or course_id is None:
        return jsonify({"error": "student_id and course_id are required"}), 400

    conn = get_db()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()

    if student is None:
        conn.close()
        return jsonify({"error": "Student not found"}), 404
    if course is None:
        conn.close()
        return jsonify({"error": "Course not found"}), 404

    existing = conn.execute(
        "SELECT * FROM enrollments WHERE student_id = ? AND course_id = ? AND status = 'approved'",
        (student_id, course_id),
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({
            "message": f"{student['name']} is already enrolled in {course['title']}",
            "enrollment_id": existing["id"],
        }), 200

    cur = conn.execute(
        "INSERT INTO enrollments (student_id, course_id, status) VALUES (?, ?, 'approved')",
        (student_id, course_id),
    )
    conn.execute(
        "UPDATE courses SET students_enrolled = students_enrolled + 1 WHERE id = ?",
        (course_id,),
    )
    conn.commit()
    enrollment_id = cur.lastrowid
    conn.close()

    return jsonify({
        "message": f"{student['name']} has been enrolled in {course['title']}",
        "enrollment_id": enrollment_id,
    }), 201


@app.route("/api/unenroll", methods=["POST"])
def unenroll_student():
    """
    Call 4: unenroll a student from a course.
    Body (JSON): { "student_id": 1, "course_id": 1 }
    """
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    course_id = data.get("course_id")

    if student_id is None or course_id is None:
        return jsonify({"error": "student_id and course_id are required"}), 400

    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM enrollments WHERE student_id = ? AND course_id = ? AND status = 'approved'",
        (student_id, course_id),
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "No active enrollment found for this student and course"}), 404

    conn.execute("DELETE FROM enrollments WHERE id = ?", (existing["id"],))
    conn.execute(
        "UPDATE courses SET students_enrolled = MAX(students_enrolled - 1, 0) WHERE id = ?",
        (course_id,),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Unenrolled successfully"}), 200


@app.route("/media/<path:filepath>", methods=["GET"])
def serve_media(filepath):
    """
    Serves video files, e.g. /media/python-course/videos/lecture1.mp4
    Matches the video_path values stored in the database (which start with "media/").
    """
    return send_from_directory(MEDIA_DIR, filepath)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Call 5: chatbot widget.
    Body (JSON): { "student_id": 1 or null, "message": "how many lectures in python?" }

    Stateless for now - each request is answered independently with no memory
    of prior messages. See chatbot.py for the upgrade path to persisted history.
    """
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    message = data.get("message", "")

    reply = get_bot_reply(student_id, message)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
