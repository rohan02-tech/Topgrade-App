"""
chatbot.py
Rule-based chatbot for the TOP GRADE app widget.

This is intentionally NOT connected to an external AI API - it answers using
your own course and enrollment data straight from topgrade.db, matched
against simple keyword intents. That keeps it free to run, fast, and
accurate about your actual catalog (no risk of it inventing course details).

HOW IT WORKS
------------
get_bot_reply(student_id, message) is the single entry point.
  - student_id: int or None. None means an unauthenticated/unidentified visitor.
  - message: the raw text the user typed.

It looks at the message, guesses an intent from keywords, pulls whatever it
needs from the database (course list, a specific course, or a student's
enrollment), and returns a plain-text reply string.

NO CHAT HISTORY (BY DESIGN, FOR NOW)
------------------------------------
Every call is independent - the bot has no memory of earlier messages in the
same conversation. This matches the current requirement.

UPGRADE PATH: TO ADD HISTORY LATER
-----------------------------------
1. Add a table to schema.sql, e.g.:
     CREATE TABLE chat_messages (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         student_id INTEGER,             -- nullable, for anonymous visitors
         sender TEXT NOT NULL,            -- 'user' or 'bot'
         message TEXT NOT NULL,
         created_at TEXT DEFAULT CURRENT_TIMESTAMP,
         FOREIGN KEY (student_id) REFERENCES students(id)
     );
2. In the /api/chat route in app.py, after computing `reply`, INSERT both the
   user's message and the bot's reply into chat_messages.
3. Add a GET /api/chat-history/<student_id> endpoint that returns past rows
   ordered by created_at, and have the frontend load it when the widget opens.
No changes to the intent-matching logic below would be needed - history is
purely an additive, storage-layer change.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "topgrade.db")


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_all_courses(conn):
    courses = conn.execute("SELECT * FROM courses").fetchall()
    result = []
    for c in courses:
        lessons = conn.execute(
            "SELECT * FROM lessons WHERE course_id = ? ORDER BY lesson_number",
            (c["id"],),
        ).fetchall()
        result.append({**dict(c), "lessons": [dict(l) for l in lessons]})
    return result


def _find_course_by_name(courses, text):
    text = text.lower()
    for c in courses:
        if c["title"].lower().split()[0] in text:  # "python" or "java"
            return c
    return None


def _get_student(conn, student_id):
    if student_id is None:
        return None
    return conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()


def _is_enrolled(conn, student_id, course_id):
    if student_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ? AND status = 'approved'",
        (student_id, course_id),
    ).fetchone()
    return row is not None


def get_bot_reply(student_id, message):
    """Main entry point. Returns a plain-text reply string."""
    if not message or not message.strip():
        return "I didn't catch that - could you type your question?"

    text = message.lower().strip()
    conn = _get_db()
    try:
        courses = _get_all_courses(conn)
        student = _get_student(conn, student_id)
        mentioned_course = _find_course_by_name(courses, text)

        # ---- Greeting ----
        if any(w in text for w in ["hi", "hello", "hey"]) and len(text) < 20:
            name = f", {student['name']}" if student else ""
            return (
                f"Hey there{name}! I'm the TOP GRADE assistant. "
                f"You can ask me about our courses, lessons, pricing, or your enrollment status."
            )

        # ---- Enrollment status: "am I enrolled", "my courses", "my learning" ----
        if any(p in text for p in ["am i enrolled", "my course", "my learning", "what am i taking", "my enrollment"]):
            if student is None:
                return (
                    "I can't tell yet who you are - please log in first, "
                    "then ask me again and I'll pull up your enrolled courses."
                )
            enrolled = [c for c in courses if _is_enrolled(conn, student_id, c["id"])]
            if not enrolled:
                return (
                    f"You're not enrolled in anything yet, {student['name']}. "
                    f"Want me to tell you about our Python or Java course?"
                )
            titles = ", ".join(c["title"] for c in enrolled)
            return f"You're enrolled in: {titles}. Tap 'My Learning' below to jump into your lessons."

        # ---- How to enroll / enrollment action ----
        if any(p in text for p in ["how do i enroll", "how to enroll", "want to enroll", "sign up", "join course"]):
            if mentioned_course:
                if student and _is_enrolled(conn, student_id, mentioned_course["id"]):
                    return f"Good news - you're already enrolled in {mentioned_course['title']}!"
                return (
                    f"To enroll in {mentioned_course['title']}, open the course card on the Home page "
                    f"and tap 'Enroll Now'. It's {mentioned_course['price']} rupees for {mentioned_course['duration']}."
                )
            return (
                "Open the Home page, find the course you're interested in, and tap 'Enroll Now' on its card. "
                "If you're not logged in yet, you'll be asked to log in first."
            )

        # ---- Lesson count / lecture details for a specific course ----
        if mentioned_course and any(p in text for p in ["lecture", "lesson", "how many", "video", "content", "syllabus", "topic"]):
            lesson_lines = "\n".join(
                f"- {l['title']} ({l['duration']})" for l in mentioned_course["lessons"]
            )
            return (
                f"{mentioned_course['title']} currently has {len(mentioned_course['lessons'])} lecture(s):\n"
                f"{lesson_lines}\n\n{mentioned_course['description']}"
            )

        # ---- Pricing ----
        if any(p in text for p in ["price", "cost", "fee", "how much"]):
            if mentioned_course:
                return f"{mentioned_course['title']} costs {mentioned_course['price']} rupees for {mentioned_course['duration']}."
            lines = "\n".join(f"- {c['title']}: {c['price']} rupees ({c['duration']})" for c in courses)
            return f"Here's our current pricing:\n{lines}"

        # ---- Course details / description ----
        if mentioned_course:
            return f"{mentioned_course['title']}: {mentioned_course['description']}"

        # ---- Course discovery: "what courses", "courses available" ----
        if any(p in text for p in ["what course", "which course", "courses do you have", "courses available", "course list"]):
            titles = ", ".join(c["title"] for c in courses)
            return f"We currently offer: {titles}. Ask me about either one for details, lessons, or pricing."

        # ---- Support / contact / escalation ----
        if any(p in text for p in ["support", "help", "contact", "human", "agent", "complaint"]):
            return (
                "I can help with course info, enrollment, and pricing questions right here. "
                "For anything else, reach our support team at support@topgradeinnovations.com."
            )

        # ---- Fallback ----
        return (
            "I'm not sure I understood that. Try asking things like "
            "\"What courses do you have?\", \"How many lectures in Python?\", "
            "\"What's the price of Java?\", or \"Am I enrolled?\""
        )
    finally:
        conn.close()
