import os, psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

# Ensure environment variables are loaded, overriding any existing ones
load_dotenv(override=True)

CFG = dict(host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT", "5432"),
           dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
           password=os.getenv("DB_PASSWORD"), sslmode="require")

@contextmanager
def cursor(commit=False):
    # Print the DB_HOST being used for debugging
    print(f"DEBUG: DB_HOST being used by db.py: {os.getenv('DB_HOST')}")
    conn = psycopg2.connect(**CFG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        if commit: conn.commit()
    finally:
        cur.close(); conn.close()

def init_db():
    with cursor(commit=True) as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE, email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255), is_verified BOOLEAN DEFAULT FALSE,
            role VARCHAR(20) NOT NULL DEFAULT 'employee')""")
        cur.execute("""ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'employee'""")
        cur.execute("""CREATE TABLE IF NOT EXISTS otp_codes (
            id SERIAL PRIMARY KEY, email VARCHAR(255), code VARCHAR(6),
            purpose VARCHAR(20), expires_at TIMESTAMP, used BOOLEAN DEFAULT FALSE)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS mood_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mood_date DATE NOT NULL DEFAULT CURRENT_DATE,
            sentiment VARCHAR(20),
            emotion VARCHAR(30),
            compound_score REAL,
            confidence REAL,
            positive_score REAL,
            negative_score REAL,
            neutral_score REAL,
            detected_language VARCHAR(80),
            cleaned_text TEXT,
            journal_text TEXT,
            source VARCHAR(10) NOT NULL DEFAULT 'manual',
            created_at TIMESTAMP NOT NULL DEFAULT NOW())""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS source VARCHAR(10) NOT NULL DEFAULT 'manual'""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS confidence REAL""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS positive_score REAL""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS negative_score REAL""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS neutral_score REAL""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS detected_language VARCHAR(80)""")
        cur.execute("""ALTER TABLE mood_logs ADD COLUMN IF NOT EXISTS cleaned_text TEXT""")
        cur.execute("""CREATE TABLE IF NOT EXISTS daily_wellness (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            wellness_date DATE NOT NULL DEFAULT CURRENT_DATE,
            stress_level REAL,
            sleep_hours REAL,
            workload VARCHAR(20),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, wellness_date)
        )""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_daily_wellness_user_date ON daily_wellness(user_id, wellness_date)""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_mood_logs_user_date
            ON mood_logs(user_id, mood_date)""")


MOOD_LABELS = ["Amazing", "Happy", "Normal", "Sad", "Angry"]

NLP_TO_MOOD_LABEL = {
    "Positive": "Happy",
    "Neutral": "Normal",
    "Negative": "Sad",
}


def save_manual_mood(user_id, mood_label):
    """Employee taps an emoji on the 'How Do You Feel?' picker — saves
    immediately (with the current date+time via created_at), no NLP involved."""
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO mood_logs (user_id, sentiment, source)
               VALUES (%s, %s, 'manual')""",
            (user_id, mood_label),
        )

def save_mood_log(user_id, sentiment, emotion, compound_score, journal_text, confidence=None,
                  positive_score=None, negative_score=None, neutral_score=None,
                  detected_language=None, cleaned_text=None):
    """Store the NLP result exactly as returned by the existing pipeline.
    NLP is not rerun by the weekly report; these stored values are reused."""
    mood_label = NLP_TO_MOOD_LABEL.get(sentiment, "Normal")
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO mood_logs
               (user_id, sentiment, emotion, compound_score, confidence,
                positive_score, negative_score, neutral_score, detected_language,
                cleaned_text, journal_text, source)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'nlp')""",
            (user_id, mood_label, emotion, compound_score, confidence,
             positive_score, negative_score, neutral_score, detected_language,
             cleaned_text, journal_text),
        )

def save_daily_wellness(user_id, wellness_date, stress_level=None, sleep_hours=None, workload=None):
    """Upsert non-journal daily wellness measurements without creating journal duplicates."""
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO daily_wellness
               (user_id, wellness_date, stress_level, sleep_hours, workload)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (user_id, wellness_date) DO UPDATE SET
                 stress_level = EXCLUDED.stress_level,
                 sleep_hours = EXCLUDED.sleep_hours,
                 workload = EXCLUDED.workload,
                 created_at = NOW()""",
            (user_id, wellness_date, stress_level, sleep_hours, workload),
        )

def get_daily_wellness_range(user_id, start_date, end_date):
    with cursor() as cur:
        cur.execute(
            """SELECT wellness_date, stress_level, sleep_hours, workload, created_at
               FROM daily_wellness
               WHERE user_id = %s AND wellness_date BETWEEN %s AND %s
               ORDER BY wellness_date""",
            (user_id, start_date, end_date),
        )
        return cur.fetchall()

def get_mood_logs_for_month(user_id, year, month):
    """Returns one row per day for a given user/month, latest entry per day.
    Used by the Home tab's calendar grid."""
    with cursor() as cur:
        cur.execute(
            """SELECT DISTINCT ON (mood_date) mood_date, sentiment, emotion, compound_score, confidence, created_at
               FROM mood_logs
               WHERE user_id = %s
                 AND EXTRACT(YEAR FROM mood_date) = %s
                 AND EXTRACT(MONTH FROM mood_date) = %s
               ORDER BY mood_date, created_at DESC""",
            (user_id, year, month),
        )
        return cur.fetchall()

def get_user_mood_history(user_id, limit=200):
    """Full history for ONE user, newest first — every field including the
    exact created_at timestamp and journal_text. Powers both the Journal
    tab's 'past entries' list and the personal Dashboard tab's charts."""
    with cursor() as cur:
        cur.execute(
            """SELECT mood_date, sentiment, emotion, compound_score, confidence, positive_score, negative_score, neutral_score, detected_language, cleaned_text, journal_text, source, created_at
               FROM mood_logs
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (user_id, limit),
        )
        return cur.fetchall()

def get_all_employee_mood_logs(limit_days=30):
    """For managers: every employee's mood entries from the last N days,
    joined with username for display."""
    with cursor() as cur:
        cur.execute(
            """SELECT u.username, u.email, m.mood_date, m.sentiment, m.emotion, m.compound_score, m.confidence, m.created_at
               FROM mood_logs m
               JOIN users u ON u.id = m.user_id
               WHERE u.role = 'employee'
                 AND m.mood_date >= CURRENT_DATE - (%s || ' days')::interval
               ORDER BY m.mood_date DESC, u.username""",
            (limit_days,),
        )
        return cur.fetchall()

def get_latest_mood_per_employee():
    """For managers: each employee's single most recent mood entry."""
    with cursor() as cur:
        cur.execute(
            """SELECT DISTINCT ON (u.id) u.username, u.email, m.mood_date, m.sentiment, m.emotion, m.confidence, m.created_at
               FROM users u
               JOIN mood_logs m ON m.user_id = u.id
               WHERE u.role = 'employee'
               ORDER BY u.id, m.created_at DESC"""
        )
        return cur.fetchall()