import json, os, http.server, socketserver, sys, re, unicodedata, http.cookies
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
from verbs_data import VERBS_DB, get_hint

PORT = 8000
HTML_FILE = os.path.join(os.path.dirname(__file__), "index.html")
FLAGGED_FILE = os.path.join(os.path.dirname(__file__), "flagged_phrases.json")

def get_stats_file(headers, path="", body=None):
    cookie_header = headers.get("Cookie", "")
    active_user = "Aline"
    if body and isinstance(body, dict) and "user" in body:
        active_user = body["user"]
    elif "?" in path:
        query_part = path.split("?", 1)[1]
        for pair in query_part.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if k == "user":
                    active_user = v
                    break
    elif cookie_header:
        try:
            cookie = http.cookies.SimpleCookie()
            cookie.load(cookie_header)
            if "active_user" in cookie:
                active_user = cookie["active_user"].value
        except Exception:
            pass
    safe_user = "".join([c for c in active_user if c.isalnum()]).lower()
    if safe_user not in ["aline", "pascal", "camil", "test"]:
        safe_user = "aline"
    return os.path.join(os.path.dirname(__file__), f"stats_apprentissage_{safe_user}.json")

def load_flagged_phrases():
    """Load flagged phrases as dict keyed by context (verb__mode__tense__pronoun).
    Auto-migrates old flat list format to new object format."""
    if os.path.exists(FLAGGED_FILE):
        try:
            with open(FLAGGED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # Migrate old flat array format
                migrated = {"_global": data} if data else {}
                save_flagged_phrases(migrated)
                return migrated
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
    return {}

def save_flagged_phrases(flagged_data):
    """Save flagged phrases object."""
    with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
        json.dump(flagged_data, f, ensure_ascii=False, indent=4)

def get_stats_file(headers, path="", body=None):
    cookie_header = headers.get("Cookie", "")
    active_user = "Aline"
    if body and isinstance(body, dict) and "user" in body:
        active_user = body["user"]
    elif "?" in path:
        query_part = path.split("?", 1)[1]
        for pair in query_part.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if k == "user":
                    active_user = v
                    break
    elif cookie_header:
        try:
            cookie = http.cookies.SimpleCookie()
            cookie.load(cookie_header)
            if "active_user" in cookie:
                active_user = cookie["active_user"].value
        except Exception:
            pass
    safe_user = "".join([c for c in active_user if c.isalnum()]).lower()
    if safe_user not in ["aline", "pascal", "camil", "test"]:
        safe_user = "aline"
    return os.path.join(os.path.dirname(__file__), f"stats_apprentissage_{safe_user}.json")

def build_cards(verb_name):
    """Inject hints into verb data before sending to client."""
    verb = VERBS_DB.get(verb_name, {})
    result = {}
    for mode, tenses in verb.items():
        result[mode] = {}
        for tense, cards in tenses.items():
            enriched = []
            for i, card in enumerate(cards):
                c = dict(card)
                if "hint" not in c:
                    c["hint"] = get_hint(mode, tense, i)
                enriched.append(c)
            result[mode][tense] = enriched
    return result

def sanitize_key(raw_key):
    nfd_normalized = unicodedata.normalize('NFD', raw_key)
    no_accents = "".join([c for c in nfd_normalized if unicodedata.category(c) != 'Mn'])
    no_spaces = re.sub(r'\s+', '-', no_accents)
    return re.sub(r'[^a-zA-Z0-9_\-]', '', no_spaces)

def load_progress(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                return {}
        
        pronouns_map = {
            "0": "yo",
            "1": "tu",
            "2": "elella",
            "3": "nosotros",
            "4": "vosotros",
            "5": "ellosellas"
        }
        
        migrated = {}
        dirty = False
        for k, v in data.items():
            sk = sanitize_key(k)
            
            # Check if key ends with __0, __1, etc.
            parts = sk.split("__")
            if len(parts) >= 2 and parts[-1] in pronouns_map:
                parts[-1] = pronouns_map[parts[-1]]
                sk = "__".join(parts)
                dirty = True
                
            if sk != k:
                dirty = True
            if sk in migrated:
                migrated[sk]["success"] = migrated[sk].get("success", 0) + v.get("success", 0)
                migrated[sk]["error"] = migrated[sk].get("error", 0) + v.get("error", 0)
                migrated[sk]["streak"] = max(migrated[sk].get("streak", 0), v.get("streak", 0))
                if v.get("lastDate"):
                    if not migrated[sk].get("lastDate") or v["lastDate"] > migrated[sk]["lastDate"]:
                        migrated[sk]["lastDate"] = v["lastDate"]
                        migrated[sk]["lastResult"] = v.get("lastResult")
            else:
                migrated[sk] = v
        if dirty:
            save_progress(migrated, file_path)
        return migrated
    return {}

def save_progress(progress, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass  # silence logs

    def do_GET(self):
        if self.path == "/":
            with open(HTML_FILE, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)

        elif self.path.startswith("/api/data"):
            file_path = get_stats_file(self.headers, self.path)
            payload = {
                "verbs": list(VERBS_DB.keys()),
                "progress": load_progress(file_path)
            }
            self._json(payload)

        elif self.path.startswith("/api/verb/"):
            verb = self.path.split("/api/verb/")[1]
            if "?" in verb:
                verb = verb.split("?")[0]
            self._json(build_cards(verb))
        elif self.path == "/conjugaisons.jpg" or self.path.startswith("/conjugaisons.jpg"):
            jpg_file = os.path.join(os.path.dirname(__file__), "conjugaisons.jpg")
            if os.path.exists(jpg_file):
                with open(jpg_file, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", "image/jpeg")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404); self.end_headers()
        elif self.path == "/flag_2.json" or self.path.startswith("/flag_2.json"):
            json_file = os.path.join(os.path.dirname(__file__), "flag_2.json")
            if os.path.exists(json_file):
                with open(json_file, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404); self.end_headers()
        elif self.path == "/flagged_phrases.json" or self.path.startswith("/flagged_phrases.json"):
            flagged_list = load_flagged_phrases()
            self._json(flagged_list)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/vote"):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            file_path = get_stats_file(self.headers, self.path, body)
            progress = load_progress(file_path)
            key = body["id"]
            vote = body["vote"]
            entry = progress.get(key, {"success": 0, "error": 0, "streak": 0, "lastDate": None, "lastResult": None})
            if vote == "reset":
                entry = {"success": 0, "error": 0, "streak": 0, "lastDate": None, "lastResult": None}
            else:
                entry[vote] += 1
                entry["lastDate"] = datetime.now(timezone.utc).isoformat()
                entry["lastResult"] = vote
                if vote == "success":
                    entry["streak"] = entry.get("streak", 0) + 1
                else:
                    entry["streak"] = 0
            progress[key] = entry
            save_progress(progress, file_path)
            self._json(entry)
        elif self.path.startswith("/api/flag"):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            phrase_id = body.get("id")
            context = body.get("context", "_global") or "_global"
            if phrase_id:
                flagged_data = load_flagged_phrases()
                if context not in flagged_data:
                    flagged_data[context] = []
                if phrase_id not in flagged_data[context]:
                    flagged_data[context].append(phrase_id)
                    save_flagged_phrases(flagged_data)
            self._json({"status": "ok"})
        elif self.path.startswith("/api/reset"):
            # read user from optional query parameters
            file_path = get_stats_file(self.headers, self.path)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            self._json({"status": "ok"})
        elif self.path.startswith("/api/reset_day_series"):
            # Reset progress entries for today only
            file_path = get_stats_file(self.headers, self.path)
            progress = load_progress(file_path)
            today_str = datetime.now(timezone.utc).isoformat()[:10]
            
            # Remove all entries from today
            keys_to_remove = [k for k, v in progress.items() if v.get("lastDate", "")[:10] == today_str]
            for k in keys_to_remove:
                del progress[k]
            
            save_progress(progress, file_path)
            self._json({"status": "ok"})

    def _json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[OK] http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Arrêt.")
