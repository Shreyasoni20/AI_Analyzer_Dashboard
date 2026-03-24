from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import sqlite3, os, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ── Language detection + translation ──
try:
    from deep_translator import GoogleTranslator
    from langdetect import detect as langdetect_detect, LangDetectException
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("⚠️  deep-translator / langdetect not installed.")

# ── API Keys ──
GEMINI_API_KEY   = "AIzaSyBUzEDkYLrAoBoem1NT_xpsjZgnAGV75ko"
HIVE_API_KEY     = "Y/KF/scB01Dx/Ds3Yzo8dQ=="
GOOGLE_CSE_KEY   = "AIzaSyBUzEDkYLrAoBoem1NT_xpsjZgnAGV75ko"
GOOGLE_CSE_ID    = "a5ff7379d35254248"
GROQ_API_KEY     = "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"

GEMINI_AVAILABLE = False
GROQ_FALLBACK    = False

# ── Primary: Google Gemini ──
try:
    from google import genai as new_genai
    _new_genai_client = new_genai.Client(api_key=GEMINI_API_KEY)
    _new_genai_client.models.generate_content(model='gemini-2.0-flash', contents='hi')
    GEMINI_AVAILABLE = True
    USE_NEW_GENAI = True
    print("✅ Google Gemini ready (gemini-2.0-flash / new SDK)")
except Exception as e1:
    USE_NEW_GENAI = False
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_models = ['gemini-2.0-flash-exp', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        _gemini_model = None
        for model_name in gemini_models:
            try:
                _gemini_model = genai.GenerativeModel(model_name)
                _gemini_model.generate_content("hi", generation_config={"max_output_tokens": 5})
                GEMINI_AVAILABLE = True
                print(f"✅ Google Gemini ready ({model_name})")
                break
            except Exception as me:
                print(f"  ⚠️  {model_name} failed: {me}")
                _gemini_model = None
        if not GEMINI_AVAILABLE:
            print(f"❌ All Gemini models failed (also tried new SDK: {e1})")
    except ImportError:
        print("⚠️  google-generativeai not installed.")
    except Exception as e:
        print(f"⚠️  Gemini init failed: {e}")

# ── Fallback: Groq ──
if not GEMINI_AVAILABLE:
    try:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
        GROQ_FALLBACK = True
        GEMINI_AVAILABLE = True
        print("✅ Groq fallback ready (llama-3.3-70b-versatile)")
    except ImportError:
        print("⚠️  groq not installed.")
    except Exception as e:
        print(f"⚠️  Groq fallback failed: {e}")


def gemini_generate(prompt_text):
    if not GEMINI_AVAILABLE:
        return None
    if not GROQ_FALLBACK:
        try:
            if USE_NEW_GENAI:
                resp = _new_genai_client.models.generate_content(model='gemini-2.0-flash', contents=prompt_text)
                return resp.text
            else:
                resp = _gemini_model.generate_content(prompt_text, generation_config={"temperature": 0.1, "max_output_tokens": 2048})
                return resp.text
        except Exception as e:
            print(f"Gemini error: {e} — trying Groq fallback")
    try:
        resp = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.1, max_tokens=2048)
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Groq fallback error: {e}")
        return None


SEARCH_AVAILABLE = False
try:
    import requests as _req_test
    SEARCH_AVAILABLE = True
    print("✅ Google Custom Search ready")
except ImportError:
    print("⚠️  requests not installed.")

try:
    import requests
    from bs4 import BeautifulSoup
    URL_FETCH_AVAILABLE = True
except ImportError:
    URL_FETCH_AVAILABLE = False

app = Flask(__name__, static_folder='static')
CORS(app)

DB_PATH    = os.path.join(os.path.dirname(__file__), 'analytica.db')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

LANG_NAMES = {
    'en': 'English', 'hi': 'Hindi', 'de': 'German', 'fr': 'French', 'es': 'Spanish',
    'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese', 'ko': 'Korean',
    'zh-cn': 'Chinese', 'zh-tw': 'Chinese', 'ar': 'Arabic', 'tr': 'Turkish',
    'bn': 'Bengali', 'ta': 'Tamil', 'mr': 'Marathi', 'gu': 'Gujarati', 'ur': 'Urdu',
}


@app.route('/api/translate', methods=['POST'])
def translate_prompt():
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'text is required'}), 400
    if not TRANSLATION_AVAILABLE:
        return jsonify({'original': text, 'translated': text, 'detected_lang': 'unknown', 'lang_name': 'Unknown'})
    try:
        detected  = langdetect_detect(text)
        lang_name = LANG_NAMES.get(detected, detected.upper())
        if detected in ('en',):
            return jsonify({'original': text, 'translated': text, 'detected_lang': detected, 'lang_name': lang_name})
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return jsonify({'original': text, 'translated': translated, 'detected_lang': detected, 'lang_name': lang_name})
    except LangDetectException:
        return jsonify({'original': text, 'translated': text, 'detected_lang': 'en', 'lang_name': 'English (fallback)'})
    except Exception as e:
        return jsonify({'original': text, 'translated': text, 'detected_lang': 'unknown', 'lang_name': 'Unknown', 'error': str(e)})


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS sql_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT NOT NULL,
        sql_query TEXT NOT NULL, dataset TEXT DEFAULT 'Customer Behaviour',
        detected_lang TEXT DEFAULT 'en', original_prompt TEXT DEFAULT '',
        created_at TEXT NOT NULL, saved INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS dashboards (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        prompt TEXT, original_prompt TEXT DEFAULT '', detected_lang TEXT DEFAULT 'en',
        config_json TEXT, insight TEXT, created_at TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS fact_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_text TEXT NOT NULL, input_type TEXT DEFAULT 'text',
        detected_lang TEXT DEFAULT 'en', lang_name TEXT DEFAULT 'English',
        overall_score REAL DEFAULT 0, total_claims INTEGER DEFAULT 0,
        true_count INTEGER DEFAULT 0, false_count INTEGER DEFAULT 0,
        partial_count INTEGER DEFAULT 0, unverifiable_count INTEGER DEFAULT 0,
        conflict_count INTEGER DEFAULT 0, claims_json TEXT,
        search_queries_json TEXT, ai_text_score REAL DEFAULT NULL,
        created_at TEXT NOT NULL)''')
    cur.execute('SELECT COUNT(*) FROM sql_queries')
    if cur.fetchone()[0] == 0:
        now = datetime.now().strftime('%m/%d/%Y %H:%M')
        demos = [
            ('show top spending customers by city',
             "SELECT city_tier,\n  AVG(avg_online_spend) AS avg_online_spend,\n  AVG(avg_store_spend) AS avg_store_spend,\n  COUNT(*) AS customer_count\nFROM customer_behaviour\nGROUP BY city_tier\nORDER BY avg_online_spend DESC;",
             'Customer Behaviour'),
            ('gender wise shopping preference',
             "SELECT gender, shopping_preference, COUNT(*) AS count\nFROM customer_behaviour\nGROUP BY gender, shopping_preference\nORDER BY gender, count DESC;",
             'Customer Behaviour'),
        ]
        for p, s, d in demos:
            cur.execute('INSERT INTO sql_queries (prompt,sql_query,dataset,created_at) VALUES (?,?,?,?)', (p, s, d, now))
    conn.commit()
    conn.close()
    print(f'✅ Database ready at {DB_PATH}')


@app.route('/api/queries', methods=['GET'])
def get_queries():
    conn = get_db()
    rows = conn.execute('SELECT * FROM sql_queries ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/queries', methods=['POST'])
def save_query():
    data = request.get_json()
    prompt    = data.get('prompt', '').strip()
    sql_query = data.get('sql_query', '').strip()
    if not prompt or not sql_query:
        return jsonify({'error': 'required'}), 400
    created_at = datetime.now().strftime('%m/%d/%Y %H:%M')
    conn = get_db()
    cur  = conn.execute(
        'INSERT INTO sql_queries (prompt,sql_query,dataset,detected_lang,original_prompt,created_at) VALUES (?,?,?,?,?,?)',
        (prompt, sql_query, data.get('dataset', 'Customer Behaviour'),
         data.get('detected_lang', 'en'), data.get('original_prompt', prompt), created_at))
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


@app.route('/api/dashboards', methods=['GET'])
def get_dashboards():
    conn = get_db()
    rows = conn.execute('SELECT * FROM dashboards ORDER BY id DESC').fetchall()
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
    created_at = datetime.now().strftime('%m/%d/%Y %H:%M')
    conn = get_db()
    cur  = conn.execute(
        'INSERT INTO dashboards (title,prompt,original_prompt,detected_lang,config_json,insight,created_at) VALUES (?,?,?,?,?,?,?)',
        (data.get('title', 'Untitled'), data.get('prompt', ''), data.get('original_prompt', ''),
         data.get('detected_lang', 'en'), json.dumps(data.get('config', {})), data.get('insight', ''), created_at))
    conn.commit()
    row = conn.execute('SELECT * FROM dashboards WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()
    d = dict(row)
    try:
        d['config'] = json.loads(d['config_json'])
    except Exception:
        d['config'] = {}
    return jsonify(d), 201


@app.route('/api/dashboards', methods=['DELETE'])
def clear_dashboards():
    conn = get_db()
    conn.execute('DELETE FROM dashboards')
    conn.commit()
    conn.close()
    return jsonify({'cleared': True})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    total_q  = conn.execute('SELECT COUNT(*) FROM sql_queries').fetchone()[0]
    saved_q  = conn.execute('SELECT COUNT(*) FROM sql_queries WHERE saved=1').fetchone()[0]
    total_d  = conn.execute('SELECT COUNT(*) FROM dashboards').fetchone()[0]
    total_fc = conn.execute('SELECT COUNT(*) FROM fact_checks').fetchone()[0]
    conn.close()
    return jsonify({
        'total_queries': total_q, 'saved_queries': saved_q,
        'total_dashboards': total_d, 'total_fact_checks': total_fc,
        'db_path': DB_PATH,
        'translation_available': TRANSLATION_AVAILABLE,
        'groq_available': GEMINI_AVAILABLE,
        'search_available': SEARCH_AVAILABLE
    })


# ════════════════════════════════════════════════════════════════════════════
# FACT CHECK PIPELINE
# ════════════════════════════════════════════════════════════════════════════

def fetch_url_text(url):
    if not URL_FETCH_AVAILABLE:
        return None, "requests/beautifulsoup4 not installed"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        text = re.sub(r'\s+', ' ', soup.get_text(separator=' ', strip=True)).strip()
        return text[:8000], None
    except Exception as e:
        return None, str(e)


def extract_claims_with_gemini(text, lang_name='English'):
    if not GEMINI_AVAILABLE:
        return [], "AI not available"
    lang_note = f"The text is in {lang_name}. Extract claims and return them in {lang_name}." if lang_name != 'English' else ""

    word_count = len(text.strip().split())
    sentences_raw = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 8]
    sentence_count = len(sentences_raw)

    if word_count <= 30 or sentence_count <= 1:
        clean = text.strip().rstrip('.').strip()
        print(f"[extract_claims] Short input ({word_count} words) → single claim: {clean[:60]}")
        return [clean], None

    if sentence_count <= 5:
        claims_list = [s.rstrip('.').strip() for s in sentences_raw[:4]]
        print(f"[extract_claims] Medium input → {len(claims_list)} sentence claims")
        return claims_list, None

    prompt = f"""Extract up to 5 key verifiable factual claims from this article. {lang_note}

STRICT RULES:
- Each claim must be a COMPLETE sentence taken or summarized from the text.
- DO NOT split one idea into parts. Keep subject + predicate together.
- Each claim must be independently verifiable (has a fact that can be checked).
- DO NOT extract opinions, only factual statements.
- Return claims as they appear — sentence by sentence if possible.

Text: {text[:2000]}

Return ONLY a JSON array of strings. No markdown, no explanation:"""
    result = None
    try:
        result = gemini_generate(prompt)
        if not result:
            return [], "AI returned empty"
        result = result.strip()
        result = re.sub(r'```json|```|`', '', result).strip()
        arr_match = re.search(r'\[.*?\]', result, re.DOTALL)
        if arr_match:
            result = arr_match.group(0)
        claims = json.loads(result)
        if isinstance(claims, list) and len(claims) > 0:
            return [str(c) for c in claims if c], None
        return [], "No claims found in response"
    except Exception as e:
        print(f"[DEBUG] Extract error: {e}")
        try:
            lines = [l.strip() for l in result.split('\n') if l.strip()]
            lines = [re.sub(r'^[\d\.\-\*\)]+\s*', '', l) for l in lines]
            lines = [l for l in lines if len(l) > 15]
            if lines:
                return lines[:8], None
        except Exception:
            pass
        return [], str(e)


def generate_search_queries(claim):
    c_lower = claim.lower()
    alive_kws = ['is alive', 'still alive', 'is living', 'is live']
    dead_kws  = ['is dead', 'has died', 'passed away', 'is deceased', 'died']
    if any(kw in c_lower for kw in alive_kws + dead_kws):
        words  = claim.split()[:4]
        person = ' '.join(words)
        return [f"{person} death 2024 2025", f"{person} died when alive status"]

    if GEMINI_AVAILABLE:
        try:
            prompt = f"""Generate 2 short Google search queries to fact-check this claim.
CLAIM: "{claim}"
Rules:
- Query 1: search for the main fact (e.g. "who is PM of Pakistan 2026")
- Query 2: search to verify or debunk
Return ONLY a JSON array of 2 strings. No explanation."""
            result = gemini_generate(prompt)
            if result:
                result = re.sub(r'```json|```', '', result).strip()
                arr = re.search(r'\[.*?\]', result, re.DOTALL)
                if arr:
                    queries = json.loads(arr.group(0))
                    if isinstance(queries, list) and len(queries) >= 1:
                        return [str(q) for q in queries[:2]]
        except Exception as e:
            print(f"[generate_search_queries] error: {e}")

    stop = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'has', 'have', 'had', 'be', 'been',
            'of', 'in', 'on', 'at', 'to', 'for', 'with', 'that', 'this', 'it', 'its'}
    words    = re.findall(r'[a-zA-Z0-9]+', claim)
    keywords = [w for w in words if w.lower() not in stop and len(w) > 2][:7]
    q1 = ' '.join(keywords[:5])
    q2 = claim[:80] + ' fact check'
    return [q1, q2]


def duckduckgo_search(query):
    try:
        import urllib.parse
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
        resp = requests.get(url, headers={'User-Agent': 'Analytica/1.0'}, timeout=8)
        data = resp.json()
        results = []
        if data.get('Abstract'):
            results.append({'title': data.get('AbstractSource', 'DuckDuckGo'), 'url': data.get('AbstractURL', ''), 'content': data.get('Abstract', '')[:600], 'score': 0.9})
        if data.get('Answer'):
            results.append({'title': 'DuckDuckGo Answer', 'url': '', 'content': data.get('Answer', '')[:300], 'score': 0.95})
        for topic in data.get('RelatedTopics', [])[:3]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append({'title': topic.get('Text', '')[:60], 'url': topic.get('FirstURL', ''), 'content': topic.get('Text', '')[:300], 'score': 0.7})
        print(f"[DuckDuckGo] Query: '{query}' → {len(results)} results")
        return results
    except Exception as e:
        print(f"[DuckDuckGo] Error: {e}")
        return []


def search_evidence(query):
    if not SEARCH_AVAILABLE:
        return []
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_ID, "q": query, "num": 5, "safe": "active"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        evidence = []
        for item in data.get("items", []):
            snippet = item.get("snippet", "")
            metatags = item.get("pagemap", {}).get("metatags", [{}])
            og_desc  = metatags[0].get("og:description", "") if metatags else ""
            content  = og_desc if len(og_desc) > len(snippet) else snippet
            evidence.append({"title": item.get("title", ""), "url": item.get("link", ""), "content": content[:600], "score": 1.0})
        print(f"[Google Search] Query: '{query}' → {len(evidence)} results")
        return evidence
    except Exception as e:
        print(f"Google Search error: {e}")
        try:
            from tavily import TavilyClient
            tc = TavilyClient(api_key="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")
            result = tc.search(query=query, max_results=5, search_depth="basic")
            ev = [{"title": r.get("title",""), "url": r.get("url",""), "content": r.get("content","")[:600], "score": r.get("score",0)} for r in result.get("results",[])]
            return ev
        except Exception as e2:
            print(f"  Tavily fallback error: {e2}")
            return []


def pre_check_claim(claim):
    c = claim.lower().strip()
    NAME_ALIASES = {
        'man mohan': 'manmohan singh', 'manmohan': 'manmohan singh',
        'dr singh': 'manmohan singh', 'dr manmohan': 'manmohan singh',
        'khamenei': 'ali khamenei', 'queen elizabeth': 'queen elizabeth ii',
        'mahatma': 'mahatma gandhi', 'bapu': 'mahatma gandhi',
        'pm modi': 'narendra modi', 'shri modi': 'narendra modi',
    }
    for alias, full_name in NAME_ALIASES.items():
        if alias in c:
            c = c.replace(alias, full_name)

    # ── SPORTS KNOWN FACTS ──
    # India T20 World Cup wins
    if ('india' in c) and ('t20 world cup' in c or 't20 wc' in c):
        if any(y in c for y in ['2007', '2024']):
            return {'verdict': 'TRUE', 'confidence': 99,
                    'explanation': 'India won the T20 World Cup in both 2007 (inaugural) and 2024.',
                    'key_evidence': 'India won T20 WC 2007 (vs Pakistan) and T20 WC 2024 (vs South Africa).',
                    'conflicting_info': ''}
        if '2022' in c or '2021' in c or '2016' in c:
            return {'verdict': 'FALSE', 'confidence': 95,
                    'explanation': f'India did not win the T20 World Cup in that year.',
                    'key_evidence': 'India won T20 WC only in 2007 and 2024.',
                    'conflicting_info': ''}

    # India ODI World Cup wins
    if ('india' in c) and ('world cup' in c or 'odi world cup' in c or 'cricket world cup' in c):
        if '1983' in c or '2011' in c:
            return {'verdict': 'TRUE', 'confidence': 99,
                    'explanation': 'India won the Cricket World Cup in 1983 and 2011.',
                    'key_evidence': 'India won ODI World Cup in 1983 (Kapil Dev) and 2011 (MS Dhoni).',
                    'conflicting_info': ''}

    # India won T20 match - generic claim with year
    if 'india' in c and ('won' in c or 'win' in c or 'beat' in c or 'defeated' in c):
        if ('t20' in c or 'match' in c or 'series' in c):
            # India regularly plays and wins T20 matches - this is TRUE in general
            # We only return TRUE for specific known series
            if '2020' in c and 'new zealand' in c:
                return {'verdict': 'TRUE', 'confidence': 98,
                        'explanation': 'India won the T20I series vs New Zealand in Jan 2020 (5-0 clean sweep in NZ).',
                        'key_evidence': 'India beat NZ 5-0 in T20I series in NZ, Jan 2020. Also won all individual T20 matches in that tour.',
                        'conflicting_info': ''}
            if '2020' in c:
                # India won multiple T20 series in 2020
                return {'verdict': 'PARTIALLY TRUE', 'confidence': 75,
                        'explanation': 'India won several T20 matches/series in 2020, but the specific match is unspecified.',
                        'key_evidence': 'India won T20I series vs NZ (5-0 in Jan 2020) among others in 2020.',
                        'conflicting_info': ''}

    # IPL known winners
    if 'ipl' in c or 'indian premier league' in c:
        IPL_WINNERS = {
            '2008': 'rajasthan royals', '2009': 'deccan chargers', '2010': 'chennai super kings',
            '2011': 'chennai super kings', '2012': 'kolkata knight riders', '2013': 'mumbai indians',
            '2014': 'kolkata knight riders', '2015': 'mumbai indians', '2016': 'sunrisers hyderabad',
            '2017': 'mumbai indians', '2018': 'chennai super kings', '2019': 'mumbai indians',
            '2020': 'mumbai indians', '2021': 'chennai super kings', '2022': 'gujarat titans',
            '2023': 'chennai super kings', '2024': 'kolkata knight riders',
        }
        for year, winner in IPL_WINNERS.items():
            if year in c and winner in c and ('won' in c or 'win' in c or 'champion' in c):
                return {'verdict': 'TRUE', 'confidence': 99,
                        'explanation': f'{winner.title()} won IPL {year}.',
                        'key_evidence': f'IPL {year} winner: {winner.title()}.',
                        'conflicting_info': ''}
            elif year in c and ('won' in c or 'win' in c or 'champion' in c):
                # Check if a wrong team is claimed
                for wrong_winner, _ in [(w, y) for y, w in IPL_WINNERS.items() if y != year]:
                    if wrong_winner in c:
                        return {'verdict': 'FALSE', 'confidence': 90,
                                'explanation': f'{wrong_winner.title()} did not win IPL {year}. {IPL_WINNERS.get(year,"").title()} did.',
                                'key_evidence': f'IPL {year} was won by {IPL_WINNERS.get(year,"").title()}.',
                                'conflicting_info': ''}

    # Football / FIFA World Cup
    if 'fifa world cup' in c or ('football' in c and 'world cup' in c):
        FIFA_WINNERS = {
            '2022': 'argentina', '2018': 'france', '2014': 'germany',
            '2010': 'spain', '2006': 'italy', '2002': 'brazil',
            '1998': 'france', '1994': 'brazil', '1990': 'west germany',
        }
        for year, winner in FIFA_WINNERS.items():
            if year in c and winner in c and ('won' in c or 'win' in c or 'champion' in c):
                return {'verdict': 'TRUE', 'confidence': 99,
                        'explanation': f'{winner.title()} won the FIFA World Cup {year}.',
                        'key_evidence': f'FIFA World Cup {year} winner: {winner.title()}.',
                        'conflicting_info': ''}

    KNOWN_FACTS = [
        ('narendra modi', 'prime minister', 'india', True),
        ('modi', 'prime minister', 'india', True),
        ('droupadi murmu', 'president', 'india', True),
        ('donald trump', 'president', 'united states', True),
        ('donald trump', 'president', 'america', True),
        ('trump', 'president', 'us', True),
        ('vladimir putin', 'president', 'russia', True),
        ('xi jinping', 'president', 'china', True),
        ('keir starmer', 'prime minister', 'uk', True),
        ('shehbaz sharif', 'prime minister', 'pakistan', True),
        ('elon musk', 'prime minister', '', False),
        ('elon musk', 'president', '', False),
        ('rishi sunak', 'prime minister', 'uk', False),
    ]
    for person, role, country, is_true in KNOWN_FACTS:
        if person in c and role in c and (not country or country in c):
            if is_true:
                return {'verdict': 'TRUE', 'confidence': 98, 'explanation': f'{person.title()} is indeed the {role}{" of " + country if country else ""}.', 'key_evidence': f'Verified: {person.title()} currently holds position of {role}.', 'conflicting_info': ''}
            else:
                return {'verdict': 'FALSE', 'confidence': 97, 'explanation': f'{person.title()} is not the {role}{" of " + country if country else ""}.', 'key_evidence': f'{person.title()} does not hold this position.', 'conflicting_info': ''}

    DEAD_PEOPLE = [
        ('indira gandhi', 1984), ('rajiv gandhi', 1991), ('mahatma gandhi', 1948),
        ('jawaharlal nehru', 1964), ('atal bihari vajpayee', 2018), ('manmohan singh', 2024),
        ('lal bahadur shastri', 1966), ('sardar vallabhbhai patel', 1950),
        ('bal thackeray', 2012), ('jayalalithaa', 2016), ('m karunanidhi', 2018),
        ('sushma swaraj', 2019), ('arun jaitley', 2019),
        ('abraham lincoln', 1865), ('adolf hitler', 1945), ('joseph stalin', 1953),
        ('napoleon', 1821), ('george washington', 1799), ('john f kennedy', 1963),
        ('fidel castro', 2016), ('muammar gaddafi', 2011), ('osama bin laden', 2011),
        ('saddam hussein', 2006), ('ali khamenei', 2025), ('queen elizabeth ii', 2022),
        ('martin luther king', 1968), ('princess diana', 1997), ('steve jobs', 2011),
        ('nelson mandela', 2013), ('michael jackson', 2009), ('kobe bryant', 2020),
        ('stephen hawking', 2018), ('albert einstein', 1955), ('isaac newton', 1727),
        ('sridevi', 2018), ('irrfan khan', 2020), ('rishi kapoor', 2020),
        ('dilip kumar', 2021), ('lata mangeshkar', 2022), ('bappi lahiri', 2022),
    ]

    ALIVE_PEOPLE = [
        ('narendra modi', 'Prime Minister of India'), ('vladimir putin', 'President of Russia'),
        ('xi jinping', 'President of China'), ('donald trump', 'President of the United States'),
        ('elon musk', 'CEO of Tesla and SpaceX'), ('bill gates', 'co-founder of Microsoft'),
        ('king charles', 'King of the United Kingdom'), ('joe biden', 'former President of the United States'),
        ('rahul gandhi', 'Leader of Opposition in India'), ('virat kohli', 'Indian cricketer'),
        ('amitabh bachchan', 'Indian actor'), ('shah rukh khan', 'Indian actor'),
    ]

    IS_ALIVE_KEYWORDS = ['is alive', 'is still alive', 'is living', 'is live', 'still living', 'is he alive', 'is she alive']
    IS_DEAD_KEYWORDS  = ['is dead', 'has died', 'passed away', 'is deceased', 'died recently', 'is no more']

    for person, desc in ALIVE_PEOPLE:
        if person in c:
            for kw in IS_ALIVE_KEYWORDS:
                if kw in c:
                    return {'verdict': 'TRUE', 'confidence': 97, 'explanation': f'{person.title()} is alive and currently serving as {desc}.', 'key_evidence': f'{person.title()} ({desc}) is alive as of 2025.', 'conflicting_info': ''}
            for kw in IS_DEAD_KEYWORDS:
                if kw in c:
                    return {'verdict': 'FALSE', 'confidence': 97, 'explanation': f'{person.title()} is alive ({desc}) — this claim is false.', 'key_evidence': f'{person.title()} is alive and active as of 2025.', 'conflicting_info': ''}

    for person, death_year in DEAD_PEOPLE:
        if death_year and person in c:
            for kw in IS_ALIVE_KEYWORDS:
                if kw in c:
                    return {'verdict': 'FALSE', 'confidence': 99, 'explanation': f'{person.title()} died in {death_year} and is not alive.', 'key_evidence': f'{person.title()} passed away in {death_year}.', 'conflicting_info': ''}
            for kw in IS_DEAD_KEYWORDS:
                if kw in c:
                    return {'verdict': 'TRUE', 'confidence': 99, 'explanation': f'{person.title()} died in {death_year}. This claim is correct.', 'key_evidence': f'{person.title()} passed away in {death_year}.', 'conflicting_info': ''}

    POLITICAL_ROLES = ['prime minister', 'president', 'pm', 'chief minister', 'cm', 'governor', 'chancellor', 'minister', 'senator', 'mp']
    for person, death_year in DEAD_PEOPLE:
        if death_year and person in c:
            for role in POLITICAL_ROLES:
                if role in c:
                    return {'verdict': 'FALSE', 'confidence': 99, 'explanation': f'{person.title()} died in {death_year} and cannot hold any current position.', 'key_evidence': f'{person.title()} is deceased (died {death_year})', 'conflicting_info': ''}

    NOT_POLITICIANS = ['elon musk', 'bill gates', 'jeff bezos', 'mark zuckerberg', 'sundar pichai',
                       'tim cook', 'warren buffett', 'cristiano ronaldo', 'lionel messi',
                       'sachin tendulkar', 'virat kohli', 'shah rukh khan', 'amitabh bachchan', 'taylor swift']
    for person in NOT_POLITICIANS:
        if person in c:
            for role in POLITICAL_ROLES:
                if role in c:
                    return {'verdict': 'FALSE', 'confidence': 97, 'explanation': f'{person.title()} is not a politician and does not hold any government position.', 'key_evidence': f'{person.title()} is a business/celebrity figure, not a government official.', 'conflicting_info': ''}

    return None


def scrape_wikipedia_direct(query):
    try:
        import urllib.parse
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit=2&format=json"
        resp = requests.get(search_url, timeout=8)
        items = resp.json().get('query',{}).get('search',[])
        results = []
        for item in items[:2]:
            title = item.get('title','')
            extract_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=extracts&exintro=0&exlimit=1&format=json&explaintext=1&exsectionformat=plain"
            eresp = requests.get(extract_url, timeout=8)
            pages = eresp.json().get('query',{}).get('pages',{})
            for pid, page in pages.items():
                extract = page.get('extract','')[:1000]
                if extract:
                    results.append({'title': title, 'url': f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ','_'))}", 'content': extract, 'score': 0.95, 'source': 'Wikipedia'})
        print(f"[Wikipedia Direct] '{query[:40]}' → {len(results)} pages")
        return results
    except Exception as e:
        print(f"[Wikipedia Direct] Error: {e}")
        return []


def google_news_search(query):
    try:
        import urllib.parse, xml.etree.ElementTree as ET
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall('.//item')
        results = []
        for item in items[:5]:
            title   = item.findtext('title', '')
            link    = item.findtext('link', '')
            desc    = item.findtext('description', '')
            pubdate = item.findtext('pubDate', '')
            desc = re.sub(r'<[^>]+>', '', desc).strip()
            if title:
                results.append({'title': title, 'url': link, 'content': f"{desc} [Published: {pubdate}]".strip(), 'score': 0.92, 'source': 'Google News'})
        print(f"[Google News RSS] '{query[:50]}' → {len(results)} articles")
        return results
    except Exception as e:
        print(f"[Google News RSS] Error: {e}")
        return []


def multi_source_search(claim):
    """Search multiple free sources. Priority: Wikipedia → Google News → DuckDuckGo → Tavily"""
    results = []

    try:
        results.extend(scrape_wikipedia_direct(claim))
    except Exception as e:
        print(f"[multi_source] Wikipedia error: {e}")

    try:
        results.extend(google_news_search(claim))
    except Exception as e:
        print(f"[multi_source] Google News error: {e}")

    try:
        import urllib.parse
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(claim)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(ddg_url, headers={'User-Agent':'Analytica/1.0'}, timeout=8)
        data = resp.json()
        if data.get('Abstract'):
            results.append({'title': data.get('AbstractSource','DuckDuckGo'), 'url': data.get('AbstractURL',''), 'content': data.get('Abstract','')[:600], 'score': 0.9, 'source': 'DuckDuckGo'})
        if data.get('Answer'):
            results.append({'title': 'DuckDuckGo Answer', 'url': '', 'content': data.get('Answer',''), 'score': 0.95, 'source': 'DuckDuckGo'})
    except Exception as e:
        print(f"[DDG] Error: {e}")

    try:
        from tavily import TavilyClient
        tc = TavilyClient(api_key="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")
        tavily_results = tc.search(query=claim[:100], max_results=4, search_depth="basic")
        for r in tavily_results.get('results', []):
            results.append({'title': r.get('title',''), 'url': r.get('url',''), 'content': r.get('content','')[:600], 'score': r.get('score', 0.7), 'source': 'Tavily'})
    except Exception as e:
        print(f"[Tavily] Error: {e}")

    seen = set()
    unique = []
    for r in results:
        key = r.get('url','') or r.get('title','')
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"[multi_source_search] Total unique: {len(unique)}")
    return unique[:8]


def calculate_confidence(claim, evidence_list):
    if not evidence_list:
        return 0
    claim_words = set(w.lower() for w in claim.split() if len(w) > 3)
    matching = 0
    for ev in evidence_list:
        content = (ev.get('content','') + ev.get('title','')).lower()
        matches = sum(1 for w in claim_words if w in content)
        if matches >= len(claim_words) * 0.4:
            matching += 1
    confidence = round((matching / len(evidence_list)) * 100)
    return confidence


def google_fact_check(claim):
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {"key": GEMINI_API_KEY, "query": claim[:200], "languageCode": "en"}
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        claims_found = data.get("claims", [])
        if not claims_found:
            return None
        best    = claims_found[0]
        reviews = best.get("claimReview", [])
        if not reviews:
            return None
        review     = reviews[0]
        rating     = review.get("textualRating", "").upper()
        publisher  = review.get("publisher", {}).get("name", "")
        review_url = review.get("url", "")
        verdict = "UNVERIFIABLE"
        confidence = 50
        if any(w in rating for w in ["TRUE", "CORRECT", "ACCURATE", "VERIFIED", "FACT"]):
            verdict = "TRUE"; confidence = 90
        elif any(w in rating for w in ["FALSE", "WRONG", "INCORRECT", "FAKE", "MISLEAD", "DEBUNK", "LIE"]):
            verdict = "FALSE"; confidence = 92
        elif any(w in rating for w in ["PARTIAL", "HALF", "MOSTLY", "MIXED"]):
            verdict = "PARTIALLY TRUE"; confidence = 75
        print(f"[FactCheck API] '{claim[:40]}' → {verdict} ({rating}) by {publisher}")
        return {"verdict": verdict, "confidence": confidence, "explanation": f"Fact-checked by {publisher}: rated as '{review.get('textualRating', 'Unknown')}'", "key_evidence": f"Source: {publisher} ({review_url})", "conflicting_info": "", "sources": [{"title": f"Fact Check by {publisher}", "url": review_url}]}
    except Exception as e:
        print(f"[FactCheck API] Error: {e}")
        return None


def wikidata_check(claim):
    try:
        c = claim.lower()
        is_alive_q = any(w in c for w in ['is alive', 'still alive', 'is living'])
        is_dead_q  = any(w in c for w in ['is dead', 'has died', 'passed away', 'died'])
        if not (is_alive_q or is_dead_q):
            return []
        words = [w for w in claim.split()[:5] if len(w) > 2]
        person_name = " ".join(words[:3])
        sparql_query = f"""
        SELECT ?item ?itemLabel ?deathDate WHERE {{
          ?item wdt:P31 wd:Q5 .
          ?item rdfs:label "{person_name}"@en .
          OPTIONAL {{ ?item wdt:P570 ?deathDate . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 3"""
        url = "https://query.wikidata.org/sparql"
        resp = requests.get(url, params={"query": sparql_query, "format": "json"}, headers={"User-Agent": "Analytica/1.0"}, timeout=10)
        bindings = resp.json().get("results", {}).get("bindings", [])
        evidence = []
        for b in bindings:
            label      = b.get("itemLabel", {}).get("value", person_name)
            death_date = b.get("deathDate", {}).get("value", "")
            if death_date:
                evidence.append({"title": f"{label} — Wikidata", "url": "https://www.wikidata.org", "content": f"{label} died on {death_date[:10]} according to Wikidata.", "score": 0.95})
            else:
                evidence.append({"title": f"{label} — Wikidata", "url": "https://www.wikidata.org", "content": f"{label} — no death date recorded (may still be alive).", "score": 0.8})
        return evidence
    except Exception as e:
        print(f"[Wikidata] Error: {e}")
        return []


def verify_claim(claim, evidence_list, lang_name='English'):
    if not GEMINI_AVAILABLE:
        return {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': 'AI not available', 'sources': []}

    # Layer 1: Pre-check obvious facts
    pre = pre_check_claim(claim)
    if pre:
        print(f"[pre_check] Caught: {claim[:60]} → {pre['verdict']}")
        pre['sources'] = [{'title': e.get('title', ''), 'url': e.get('url', '')} for e in evidence_list[:3]]
        return pre

    # Layer 2: Google Fact Check API
    fact_check_result = google_fact_check(claim)
    if fact_check_result:
        fact_check_result['sources'] = [{'title': e.get('title', ''), 'url': e.get('url', '')} for e in evidence_list[:3]]
        return fact_check_result

    # Layer 3: AI with web evidence
    lang_note = f"Reply in {lang_name}." if lang_name != 'English' else ""
    evidence_text = " | ".join([f"{e.get('title', '')} - {e.get('content', '')[:200]}" for e in evidence_list[:5]])
    has_evidence = bool(evidence_text and len(evidence_text) > 30)

    # Detect claim type for better prompting
    c_lower = claim.lower()
    is_sports = any(w in c_lower for w in ['match', 'won', 'win', 'beat', 'defeated', 'score', 't20', 'odi', 'test', 'ipl', 'cricket', 'football', 'tournament', 'series', 'cup', 'championship', 'goal', 'runs', 'wicket'])
    is_science = any(w in c_lower for w in ['launched', 'mission', 'planet', 'satellite', 'isro', 'nasa', 'space', 'rocket', 'discovered', 'invented'])
    is_political = any(w in c_lower for w in ['prime minister', 'president', 'minister', 'government', 'election', 'voted', 'party', 'cm', 'pm'])

    sports_hint = """
SPORTS CLAIM RULES (very important):
- India has won MANY T20 matches/series over the years — a generic claim like "India won a T20 match" is almost always TRUE
- If the claim says India won a T20 series/match in a specific year, check web evidence for that year
- "India won t20 match in 2020" — India played many T20s in Jan 2020 (beat NZ 5-0) — this is TRUE
- Look at the web evidence titles carefully — if they show India playing/winning in that year, verdict is TRUE
- Do NOT mark sports claims FALSE just because you lack exact details — use PARTIALLY TRUE if year/opponent unclear
- If evidence shows India cricket results page for that year, the claim is likely TRUE
""" if is_sports else ""

    science_hint = """
SCIENCE/SPACE CLAIM RULES:
- ISRO launches satellites and spacecraft, NOT missiles at planets — such claims are FALSE or misleading
- NASA/ISRO missions to Mars, Moon, Sun (Aditya) are real — verify year/details
- "Chandrayaan-3 landed on moon" (2023) → TRUE
- "India went to Mars" (Mangalyaan 2014) → TRUE
""" if is_science else ""

    prompt = f"""You are a rigorous fact-checking AI with deep knowledge of sports, science, politics, and current events. Today is 2025/2026. {lang_note}

CLAIM: "{claim}"

WEB EVIDENCE (use these to verify):
{evidence_text if has_evidence else "No direct web results found — rely on your training knowledge."}

{sports_hint}{science_hint}

ANALYSIS STEPS:
1. What do you know about this claim from training data?
2. What does the web evidence show? (Read titles and content carefully)
3. Does evidence SUPPORT or CONTRADICT the claim?

CRITICAL RULES:
- If web evidence shows results/scores/schedules related to the claim → it likely SUPPORTS the claim → TRUE or PARTIALLY TRUE
- Celebrities/businessmen CANNOT hold political office → FALSE  
- Generic sports claims ("India won a match in year X") — India plays ~30+ T20 matches/year, winning most → likely TRUE
- Only mark FALSE if evidence clearly contradicts the claim
- Only UNVERIFIABLE if truly zero evidence and claim is obscure/unknowable
- NEVER mark FALSE just because evidence is about a different specific match — use PARTIALLY TRUE
- Confidence: 90+ for clear facts, 70-85 for likely true, 50-65 for uncertain

Return ONLY valid JSON, nothing else:
{{"verdict":"TRUE"|"FALSE"|"PARTIALLY TRUE"|"UNVERIFIABLE"|"CONFLICTING","confidence":<0-100>,"explanation":"<one clear sentence explaining verdict>","key_evidence":"<specific evidence or knowledge that decided the verdict>","conflicting_info":""}}"""

    try:
        result = gemini_generate(prompt)
        if not result:
            return {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': 'No AI response', 'sources': []}
        result = re.sub(r'```json|```', '', result).strip()
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result = json_match.group(0)
        parsed = json.loads(result)
        v = parsed.get('verdict', '').upper().strip()
        if v not in ['TRUE', 'FALSE', 'PARTIALLY TRUE', 'UNVERIFIABLE', 'CONFLICTING']:
            parsed['verdict'] = 'UNVERIFIABLE'
        parsed['sources'] = [{'title': e.get('title', ''), 'url': e.get('url', '')} for e in evidence_list[:3]]
        return parsed
    except json.JSONDecodeError as e:
        print(f"[verify_claim] JSON error: {e}")
        return {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': 'Parse error', 'sources': []}
    except Exception as e:
        print(f"[verify_claim] Error: {e}")
        return {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': 'Verification failed', 'sources': []}


def detect_ai_text(text):
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = f'''Analyze if this text is AI-generated or human-written.
Text: "{text[:1200]}"
Return ONLY JSON: {{"ai_probability":<0-100>,"indicators":["ind1","ind2"],"verdict":"AI-Generated"|"Human-Written"|"Uncertain"}}'''
        result = gemini_generate(prompt)
        if not result:
            return None
        result = re.sub(r'```json|```', '', result).strip()
        return json.loads(result)
    except Exception as e:
        print(f"[detect_ai_text] Error: {e}")
        return None


@app.route('/api/factcheck/stream', methods=['POST', 'OPTIONS'])
def factcheck_stream():
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        resp.headers['Access-Control-Allow-Origin']  = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp

    data       = request.get_json() or {}
    input_text = data.get('text', '').strip()
    if not input_text:
        return jsonify({'error': 'text required'}), 400

    def generate():
        try:
            detected_lang = 'en'
            lang_name     = 'English'
            if TRANSLATION_AVAILABLE:
                try:
                    detected_lang = langdetect_detect(input_text)
                    lang_name     = LANG_NAMES.get(detected_lang, detected_lang.upper())
                except Exception:
                    pass
            yield f"data: {json.dumps({'step': 'lang', 'lang': detected_lang, 'lang_name': lang_name})}\n\n"

            is_url          = bool(re.match(r'^https?://\S+$', input_text))
            text_to_analyze = input_text

            if is_url:
                yield f"data: {json.dumps({'step': 'fetching_url', 'message': 'Fetching article…'})}\n\n"
                fetched, err = fetch_url_text(input_text)
                if fetched:
                    text_to_analyze = fetched
                yield f"data: {json.dumps({'step': 'url_fetched', 'chars': len(text_to_analyze)})}\n\n"

            yield f"data: {json.dumps({'step': 'extracting', 'message': 'Extracting claims…'})}\n\n"
            claims, err = extract_claims_with_gemini(text_to_analyze, lang_name)
            urls = re.findall(r'https?://[^\s]+', input_text)
            claims = claims + urls
            if not claims:
                yield f"data: {json.dumps({'step': 'error', 'message': 'No claims found. Try more factual text.'})}\n\n"
                return
            claims = claims[:4]
            yield f"data: {json.dumps({'step': 'claims_found', 'count': len(claims), 'claims': claims})}\n\n"

            yield f"data: {json.dumps({'step': 'generating_queries', 'message': 'Formulating queries…'})}\n\n"
            all_queries = [generate_search_queries(c) for c in claims]
            yield f"data: {json.dumps({'step': 'queries_ready', 'queries': all_queries})}\n\n"

            yield f"data: {json.dumps({'step': 'verifying', 'index': 0, 'claim': claims[0], 'total': len(claims)})}\n\n"

            # ══════════════════════════════════════════════════════════════
            # FIX: process_claim — proper URL vs text branching with else
            # ══════════════════════════════════════════════════════════════
            def process_claim(i):
                claim = claims[i]

                # ── URL claim: fetch and verify the page content ──
                if claim.startswith("http"):
                    text, err = fetch_url_text(claim)
                    if text:
                        ev = multi_source_search(text[:300])
                        result = verify_claim(text[:300], ev, lang_name)
                    else:
                        result = {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': 'URL could not be fetched', 'sources': []}
                    return i, result

                # ── Normal text claim: search + verify ──
                ev = []
                try:
                    ev = multi_source_search(claim)
                    ev.extend(wikidata_check(claim))
                    if SEARCH_AVAILABLE:
                        for q in all_queries[i][:1]:
                            ev.extend(search_evidence(q))
                    seen = set()
                    ev_dedup = []
                    for e in ev:
                        key = e.get('url','') or e.get('title','')
                        if key not in seen:
                            seen.add(key)
                            ev_dedup.append(e)
                    ev = ev_dedup[:10]
                    print(f"[process_claim] Claim {i}: {len(ev)} evidence items")
                    src_confidence = calculate_confidence(claim, ev)
                    print(f"[process_claim] Source confidence: {src_confidence}%")
                except Exception as e:
                    print(f"[process_claim] Search error for claim {i}: {e}")

                result = verify_claim(claim, ev, lang_name)
                print(f"[process_claim] Claim {i} verdict: {result.get('verdict')} ({result.get('confidence')}%)")
                return i, result
            # ══════════════════════════════════════════════════════════════

            verified_map = {}
            with ThreadPoolExecutor(max_workers=4) as ex:
                futures = {ex.submit(process_claim, i): i for i in range(len(claims))}
                for fut in as_completed(futures):
                    try:
                        idx, res = fut.result(timeout=30)
                    except Exception as e:
                        idx = futures[fut]
                        print(f"[stream] Future error for claim {idx}: {e}")
                        res = {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': 'Timeout or error', 'sources': []}
                    verified_map[idx] = res

            verified = []
            true_c = false_c = partial_c = unverifiable_c = conflict_c = 0
            for i, claim in enumerate(claims):
                result = verified_map.get(i, {'verdict': 'UNVERIFIABLE', 'confidence': 0, 'explanation': '', 'sources': []})
                v = result.get('verdict', 'UNVERIFIABLE').upper()
                if 'TRUE' in v and 'PARTIALLY' not in v: true_c += 1
                elif 'FALSE' in v: false_c += 1
                elif 'PARTIALLY' in v: partial_c += 1
                elif 'CONFLICT' in v: conflict_c += 1
                else: unverifiable_c += 1
                claim_obj = {
                    'claim':            claim,
                    'verdict':          result.get('verdict', 'UNVERIFIABLE'),
                    'confidence':       result.get('confidence', 0),
                    'explanation':      result.get('explanation', ''),
                    'key_evidence':     result.get('key_evidence', ''),
                    'conflicting_info': result.get('conflicting_info', ''),
                    'sources':          result.get('sources', []),
                    'search_queries':   all_queries[i]
                }
                verified.append(claim_obj)
                yield f"data: {json.dumps({'step': 'claim_done', 'index': i, 'result': claim_obj})}\n\n"

            yield f"data: {json.dumps({'step': 'ai_detection', 'message': 'Checking AI content…'})}\n\n"
            ai_result = detect_ai_text(text_to_analyze[:400])
            if ai_result:
                yield f"data: {json.dumps({'step': 'ai_done', 'result': ai_result})}\n\n"

            total      = len(verified)
            score      = round(((true_c + partial_c * 0.5) / total * 100) if total > 0 else 0, 1)
            if total > 0:
                true_perc    = (true_c / total) * 100
                false_perc   = (false_c / total) * 100
                partial_perc = (partial_c / total) * 100
                if true_perc >= 60:     final_verdict = "MOSTLY TRUE"
                elif false_perc >= 60:  final_verdict = "MOSTLY FALSE"
                elif partial_perc >= 40: final_verdict = "MIXED"
                else:                   final_verdict = "UNCERTAIN"
            else:
                final_verdict = "NO DATA"

            created_at = datetime.now().strftime('%m/%d/%Y %H:%M')
            conn = get_db()
            conn.execute(
                '''INSERT INTO fact_checks
                    (input_text,input_type,detected_lang,lang_name,overall_score,total_claims,
                     true_count,false_count,partial_count,unverifiable_count,conflict_count,
                     claims_json,search_queries_json,ai_text_score,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (input_text[:500], 'url' if is_url else 'text', detected_lang, lang_name, score, total,
                 true_c, false_c, partial_c, unverifiable_c, conflict_c,
                 json.dumps(verified), json.dumps(all_queries), None, created_at))
            conn.commit()
            fc_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.close()

            yield f"data: {json.dumps({'final_verdict': final_verdict, 'step': 'complete', 'id': fc_id, 'score': score, 'total': total, 'true': true_c, 'false': false_c, 'partial': partial_c, 'unverifiable': unverifiable_c, 'conflict': conflict_c, 'claims': verified, 'ai_detection': ai_result, 'lang': detected_lang, 'lang_name': lang_name})}\n\n"

        except Exception as e:
            print(f"Stream error: {e}")
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Access-Control-Allow-Origin': '*'}
    )


@app.route('/api/factchecks', methods=['GET'])
def get_factchecks():
    conn   = get_db()
    rows   = conn.execute('SELECT * FROM fact_checks ORDER BY id DESC LIMIT 50').fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['claims'] = json.loads(d['claims_json']) if d['claims_json'] else []
        except Exception:
            d['claims'] = []
        result.append(d)
    return jsonify(result)


@app.route('/api/factchecks/<int:fid>', methods=['GET'])
def get_factcheck(fid):
    conn = get_db()
    row  = conn.execute('SELECT * FROM fact_checks WHERE id=?', (fid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
    d = dict(row)
    try:
        d['claims'] = json.loads(d['claims_json']) if d['claims_json'] else []
    except Exception:
        d['claims'] = []
    return jsonify(d)


@app.route('/api/factchecks', methods=['DELETE'])
def clear_factchecks():
    conn = get_db()
    conn.execute('DELETE FROM fact_checks')
    conn.commit()
    conn.close()
    return jsonify({'cleared': True})


@app.route('/api/generate-sql', methods=['POST'])
def generate_sql():
    data   = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'error': 'prompt required'}), 400
    sql_prompt = f"""You are a SQL expert. Generate a SQL query for this request.
Dataset: customer_behaviour table with columns:
customer_id, age, gender, city_tier, shopping_preference,
avg_online_spend, avg_store_spend, product_category,
monthly_orders, loyalty_score

Request: "{prompt}"

Return ONLY the SQL query. No explanation, no markdown, no backticks."""
    result = gemini_generate(sql_prompt)
    if not result:
        return jsonify({'error': 'Could not generate SQL'}), 500
    result = re.sub(r'```sql|```', '', result).strip()
    return jsonify({'sql': result, 'prompt': prompt})


@app.route('/api/detect-media', methods=['POST', 'OPTIONS'])
def detect_media():
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        resp.headers['Access-Control-Allow-Origin']  = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400
    img_bytes = file.read()
    img_b64   = __import__('base64').b64encode(img_bytes).decode('utf-8')
    mime_type = file.content_type or 'image/jpeg'
    result = detect_ai_image(img_b64, mime_type, file.filename)
    return jsonify(result)


def detect_with_hive(img_bytes, mime_type):
    try:
        import base64
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        resp = requests.post(
            "https://hivemoderation.com/api/v1/task/sync/ai_generated_image_detection/v2",
            headers={"Authorization": f"Token {HIVE_API_KEY}", "Content-Type": "application/json"},
            json={"image": f"data:{mime_type};base64,{img_b64}"},
            timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            ai_score = 0
            output = []
            try: output = data.get('status', [{}])[0].get('response', {}).get('output', [])
            except: pass
            if not output: output = data.get('output', [])
            if not output: output = data.get('classes', [])
            for item in output:
                if isinstance(item, dict):
                    cls   = str(item.get('class', item.get('name', ''))).lower()
                    score = float(item.get('score', item.get('confidence', 0)))
                    if any(w in cls for w in ['ai_gen', 'ai-gen', 'artificial', 'synthetic', 'generated']):
                        ai_score = max(ai_score, score)
                    elif any(w in cls for w in ['not_ai', 'human', 'real', 'authentic']):
                        ai_score = min(ai_score, 1 - score)
            if ai_score == 0:
                ai_score = float(data.get('ai_probability', data.get('score', 0.5)))
            ai_probability = int(ai_score * 100) if ai_score <= 1 else int(ai_score)
            return ai_probability, True
        return None, False
    except Exception as e:
        print(f"[Hive API] Exception: {e}")
        return None, False


def detect_ai_image(img_b64, mime_type, filename):
    import base64 as _b64, io, math
    scores = {}
    indicators = []
    img_bytes = _b64.b64decode(img_b64)

    try:
        hive_prob, hive_ok = detect_with_hive(img_bytes, mime_type)
        if hive_ok and hive_prob is not None:
            scores['hive'] = hive_prob
            indicators.append(f"Hive AI: {hive_prob}% {'AI-generated' if hive_prob >= 80 else 'possible AI' if hive_prob >= 50 else 'likely human'}")
        else:
            scores['hive'] = None
    except Exception as e:
        scores['hive'] = None

    try:
        meta_score = 50
        meta_notes = []
        fname_lower = filename.lower()
        ai_name_patterns = ['midjourney','stable-diffusion','dalle','dall-e','generated','ai-image','synthetic','deepfake','thispersondoesnotexist','artbreeder','nightcafe','runway','leonardo','firefly','bing-image','file_0000000','image_fx','gemini_generated','chatgpt','gpt-image','sora']
        for pattern in ai_name_patterns:
            if pattern in fname_lower:
                meta_score += 35
                meta_notes.append(f"AI tool pattern in filename: {pattern}")
                break
        try:
            from PIL import Image as _PILImg
            from PIL.ExifTags import TAGS as _TAGS
            _img_check = _PILImg.open(io.BytesIO(img_bytes))
            exif_data = _img_check._getexif() if hasattr(_img_check, '_getexif') else None
            if not exif_data:
                is_social = any(p in fname_lower for p in ['whatsapp','telegram','instagram','facebook','messenger','signal','twitter','snapchat'])
                if is_social: meta_score += 5; meta_notes.append("Social app photo (EXIF stripped normally)")
                else: meta_score += 30; meta_notes.append("No EXIF metadata — AI indicator")
            else:
                meta_score -= 15
                exif_decoded = {_TAGS.get(k, k): v for k, v in exif_data.items()}
                make  = str(exif_decoded.get('Make', '')).lower()
                model = str(exif_decoded.get('Model', '')).lower()
                real_cams = ['canon','nikon','sony','samsung','apple','iphone','huawei','xiaomi','oneplus','google','oppo','vivo','motorola']
                if any(cam in make+model for cam in real_cams):
                    meta_score -= 25; meta_notes.append(f"Real camera: {make.title()} {model.title()}")
                software = str(exif_decoded.get('Software', '')).lower()
                if any(s in software for s in ['stable diffusion','midjourney','dall','firefly','runway','sora']):
                    meta_score += 45; meta_notes.append(f"AI software in EXIF: {software[:40]}")
        except Exception:
            pass
        scores['metadata'] = min(100, max(0, meta_score))
        indicators.extend(meta_notes[:3])
    except Exception as e:
        scores['metadata'] = 50

    try:
        from PIL import Image, ImageFilter
        import numpy as np
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        img_resized = img.resize((256, 256))
        arr = np.array(img_resized, dtype=np.float32)
        pixel_score = 50
        pixel_notes = []
        unique_colors = len(set(map(tuple, arr.reshape(-1,3).astype(int).tolist())))
        color_ratio = unique_colors / (256 * 256)
        if color_ratio < 0.15: pixel_score += 30; pixel_notes.append(f"Low color diversity ({color_ratio:.2f})")
        elif color_ratio > 0.4: pixel_score -= 25; pixel_notes.append(f"Rich color diversity ({color_ratio:.2f}) — natural photo")
        r_std = float(np.std(arr[:,:,0])); g_std = float(np.std(arr[:,:,1])); b_std = float(np.std(arr[:,:,2]))
        avg_std = (r_std + g_std + b_std) / 3
        if avg_std < 35: pixel_score += 25; pixel_notes.append(f"Low color variance ({avg_std:.1f}) — AI characteristic")
        elif avg_std > 65: pixel_score -= 15; pixel_notes.append(f"High natural variance ({avg_std:.1f})")
        gray = np.mean(arr, axis=2)
        gray_img = Image.fromarray(gray.astype(np.uint8))
        laplacian = gray_img.filter(ImageFilter.FIND_EDGES)
        noise_level = float(np.std(np.array(laplacian, dtype=np.float32)))
        if noise_level < 15: pixel_score += 20; pixel_notes.append(f"Very smooth texture ({noise_level:.1f})")
        elif noise_level > 35: pixel_score -= 20; pixel_notes.append(f"Natural noise ({noise_level:.1f})")
        left_half  = arr[:, :128, :]; right_half = np.fliplr(arr[:, 128:, :])
        min_h = min(left_half.shape[0], right_half.shape[0]); min_w = min(left_half.shape[1], right_half.shape[1])
        symmetry_diff = float(np.mean(np.abs(left_half[:min_h,:min_w,:] - right_half[:min_h,:min_w,:])))
        if symmetry_diff < 18: pixel_score += 20; pixel_notes.append(f"High symmetry ({symmetry_diff:.1f}) — AI faces")
        elif symmetry_diff > 40: pixel_score -= 10
        scores['pixel'] = min(100, max(0, pixel_score))
        indicators.extend([n for n in pixel_notes[:2] if n not in indicators])
    except ImportError:
        scores['pixel'] = 50
    except Exception as e:
        scores['pixel'] = 50

    try:
        groq_score = 50
        context_prompt = f"""An image file named "{filename}" ({mime_type}, size: {len(img_bytes)} bytes) was analyzed.
Pixel score: {scores.get('pixel', 50)}/100 | Metadata score: {scores.get('metadata', 50)}/100
Indicators: {indicators}
Estimate AI probability (0-100).
Return ONLY JSON: {{"ai_probability":<0-100>,"reasoning":"<1 sentence>"}}"""
        groq_result = gemini_generate(context_prompt)
        if groq_result:
            groq_result = re.sub(r'```json|```', '', groq_result).strip()
            jm = re.search(r'\{.*\}', groq_result, re.DOTALL)
            if jm:
                gd = json.loads(jm.group(0))
                groq_score = int(gd.get('ai_probability', 50))
                if gd.get('reasoning'): indicators.append(gd['reasoning'][:80])
        scores['groq'] = min(100, max(0, groq_score))
    except Exception as e:
        scores['groq'] = 50

    pixel_w = scores.get('pixel', 50); metadata_w = scores.get('metadata', 50); groq_w = scores.get('groq', 50); hive_w = scores.get('hive')
    if hive_w is not None:
        final_score = int(0.50 * hive_w + 0.25 * pixel_w + 0.15 * metadata_w + 0.10 * groq_w)
    else:
        final_score = int(0.40 * pixel_w + 0.35 * metadata_w + 0.25 * groq_w)
        if mime_type == 'image/png' and metadata_w >= 70: final_score = min(100, final_score + 15)
        if pixel_w > 55 and metadata_w > 55 and groq_w > 55: final_score = min(100, final_score + 10)

    if final_score >= 75:   verdict = 'AI-GENERATED';  manipulation = 'HEAVY';    explanation = f"High AI probability ({final_score}%) detected."
    elif final_score >= 60: verdict = 'DEEPFAKE';      manipulation = 'MODERATE'; explanation = f"Significant manipulation ({final_score}%) detected."
    elif final_score >= 45: verdict = 'UNCERTAIN';     manipulation = 'MINOR';    explanation = f"Mixed signals ({final_score}%). Manual review recommended."
    else:                   verdict = 'HUMAN-CREATED'; manipulation = 'NONE';     explanation = f"Low AI probability ({final_score}%). Looks like a real photo."

    deepfake_score = max(0, final_score - 10) if verdict == 'DEEPFAKE' else int(final_score * 0.6)
    return {'verdict': verdict, 'ai_probability': final_score, 'deepfake_score': deepfake_score, 'manipulation': manipulation, 'explanation': explanation, 'indicators': indicators[:4], 'confidence': min(85, final_score + 10), 'filename': filename, 'scores': {'pixel_forensics': pixel_w, 'metadata': metadata_w, 'context_ai': groq_w}}


@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')


@app.route('/sw.js')
def service_worker():
    resp = send_from_directory('.', 'sw.js')
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/')
def index():
    if not os.path.exists(os.path.join(STATIC_DIR, 'index.html')):
        return "<h2>⚠️ index.html not found in static/</h2>", 404
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    init_db()
    print('\n🚀 Analytica + Fact Checker running at http://localhost:5000')
    print(f'🌍 Translation: {"✅" if TRANSLATION_AVAILABLE else "❌"}')
    print(f'🤖 AI:          {"✅" if GEMINI_AVAILABLE else "❌"}')
    print(f'🔍 Search:      {"✅" if SEARCH_AVAILABLE else "❌"}')
    print(f'🌐 URL Fetch:   {"✅" if URL_FETCH_AVAILABLE else "❌"}\n')
    app.run(debug=True, port=5000, threaded=True)