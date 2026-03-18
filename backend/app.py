"""
Analytica Backend - Flask + SQLite + Deep Translator + LangDetect
Run: pip install flask flask-cors deep-translator langdetect
Then: python app.py
Open: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime

# ── Language detection + translation ──
try:
    from deep_translator import GoogleTranslator
    from langdetect import detect as langdetect_detect, LangDetectException
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("⚠️  deep-translator / langdetect not installed.")
    print("   Run: pip install deep-translator langdetect")

app = Flask(__name__, static_folder='static')
CORS(app)

DB_PATH    = os.path.join(os.path.dirname(__file__), 'analytica.db')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)


# ─── Language map (langdetect code → readable name) ───────────────────────────
LANG_NAMES = {
    'en': 'English',   'hi': 'Hindi',    'de': 'German',
    'fr': 'French',    'es': 'Spanish',  'it': 'Italian',
    'pt': 'Portuguese','ru': 'Russian',  'ja': 'Japanese',
    'ko': 'Korean',    'zh-cn': 'Chinese','zh-tw': 'Chinese',
    'ar': 'Arabic',    'tr': 'Turkish',  'nl': 'Dutch',
    'pl': 'Polish',    'sv': 'Swedish',  'da': 'Danish',
    'fi': 'Finnish',   'no': 'Norwegian','cs': 'Czech',
    'ro': 'Romanian',  'hu': 'Hungarian','uk': 'Ukrainian',
    'vi': 'Vietnamese','th': 'Thai',     'id': 'Indonesian',
    'ms': 'Malay',     'bn': 'Bengali',  'ta': 'Tamil',
    'te': 'Telugu',    'mr': 'Marathi',  'gu': 'Gujarati',
    'kn': 'Kannada',   'ml': 'Malayalam','pa': 'Punjabi',
    'ur': 'Urdu',
}


# ─── Translation endpoint ─────────────────────────────────────────────────────

@app.route('/api/translate', methods=['POST'])
def translate_prompt():
    """
    Accepts: { "text": "Internetnutzung analysieren" }
    Returns: { "original": "...", "translated": "...", "detected_lang": "de", "lang_name": "German" }
    """
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'text is required'}), 400

    if not TRANSLATION_AVAILABLE:
        return jsonify({
            'original': text,
            'translated': text,
            'detected_lang': 'unknown',
            'lang_name': 'Unknown (install deep-translator)',
            'error': 'Translation libraries not installed'
        })

    try:
        # Detect language
        detected = langdetect_detect(text)
        lang_name = LANG_NAMES.get(detected, detected.upper())

        # If already English, skip translation
        if detected in ('en',):
            return jsonify({
                'original': text,
                'translated': text,
                'detected_lang': detected,
                'lang_name': lang_name
            })

        # Translate to English
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return jsonify({
            'original': text,
            'translated': translated,
            'detected_lang': detected,
            'lang_name': lang_name
        })

    except LangDetectException:
        return jsonify({
            'original': text, 'translated': text,
            'detected_lang': 'en', 'lang_name': 'English (fallback)'
        })
    except Exception as e:
        return jsonify({
            'original': text, 'translated': text,
            'detected_lang': 'unknown', 'lang_name': 'Unknown',
            'error': str(e)
        })


# ─── Database setup ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS sql_queries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt      TEXT NOT NULL,
            sql_query   TEXT NOT NULL,
            dataset     TEXT DEFAULT 'Customer Behaviour',
            detected_lang TEXT DEFAULT 'en',
            original_prompt TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            saved       INTEGER DEFAULT 0
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS dashboards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            prompt      TEXT,
            original_prompt TEXT DEFAULT '',
            detected_lang TEXT DEFAULT 'en',
            config_json TEXT,
            insight     TEXT,
            created_at  TEXT NOT NULL
        )
    ''')

    # Seed demo SQL rows if empty
    cur.execute('SELECT COUNT(*) FROM sql_queries')
    if cur.fetchone()[0] == 0:
        demos = [
            ('show top spending customers by city',
             "SELECT city_tier,\n  AVG(avg_online_spend) AS avg_online_spend,\n  AVG(avg_store_spend) AS avg_store_spend,\n  COUNT(*) AS customer_count\nFROM customer_behaviour\nGROUP BY city_tier\nORDER BY avg_online_spend DESC;",
             'Customer Behaviour'),
            ('gender wise shopping preference',
             "SELECT gender,\n  shopping_preference,\n  COUNT(*) AS count,\n  ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(PARTITION BY gender),2) AS pct\nFROM customer_behaviour\nGROUP BY gender, shopping_preference\nORDER BY gender, count DESC;",
             'Customer Behaviour'),
            ('monthly orders by age group',
             "SELECT\n  CASE\n    WHEN age BETWEEN 18 AND 25 THEN '18-25'\n    WHEN age BETWEEN 26 AND 35 THEN '26-35'\n    WHEN age BETWEEN 36 AND 45 THEN '36-45'\n    WHEN age BETWEEN 46 AND 55 THEN '46-55'\n    ELSE '55+'\n  END AS age_group,\n  ROUND(AVG(monthly_online_orders),2) AS avg_online_orders,\n  ROUND(AVG(monthly_store_visits),2) AS avg_store_visits\nFROM customer_behaviour\nGROUP BY age_group\nORDER BY age_group;",
             'Customer Behaviour'),
        ]
        now = datetime.now().strftime('%m/%d/%Y %H:%M')
        for prompt, sql, ds in demos:
            cur.execute(
                'INSERT INTO sql_queries (prompt, sql_query, dataset, created_at) VALUES (?,?,?,?)',
                (prompt, sql, ds, now)
            )

    conn.commit()
    conn.close()
    print(f'✅ Database ready at {DB_PATH}')


# ─── SQL Queries API ──────────────────────────────────────────────────────────

@app.route('/api/queries', methods=['GET'])
def get_queries():
    conn = get_db()
    rows = conn.execute('SELECT * FROM sql_queries ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/queries', methods=['POST'])
def save_query():
    data          = request.get_json()
    prompt        = data.get('prompt', '').strip()
    sql_query     = data.get('sql_query', '').strip()
    dataset       = data.get('dataset', 'Customer Behaviour')
    detected_lang = data.get('detected_lang', 'en')
    original      = data.get('original_prompt', prompt)

    if not prompt or not sql_query:
        return jsonify({'error': 'prompt and sql_query required'}), 400

    created_at = datetime.now().strftime('%m/%d/%Y %H:%M')
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO sql_queries (prompt, sql_query, dataset, detected_lang, original_prompt, created_at) VALUES (?,?,?,?,?,?)',
        (prompt, sql_query, dataset, detected_lang, original, created_at)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM sql_queries WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route('/api/queries/<int:qid>/save', methods=['PATCH'])
def mark_saved(qid):
    conn = get_db()
    conn.execute('UPDATE sql_queries SET saved=1 WHERE id=?', (qid,))
    conn.commit()
    row = conn.execute('SELECT * FROM sql_queries WHERE id=?', (qid,)).fetchone()
    conn.close()
    if not row: return jsonify({'error': 'not found'}), 404
    return jsonify(dict(row))


@app.route('/api/queries/<int:qid>', methods=['DELETE'])
def delete_query(qid):
    conn = get_db()
    conn.execute('DELETE FROM sql_queries WHERE id=?', (qid,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': qid})


@app.route('/api/queries', methods=['DELETE'])
def clear_queries():
    conn = get_db()
    conn.execute('DELETE FROM sql_queries')
    conn.commit()
    conn.close()
    return jsonify({'cleared': True})


# ─── Dashboard History API ────────────────────────────────────────────────────

@app.route('/api/dashboards', methods=['GET'])
def get_dashboards():
    conn = get_db()
    rows = conn.execute('SELECT * FROM dashboards ORDER BY id DESC').fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try: d['config'] = json.loads(d['config_json']) if d['config_json'] else {}
        except: d['config'] = {}
        result.append(d)
    return jsonify(result)


@app.route('/api/dashboards', methods=['POST'])
def save_dashboard():
    data          = request.get_json()
    title         = data.get('title', 'Untitled Dashboard')
    prompt        = data.get('prompt', '')
    original      = data.get('original_prompt', prompt)
    detected_lang = data.get('detected_lang', 'en')
    config        = data.get('config', {})
    insight       = data.get('insight', '')
    created_at    = datetime.now().strftime('%m/%d/%Y %H:%M')

    conn = get_db()
    cur = conn.execute(
        'INSERT INTO dashboards (title, prompt, original_prompt, detected_lang, config_json, insight, created_at) VALUES (?,?,?,?,?,?,?)',
        (title, prompt, original, detected_lang, json.dumps(config), insight, created_at)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM dashboards WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()
    d = dict(row)
    try: d['config'] = json.loads(d['config_json'])
    except: d['config'] = {}
    return jsonify(d), 201


@app.route('/api/dashboards/<int:did>', methods=['DELETE'])
def delete_dashboard(did):
    conn = get_db()
    conn.execute('DELETE FROM dashboards WHERE id=?', (did,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': did})


@app.route('/api/dashboards', methods=['DELETE'])
def clear_dashboards():
    conn = get_db()
    conn.execute('DELETE FROM dashboards')
    conn.commit()
    conn.close()
    return jsonify({'cleared': True})


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    total_q = conn.execute('SELECT COUNT(*) FROM sql_queries').fetchone()[0]
    saved_q = conn.execute('SELECT COUNT(*) FROM sql_queries WHERE saved=1').fetchone()[0]
    total_d = conn.execute('SELECT COUNT(*) FROM dashboards').fetchone()[0]
    conn.close()
    return jsonify({
        'total_queries': total_q, 'saved_queries': saved_q,
        'total_dashboards': total_d, 'db_path': DB_PATH,
        'translation_available': TRANSLATION_AVAILABLE
    })


# ─── Serve frontend ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if not os.path.exists(index_path):
        return (
            "<h2 style='font-family:sans-serif;color:#c0392b'>⚠️ index.html not found</h2>"
            "<p style='font-family:sans-serif'>Place <b>index.html</b> inside <code>static/</code> folder</p>"
            "<p style='font-family:sans-serif'>Path: <code>" + index_path + "</code></p>"
        ), 404
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    init_db()
    print('\n🚀 Analytica running at http://localhost:5000')
    print(f'🌍 Translation: {"✅ Ready" if TRANSLATION_AVAILABLE else "❌ Install: pip install deep-translator langdetect"}\n')
    app.run(debug=True, port=5000)
