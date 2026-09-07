"""
seed.py
Creates topgrade.db and fills it with real course content from TOP GRADE curriculum PDFs.

Courses:
  1. Python language (from the "Artificial Intelligence" curriculum PDF - Python/AI/ML track)
  2. Java language (from the "Java Full Stack Development" curriculum PDF)

Students:
  - Rohan  -> enrolled in Python language
  - Aman   -> not enrolled in anything (exploring, interested in Java)

Only 2 lessons are created per course for now (as requested). Video file paths point to
placeholder locations under backend/media/<course>/videos/ - drop your .mp4 files there.

Run: python seed.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "topgrade.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH, "r") as f:
        cur.executescript(f.read())

    # ---- Courses ----
    python_description = (
        "A Python-first path into Artificial Intelligence: covers Python fundamentals "
        "(data types, loops, arrays, Pandas and data visualization), an introduction to AI "
        "and its applications, fundamentals of machine learning (process, algorithms, "
        "regression), deep learning and ANN (perceptron, multilayer networks, back "
        "propagation), statistics and probability, and image processing (OpenCV, filters, "
        "edge and corner detection). Includes a minor and a major project."
    )
    cur.execute("""INSERT INTO courses (title, category, price, duration, description, students_enrolled)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("Python language", "Tech & Data", 8500, "2 months", python_description, 169))
    python_id = cur.lastrowid

    java_description = (
        "A Java Full Stack Development path across 16 modules: Java programming basics and "
        "OOP, advanced Java (collections, generics, streams), front-end basics (HTML5, CSS3, "
        "JavaScript, DOM), React.js, database fundamentals and JDBC, back-end development "
        "with Spring Boot, Spring Data and ORM (Hibernate), building full stack CRUD "
        "applications, authentication and security (Spring Security, JWT), deployment and "
        "DevOps basics (Docker, CI/CD), testing (JUnit, Mockito, Jest), and career preparation. "
        "Includes a minor and a major project."
    )
    cur.execute("""INSERT INTO courses (title, category, price, duration, description, students_enrolled)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("Java language", "Tech & Data", 8000, "2 months", java_description, 0))
    java_id = cur.lastrowid

    # ---- Lessons: 2 per course, drawn from the real curriculum's first modules ----
    lessons = [
        (python_id, 1,
         "Lecture 1: Introduction to Python (data types, loops, arrays)",
         "01:20:18", "media/python-course/videos/lecture1.mp4"),
        (python_id, 2,
         "Lecture 2: Pandas and Data Visualization + Introduction to AI",
         "01:15:26", "media/python-course/videos/lecture2.mp4"),

        (java_id, 1,
         "Lecture 1: Introduction to Java Full Stack Development",
         "01:10:00", "media/java-course/videos/lecture1.mp4"),
        (java_id, 2,
         "Lecture 2: Java Programming Basics (syntax, variables, loops, conditionals)",
         "01:05:40", "media/java-course/videos/lecture2.mp4"),
    ]
    cur.executemany("""INSERT INTO lessons (course_id, lesson_number, title, duration, video_path)
                       VALUES (?, ?, ?, ?, ?)""", lessons)

    # ---- Students ----
    cur.execute("INSERT INTO students (name, email) VALUES (?, ?)", ("Rohan", "rohan@example.com"))
    rohan_id = cur.lastrowid

    cur.execute("INSERT INTO students (name, email) VALUES (?, ?)", ("Aman", "aman@example.com"))
    aman_id = cur.lastrowid

    # ---- Enrollments: Rohan enrolled in Python only. Aman enrolled in nothing. ----
    cur.execute("INSERT INTO enrollments (student_id, course_id, status) VALUES (?, ?, ?)",
                (rohan_id, python_id, "approved"))

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")
    print("Rohan -> enrolled in Python language")
    print("Aman  -> not enrolled in anything, exploring Java language")

if __name__ == "__main__":
    build_database()
