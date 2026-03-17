"""
Analytica Backend - Flask + SQLite
Saves all SQL queries, dashboards and history to a local database.
Run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'analytica.db')

# ─── Database setup ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # SQL Queries table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sql_queries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt      TEXT NOT NULL,
            sql_query   TEXT NOT NULL,
            dataset     TEXT DEFAULT 'Customer Behaviour',
            created_at  TEXT NOT NULL,
            saved       INTEGER DEFAULT 0
        )
    ''')

    # Dashboard history table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dashboards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            prompt      TEXT,
            config_json TEXT,
            insight     TEXT,
            created_at  TEXT NOT NULL
        )
    ''')

    # Seed a few demo SQL rows if empty
    cur.execute('SELECT COUNT(*) FROM sql_queries')
    if cur.fetchone()[0] == 0:
        demos = [
            ('show top spending customers by city',
             "SELECT city_tier,\n  AVG(avg_online_spend) AS avg_online_spend,\n  AVG(avg_store_spend)  AS avg_store_spend,\n  COUNT(*)              AS customer_count\nFROM customer_behaviour\nGROUP BY city_tier\nORDER BY avg_online_spend DESC;",
             'Customer Behaviour'),
            ('gender wise shopping preference',
             "SELECT gender,\n  shopping_preference,\n  COUNT(*) AS count,\n  ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(PARTITION BY gender),2) AS pct\nFROM customer_behaviour\nGROUP BY gender, shopping_preference\nORDER BY gender, count DESC;",
             'Customer Behaviour'),
            ('monthly orders by age group',
             "SELECT\n  CASE\n    WHEN age BETWEEN 18 AND 25 THEN '18-25'\n    WHEN age BETWEEN 26 AND 35 THEN '26-35'\n    WHEN age BETWEEN 36 AND 45 THEN '36-45'\n    WHEN age BETWEEN 46 AND 55 THEN '46-55'\n    ELSE '55+'\n  END AS age_group,\n  ROUND(AVG(monthly_online_orders),2) AS avg_online_orders,\n  ROUND(AVG(monthly_store_visits),2)  AS avg_store_visits\nFROM customer_behaviour\nGROUP BY age_group\nORDER BY age_group;",
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
    rows = conn.execute(
        'SELECT * FROM sql_queries ORDER BY id DESC'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/queries', methods=['POST'])
def save_query():
    data = request.get_json()
    prompt    = data.get('prompt', '').strip()
    sql_query = data.get('sql_query', '').strip()
    dataset   = data.get('dataset', 'Customer Behaviour')
    if not prompt or not sql_query:
        return jsonify({'error': 'prompt and sql_query required'}), 400
    created_at = datetime.now().strftime('%m/%d/%Y %H:%M')
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO sql_queries (prompt, sql_query, dataset, created_at) VALUES (?,?,?,?)',
        (prompt, sql_query, dataset, created_at)
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute('SELECT * FROM sql_queries WHERE id=?', (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route('/api/queries/<int:qid>/save', methods=['PATCH'])
def mark_saved(qid):
    conn = get_db()
    conn.execute('UPDATE sql_queries SET saved=1 WHERE id=?', (qid,))
    conn.commit()
    row = conn.execute('SELECT * FROM sql_queries WHERE id=?', (qid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
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
    rows = conn.execute(
        'SELECT * FROM dashboards ORDER BY id DESC'
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['config'] = json.loads(d['config_json']) if d['config_json'] else {}
        except Exception:
            d['config'] = {}
        result.append(d)
    return jsonify(result)


@app.route('/api/dashboards', methods=['POST'])
def save_dashboard():
    data = request.get_json()
    title      = data.get('title', 'Untitled Dashboard')
    prompt     = data.get('prompt', '')
    config     = data.get('config', {})
    insight    = data.get('insight', '')
    created_at = datetime.now().strftime('%m/%d/%Y %H:%M')
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO dashboards (title, prompt, config_json, insight, created_at) VALUES (?,?,?,?,?)',
        (title, prompt, json.dumps(config), insight, created_at)
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute('SELECT * FROM dashboards WHERE id=?', (new_id,)).fetchone()
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


# ─── Stats endpoint ───────────────────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    total_q   = conn.execute('SELECT COUNT(*) FROM sql_queries').fetchone()[0]
    saved_q   = conn.execute('SELECT COUNT(*) FROM sql_queries WHERE saved=1').fetchone()[0]
    total_d   = conn.execute('SELECT COUNT(*) FROM dashboards').fetchone()[0]
    conn.close()
    return jsonify({
        'total_queries': total_q,
        'saved_queries': saved_q,
        'total_dashboards': total_d,
        'db_path': DB_PATH
    })


# ─── Serve frontend ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print('\n🚀 Analytica Backend running at http://localhost:5000\n')
    app.run(debug=True, port=5000)
