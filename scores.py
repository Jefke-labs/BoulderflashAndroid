import json
import os
import urllib.request
import urllib.parse
from utils import resource_path

# Leaderboard settings (dreamlo.com)
DREAMLO_PUBLIC_KEY = "6988f7f48f40bb1184d376ed" 
DREAMLO_PRIVATE_KEY = "m6vbCdkuJUGID6iKNnPS8QhV2sfGKFMkKiC6BHW1fZBA" 

# Android-compatible path for scores file
def get_scores_path():
    """Get platform-appropriate path for highscores.json"""
    try:
        # Android: Use app's private storage
        from android.storage import app_storage_path
        return os.path.join(app_storage_path(), "highscores.json")
    except ImportError:
        # Desktop/other: Use current directory
        return "highscores.json"

SCORES_FILE = get_scores_path()

def load_local_scores():
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading local scores: {e}")
    return []

def save_local_score(name, level):
    scores = load_local_scores()
    scores.append({"name": name, "level": level})
    # Sort by level descending
    scores.sort(key=lambda x: x["level"], reverse=True)
    # Increase local capacity to 50
    scores = scores[:50]
    
    try:
        with open(SCORES_FILE, "w") as f:
            json.dump(scores, f, indent=4)
    except Exception as e:
        print(f"Error saving local scores: {e}")

def get_personal_best(name):
    scores = load_local_scores()
    personal_scores = [s["level"] for s in scores if s["name"] == name]
    return max(personal_scores) if personal_scores else 0

def upload_online_score(name, level):
    try:
        # Nettoyage du nom pour l'URL
        safe_name = urllib.parse.quote(name)
        url = f"http://dreamlo.com/lb/{DREAMLO_PRIVATE_KEY}/add/{safe_name}/{level}"
        with urllib.request.urlopen(url, timeout=5) as response:
            res = response.read().decode()
            if "ERROR" in res:
                print(f"Dreamlo Upload Error: {res}")
            return res
    except Exception as e:
        print(f"Connection error while uploading score: {e}")
        return None

def fetch_online_scores():
    try:
        url = f"http://dreamlo.com/lb/{DREAMLO_PUBLIC_KEY}/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            res_raw = response.read().decode()
            if "ERROR" in res_raw:
                print(f"Dreamlo Fetch Error: {res_raw}")
                return []
            data = json.loads(res_raw)
            if "dreamlo" in data and "leaderboard" in data["dreamlo"]:
                lb = data["dreamlo"]["leaderboard"]
                if lb and "entry" in lb:
                    entries = lb["entry"]
                    if isinstance(entries, dict): entries = [entries]
                    return [{"name": e["name"], "level": int(e["score"])} for e in entries]
    except Exception as e:
        print(f"Connection error while fetching scores: {e}")
        return [{"name": "FETCH ERROR", "level": 0, "error": str(e)}]
    return []

def save_score(name, level):
    # 1. Get current personal best BEFORE saving this one
    old_best = get_personal_best(name)
    
    # 2. Sauvegarde locale (all scores go here)
    save_local_score(name, level)
    
    # 3. Upload en ligne ONLY if it's a new personal best
    if level > old_best:
        print(f"New personal best for {name}! Uploading to online leaderboard.")
        upload_online_score(name, level)
    else:
        print(f"Score {level} is not a personal best for {name} (Current best: {old_best}). Local only.")

def get_top_scores(online=True):
    if online:
        return fetch_online_scores()
    else:
        return load_local_scores()

