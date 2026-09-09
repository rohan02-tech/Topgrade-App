"""
chatbot.py
TOP GRADE chat widget backend logic.

Uses the OpenAI ChatGPT API to generate natural, flexible replies, while
keeping topgrade.db as the single source of truth for facts (prices, lesson
counts, enrollment status, descriptions). We never let the model "know"
facts on its own - every request rebuilds a fresh context string straight
from the database and tells the model to only use that, and nothing else,
for anything factual about TOP GRADE.

HOW IT WORKS
------------
get_bot_reply(student_id, message) is the single entry point, unchanged
from before, so app.py does not need to change at all.

  1. Pull live data from the DB: all courses + lessons, and (if student_id
     is given) that student's name and enrollment status.
  2. Build a system prompt containing that data as plain facts, plus
     instructions on tone and what to do if asked something unrelated.
  3. Send that + the user's message to the OpenAI Chat Completions API.
  4. Return the model's reply text.

FALLBACK BEHAVIOUR
-------------------
If OPENAI_API_KEY is not set, or the API call fails for any reason
(network issue, quota exhausted, bad key), we fall back to the old
rule-based keyword responder below so the chat widget never just breaks or
shows an error to a student. This is a graceful degrade, not a crash.

NO CHAT HISTORY (BY DESIGN, FOR NOW)
------------------------------------
Every call is still independent - same as before. See the note in the
old version of this file for how to add persistent history later; that
upgrade path is unchanged by this rewrite.

SETUP
-----
Set the OPENAI_API_KEY environment variable (locally in a .env / shell
export, and on Render under the backend service's Environment tab).
Nothing else in the codebase needs to change once that variable is set.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "topgrade.db")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # cheap, fast, good enough for a support bot

_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"[chatbot] Could not initialise OpenAI client, will use fallback only: {e}")
        _client = None


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
        "SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ? AND status = 'active'",
        (student_id, course_id),
    ).fetchone()
    return row is not None


def _get_enrolled_courses(conn, student_id):
    if student_id is None:
        return []
    rows = conn.execute(
        """SELECT c.* FROM courses c
           JOIN enrollments e ON e.course_id = c.id
           WHERE e.student_id = ? AND e.status = 'active'""",
        (student_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Context building for the LLM
# ---------------------------------------------------------------------------

def _build_context(conn, student_id):
    """Builds a plain-text block of live facts to ground the model's reply."""
    courses = _get_all_courses(conn)
    student = _get_student(conn, student_id)
    enrolled_courses = _get_enrolled_courses(conn, student_id) if student else []
    enrolled_ids = {c["id"] for c in enrolled_courses}

    lines = []
    lines.append("TOP GRADE course catalog (this is the full and only catalog, do not mention any other courses):")
    for c in courses:
        lines.append(
            f"- {c['title']} | category: {c['category']} | price: Rs. {c['price']} | "
            f"duration: {c['duration']} | students enrolled: {c['students_enrolled']} | "
            f"lessons available so far: {len(c['lessons'])}"
        )
        for l in c["lessons"]:
            lines.append(f"    Lesson {l['lesson_number']}: {l['title']} ({l['duration']})")
        lines.append(f"    Description: {c['description']}")

    lines.append("")
    if student:
        lines.append(f"The person chatting is a logged-in student named {student['name']}.")
        if enrolled_courses:
            titles = ", ".join(c["title"] for c in enrolled_courses)
            lines.append(f"They are currently enrolled in: {titles}.")
        else:
            lines.append("They are not currently enrolled in any course.")
    else:
        lines.append("The person chatting is an anonymous visitor who is not logged in.")

    lines.append("")
    lines.append("TOP GRADE company facts: tagline 'Learn Today, Lead Tomorrow'. "
                  "Support contact: support@topgradeinnovations.com. Website: www.topgradeinnovation.com. "
                  "TOP GRADE is MSME, MCA, and ISO 9001 approved.")

    return "\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """You are the TOP GRADE support and course assistant chat widget, embedded in the TOP GRADE learning app.

Be warm, concise, and helpful, like a friendly course advisor. Keep replies short - a few sentences at most, this is a chat widget, not an essay. Do not use markdown formatting, tables or bullet symbols; write in plain conversational sentences since this is rendered as plain text in a chat bubble.

Only state facts about TOP GRADE, its courses, prices, lessons, or the student's enrollment using the information given below. Never invent a course, price, lesson, or company detail that is not listed. If someone asks something about TOP GRADE that is not covered in the facts below, say you're not sure and suggest they contact support at support@topgradeinnovations.com.

You CAN and SHOULD chat naturally and helpfully about general topics unrelated to TOP GRADE too (e.g. study tips, explaining a programming concept, motivation, general questions) - the goal is to be a genuinely useful assistant for students, not just a rigid course FAQ bot.

Here are the current live facts about TOP GRADE:

{context}
"""


# ---------------------------------------------------------------------------
# LLM-backed reply
# ---------------------------------------------------------------------------

def _get_llm_reply(student_id, message):
    if _client is None:
        return None

    conn = _get_db()
    try:
        context = _build_context(conn, student_id)
    finally:
        conn.close()

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    try:
        response = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=300,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[chatbot] OpenAI call failed, falling back to rule-based reply: {e}")
        return None


# ---------------------------------------------------------------------------
# Rule-based fallback (used if no API key set, or the API call fails)
# ---------------------------------------------------------------------------

def _get_rule_based_reply(student_id, message):
    text = message.lower().strip()
    conn = _get_db()
    try:
        courses = _get_all_courses(conn)
        student = _get_student(conn, student_id)

        if any(g in text for g in ["hi", "hello", "hey"]):
            name = f", {student['name']}" if student else ""
            return f"Hi there{name}! I'm the TOP GRADE assistant. Ask me about our courses, pricing, or your enrollment."

        if "enrolled" in text or "my course" in text:
            if not student:
                return "You're not logged in yet, so I can't check your enrollment. Please log in first."
            enrolled = _get_enrolled_courses(conn, student_id)
            if enrolled:
                titles = ", ".join(c["title"] for c in enrolled)
                return f"You're enrolled in: {titles}."
            return "You're not enrolled in any course yet. Head to the home page to enroll."

        if "how" in text and "enroll" in text:
            return "Just open a course from the home page and tap Enroll. It's instant, no payment needed in this demo."

        course = _find_course_by_name(courses, text)
        if course and ("lesson" in text or "lecture" in text):
            return f"{course['title']} currently has {len(course['lessons'])} lessons available."

        if "price" in text or "cost" in text or "fee" in text:
            if course:
                return f"{course['title']} costs Rs. {course['price']} for {course['duration']}."
            parts = [f"{c['title']}: Rs. {c['price']}" for c in courses]
            return "Here's our pricing: " + "; ".join(parts) + "."

        if course:
            return f"{course['title']}: {course['description']}"

        if "course" in text:
            titles = ", ".join(c["title"] for c in courses)
            return f"We currently offer: {titles}. Ask me about either one for more details."

        if "support" in text or "help" in text or "contact" in text:
            return "You can reach our support team at support@topgradeinnovations.com."

        return "I'm not totally sure about that. You can ask me about our courses, pricing, lessons, or your enrollment, or contact support@topgradeinnovations.com."
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public entry point (unchanged signature - app.py needs no changes)
# ---------------------------------------------------------------------------

def get_bot_reply(student_id, message):
    reply = _get_llm_reply(student_id, message)
    if reply:
        return reply
    return _get_rule_based_reply(student_id, message)
