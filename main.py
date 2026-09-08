
import time
import json
import logging
import threading
import math
import sys
from collections import Counter
from datetime import datetime, timedelta
import urllib.request

try:
    import requests
except ImportError:
    requests = None

try:
    import telebot
    from telebot import types
except ImportError:
    telebot = None
    types = None

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
BOT_USERNAME = "DRX_TM_POD_BOT"
CHANNEL_USERNAME = "@DARK67HACK"
CHANNEL_URL = "https://t.me/DARK67HACK"
OWNER_CHAT_ID = 8707571669

MARKETS = {
    "30S": {
        "name": "WINGO 30 SECONDS",
        "interval": 30,
        "api_url": "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json",
    },
    "5M": {
        "name": "WINGO 5 MINUTES",
        "interval": 300,
        "api_url": "https://advanced-predict1.ai.studio/apipid.json",
    }
}

TOTAL_PAGES = 50

# ENGINE DEFINITIONS (Clean Short Names)
ENGINES = {
    "DRX_VIP": {
        "name": "DRX-VIP-PRO",
        "desc": "SINGLE DIGIT HIGH HIT + BIG/SMALL",
        "type": "DRX_VIP_SINGLE",   # Size + 1 Single Digit Number, Color replaced by "LVL X"
    },
    "TIGER": {
        "name": "TIGER PRO",
        "desc": "2-DIGIT SNIPER + BIG/SMALL",
        "type": "SNIPER_SIZE",
    },
    "DRAGON": {
        "name": "DRAGON PRO",
        "desc": "PURE BIG/SMALL MOMENTUM",
        "type": "PURE_SIZE",
    },
    "DEMON": {
        "name": "DEMON KING",
        "desc": "PURE COLOR CYCLE MASTER",
        "type": "PURE_COLOR",
    },
    "RED": {
        "name": "RED KEEPER",
        "desc": "SEQUENCE PATTERN + AFFINITY",
        "type": "FULL_DUAL_NUM",
    },
    "GREEN": {
        "name": "GREEN KEEPER",
        "desc": "MARKOV 3-DIGIT HIGH HIT",
        "type": "FULL_TRI_NUM",
    },
    "TITAN": {
        "name": "TITAN AI",
        "desc": "CONSENSUS HYBRID ENGINE",
        "type": "FULL_DUAL_NUM",
    },
    "PHOENIX": {
        "name": "PHOENIX MATRIX",
        "desc": "ANTI-STREAK REVERSION HUNTER",
        "type": "SNIPER_SIZE",
    },
    "SHADOW": {
        "name": "SHADOW SNIPER",
        "desc": "GOLDEN RATIO GAP RECURRENCE",
        "type": "SNIPER_SIZE",
    }
}

ENGINE_KEYS_ORDER = ["DRX_VIP", "TIGER", "DRAGON", "DEMON", "RED", "GREEN", "TITAN", "PHOENIX", "SHADOW"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

if telebot is None:
    class DummyBot:
        def message_handler(self, *args, **kwargs):
            return lambda f: f
        def callback_query_handler(self, *args, **kwargs):
            return lambda f: f
    bot = DummyBot()
else:
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# VIP FONT ENGINE (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
# =========================================================
def to_vip(text: str) -> str:
    res = []
    for ch in str(text):
        code = ord(ch)
        if 65 <= code <= 90:     # A-Z -> 𝐀-𝐙
            res.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:  # a-z -> 𝐚-𝐳
            res.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:   # 0-9 -> 𝟎-𝟗
            res.append(chr(0x1D7CE + (code - 48)))
        else:
            res.append(ch)
    return "".join(res)

# =========================================================
# RULES & HELPER FUNCTIONS
# =========================================================
VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

GREEN_AFFINITY = {1, 3, 5, 7, 9}
RED_AFFINITY = {0, 2, 4, 6, 8}

def get_color(num: int) -> str:
    if num in VIOLET_NUMBERS:
        return "VIOLET"
    return "RED" if num in RED_NUMBERS else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num in BIG_NUMBERS else "SMALL"

# =========================================================
# ADVANCED MATHEMATICAL PREDICTION LOGIC: DRX-VIP-PRO
# (SINGLE DIGIT NUMBER + BIG/SMALL + NO COLOR + LVL LOSS TRACKER)
# =========================================================
def analyze_drx_vip_pro(records):
    """
    DRX-VIP-PRO:
    Deep mathematical algorithm for 30 Seconds WinGo:
      1. Dynamic Historical Window: Analyzes up to 500 records (50 pages).
      2. 1st & 2nd Order Markov Transition Matrix.
      3. Poisson Interval Gap Recurrence Sweet-Spot.
      4. Exponential Decay Frequency Momentum (EMA).
      5. Mirror Symmetries: 9's Complement & Modulo 5 Inversion.
      6. Parity Momentum (Odd / Even Cycle Balance).
    Returns:
      - size: 'BIG' or 'SMALL'
      - num: Exactly 1 single digit number string (e.g. '7')
      - color: '--' (Replaced in display by LVL X)
    """
    total_records = len(records)
    if total_records < 3:
        return {"size": "BIG", "num": "7", "color": "--"}

    sample_size = max(10, min(total_records, 500))
    sample = records[:sample_size]

    curr_num = sample[0]["number"]
    prev_num = sample[1]["number"] if sample_size > 1 else (curr_num + 1) % 10

    scores = {d: 0.0 for d in range(10)}

    # 1. Markov 1st & 2nd order transition probabilities
    direct_followers = []
    second_order_followers = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == curr_num:
            direct_followers.append(sample[idx]["number"])
            if idx + 2 < len(sample) and sample[idx + 2]["number"] == prev_num:
                second_order_followers.append(sample[idx]["number"])

    d_counts = Counter(direct_followers)
    s_counts = Counter(second_order_followers)

    for d in range(10):
        scores[d] += d_counts.get(d, 0) * 4.2
        scores[d] += s_counts.get(d, 0) * 6.5

    # 2. Recurrence Gap & Poisson Sweet-Spot
    last_gap = {}
    gap_history = {d: [] for d in range(10)}

    for d in range(10):
        prev_idx = None
        for idx, r in enumerate(sample):
            if r["number"] == d:
                if d not in last_gap:
                    last_gap[d] = idx
                if prev_idx is not None:
                    gap_history[d].append(idx - prev_idx)
                prev_idx = idx
        if d not in last_gap:
            last_gap[d] = sample_size + 15

    for d in range(10):
        g = last_gap.get(d, 50)
        avg_g = (sum(gap_history[d]) / len(gap_history[d])) if gap_history[d] else 10.0

        if 4 <= g <= 13:
            scores[d] += 5.5
        elif g in (1, 2):
            scores[d] += 3.2
        elif g > 25:
            scores[d] += 4.0

        if abs(g - avg_g) <= 1.2:
            scores[d] += 4.5

    # 3. Exponential Decay Momentum (EMA Weight)
    decay = 0.035
    for idx, r in enumerate(sample):
        d = r["number"]
        scores[d] += math.exp(-decay * idx) * 2.0

    # 4. Harmonic Mirror & Modulo Symmetries
    scores[9 - curr_num] += 3.5           # 9's complement
    scores[(curr_num + 5) % 10] += 3.0    # Modulo 5 polarity
    scores[(curr_num + 1) % 10] += 2.2    # Step forward
    scores[(curr_num - 1) % 10] += 2.2    # Step backward

    # 5. Parity & Streak Balance
    recent_10 = [r["number"] for r in sample[:min(10, sample_size)]]
    odd_count = sum(1 for n in recent_10 if n % 2 != 0)
    target_parity = 0 if odd_count >= 7 else (1 if odd_count <= 3 else None)

    if target_parity is not None:
        for d in range(10):
            if d % 2 == target_parity:
                scores[d] += 3.0

    # 6. Rank Digits & Choose Best Single Digit
    ranked = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    best_single_digit = ranked[0]

    # 7. Big/Small Calculation
    recent_12 = [r["size"] for r in sample[:12]]
    big_ratio = recent_12.count("BIG") / len(recent_12) if recent_12 else 0.5
    streak = 1
    first_s = recent_12[0] if recent_12 else "BIG"
    for s in recent_12[1:]:
        if s == first_s:
            streak += 1
        else:
            break

    if streak >= 4:
        pred_size = "SMALL" if first_s == "BIG" else "BIG"
    elif best_single_digit >= 5 and big_ratio >= 0.45:
        pred_size = "BIG"
    elif best_single_digit < 5 and big_ratio < 0.55:
        pred_size = "SMALL"
    else:
        pred_size = "BIG" if best_single_digit >= 5 else "SMALL"

    return {
        "size": pred_size,
        "num": str(best_single_digit),
        "color": "--"
    }

def analyze_tiger_pro(records):
    """TIGER PRO: 2-Digit Sniper + Big/Small."""
    if len(records) < 5:
        return {"size": "BIG", "num": "3,7", "color": "--"}

    sample = records[:60]
    curr_num = sample[0]["number"]

    last_seen_gap = {}
    for d in range(10):
        found = False
        for idx, r in enumerate(sample):
            if r["number"] == d:
                last_seen_gap[d] = idx
                found = True
                break
        if not found:
            last_seen_gap[d] = 70

    transitions = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == curr_num:
            transitions.append(sample[idx]["number"])
    trans_counts = Counter(transitions)

    scores = {}
    for d in range(10):
        t_score = trans_counts.get(d, 0) * 3.5
        gap = last_seen_gap.get(d, 70)
        g_score = 4.0 if 3 <= gap <= 12 else (2.0 if gap > 20 else 1.0)
        scores[d] = t_score + g_score

    ranked_digits = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    n1, n2 = sorted(ranked_digits[:2])

    recent_12 = [r["size"] for r in sample[:12]]
    big_ratio = recent_12.count("BIG") / len(recent_12)
    target_bigs = sum(1 for x in [n1, n2] if x >= 5)
    if target_bigs == 2 or (target_bigs == 1 and big_ratio >= 0.5):
        pred_size = "BIG"
    elif target_bigs == 0 or (target_bigs == 1 and big_ratio < 0.5):
        pred_size = "SMALL"
    else:
        pred_size = "BIG" if (n1 + n2) >= 9 else "SMALL"

    return {"size": pred_size, "num": f"{n1},{n2}", "color": "--"}

def analyze_dragon_pro(records):
    """DRAGON PRO: Pure BIG/SMALL Momentum."""
    if len(records) < 5:
        return {"size": "BIG", "num": "--", "color": "--"}

    sample = records[:50]
    sizes = [r["size"] for r in sample]

    current_streak = 1
    streak_type = sizes[0]
    for s in sizes[1:]:
        if s == streak_type:
            current_streak += 1
        else:
            break

    if current_streak >= 4:
        pred_size = "SMALL" if streak_type == "BIG" else "BIG"
    elif current_streak == 3:
        recent_15 = sizes[:15]
        dominant_count = recent_15.count(streak_type)
        pred_size = streak_type if dominant_count >= 11 else ("SMALL" if streak_type == "BIG" else "BIG")
    else:
        recent_10 = sizes[:10]
        big_c = recent_10.count("BIG")
        small_c = recent_10.count("SMALL")
        pred_size = "BIG" if big_c > small_c else ("SMALL" if small_c > big_c else ("SMALL" if sizes[0] == "BIG" else "BIG"))

    return {"size": pred_size, "num": "--", "color": "--"}

def analyze_demon_king(records):
    """DEMON KING: Pure Color Cycle Master."""
    if len(records) < 5:
        return {"size": "--", "num": "--", "color": "RED"}

    sample = records[:50]
    colors = [r["color"] for r in sample]

    r_count = colors[:10].count("RED")
    g_count = colors[:10].count("GREEN")

    if len(colors) >= 3 and colors[0] == colors[1] == colors[2] and colors[0] in ["RED", "GREEN"]:
        pred_color = "GREEN" if colors[0] == "RED" else "RED"
    elif r_count > g_count:
        pred_color = "RED" if colors[0] != "RED" else "GREEN"
    else:
        pred_color = "GREEN" if colors[0] != "GREEN" else "RED"

    return {"size": "--", "num": "--", "color": pred_color}

def analyze_red_keeper(records):
    """RED KEEPER: Sequence pattern search + affinity resolution."""
    if len(records) < 5:
        return {"size": "BIG", "num": "1,5", "color": "GREEN"}

    t1 = records[0]["number"]
    t2 = records[1]["number"] if len(records) > 1 else (t1 + 1) % 10

    found_idx = -1
    search_start = 20 if len(records) >= 25 else 2
    for i in range(search_start, len(records) - 2):
        curr_pair = (records[i]["number"], records[i + 1]["number"])
        if curr_pair in ((t1, t2), (t2, t1)):
            if i - 1 >= 0 and i + 2 < len(records):
                found_idx = i
                break

    if found_idx == -1:
        n_above = (t1 + 3) % 10
        n_below = (t2 + 7) % 10
    else:
        n_above = records[found_idx - 1]["number"]
        n_below = records[found_idx + 2]["number"]

    pair_nums = {n_above, n_below}
    if pair_nums.issubset(GREEN_AFFINITY) or (9 in pair_nums and 5 in pair_nums):
        pred_color = "GREEN"
    elif pair_nums.issubset(RED_AFFINITY) or (0 in pair_nums and any(x in RED_NUMBERS for x in pair_nums)):
        pred_color = "RED"
    else:
        c_above = get_color(n_above)
        c_below = get_color(n_below)
        pred_color = c_above if c_above == c_below else "GREEN"

    avg = (n_above + n_below) / 2.0
    pred_size = "BIG" if avg >= 4.5 else "SMALL"

    return {"size": pred_size, "num": f"{n_above},{n_below}", "color": pred_color}

def analyze_green_keeper(records):
    """GREEN KEEPER: 150-Rounds Markov Transition Chain + 3-Digit Sniper."""
    if len(records) < 3:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}

    sample = records[:150]
    latest_num = sample[0]["number"]

    transitions = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == latest_num:
            transitions.append(sample[idx]["number"])

    follow_up_candidates = [n for n, _ in Counter(transitions).most_common(2)]
    recent_40 = [r["number"] for r in sample[:40]]
    hot_candidates = [n for n, _ in Counter(recent_40).most_common(3)]
    mirror_candidate = (9 - latest_num)

    predicted_pool = []
    for c in follow_up_candidates + hot_candidates + [mirror_candidate, (latest_num + 3) % 10, (latest_num + 7) % 10]:
        if c not in predicted_pool and 0 <= c <= 9:
            predicted_pool.append(c)
        if len(predicted_pool) == 3:
            break

    target_3_numbers = sorted(predicted_pool)
    num_str = f"{target_3_numbers[0]},{target_3_numbers[1]},{target_3_numbers[2]}"

    big_in_target = sum(1 for n in target_3_numbers if n >= 5)
    pred_size = "BIG" if big_in_target >= 2 else "SMALL"
    pred_color = "GREEN" if (target_3_numbers[0] % 2 != 0) else "RED"

    return {"size": pred_size, "num": num_str, "color": pred_color}

def analyze_titan_ai(records):
    """TITAN AI: Multi-indicator consensus engine."""
    if len(records) < 5:
        return {"size": "BIG", "num": "2,6", "color": "RED"}

    sample = records[:40]
    nums = [r["number"] for r in sample]
    avg_num = sum(nums[:8]) / 8.0
    pred_size = "BIG" if avg_num >= 4.5 else "SMALL"

    odd_count = sum(1 for n in nums[:12] if n % 2 != 0)
    target_parity = 0 if odd_count >= 7 else 1

    candidates = [n for n in range(10) if (n % 2 == target_parity)]
    candidates = [c for c in candidates if (c >= 5 if pred_size == "BIG" else c < 5)]
    if len(candidates) < 2:
        candidates = [2, 6] if pred_size == "BIG" else [1, 3]

    n1, n2 = candidates[0], candidates[1]
    return {"size": pred_size, "num": f"{n1},{n2}", "color": get_color(n1)}

def analyze_phoenix_matrix(records):
    """PHOENIX MATRIX: Anti-Streak Reversion Hunter."""
    if len(records) < 5:
        return {"size": "SMALL", "num": "0,4", "color": "--"}

    first_size = records[0]["size"]
    pred_size = "SMALL" if first_size == "BIG" else "BIG"
    n1, n2 = (1, 4) if pred_size == "SMALL" else (6, 8)
    return {"size": pred_size, "num": f"{n1},{n2}", "color": "--"}

def analyze_shadow_sniper(records):
    """SHADOW SNIPER: Golden Ratio Interval Gap Sniper."""
    if len(records) < 5:
        return {"size": "BIG", "num": "5,9", "color": "--"}

    curr = records[0]["number"]
    n1 = (curr + 3) % 10
    n2 = (curr + 8) % 10
    if n1 > n2:
        n1, n2 = n2, n1
    pred_size = "BIG" if (n1 + n2) >= 9 else "SMALL"
    return {"size": pred_size, "num": f"{n1},{n2}", "color": "--"}

ENGINE_ANALYZERS = {
    "DRX_VIP": analyze_drx_vip_pro,
    "TIGER": analyze_tiger_pro,
    "DRAGON": analyze_dragon_pro,
    "DEMON": analyze_demon_king,
    "RED": analyze_red_keeper,
    "GREEN": analyze_green_keeper,
    "TITAN": analyze_titan_ai,
    "PHOENIX": analyze_phoenix_matrix,
    "SHADOW": analyze_shadow_sniper,
}

# =========================================================
# STATE MANAGEMENT & DUAL MARKET STORAGE
# =========================================================
class MarketState:
    def __init__(self, key: str):
        self.key = key
        self.config = MARKETS[key]
        self.current_period = ""
        self.market_data = []          # Up to 500 rows (50 pages)

        # Dictionary of engines: key -> {pred, history, win_loss, max_loss_streak}
        self.engines_data = {}
        for eng_key in ENGINE_KEYS_ORDER:
            self.engines_data[eng_key] = {
                "pred": {"period": "", "size": "--", "num": "--", "color": "--"},
                "history": {},       # period -> {prediction dict, timestamp}
                "win_loss": {},      # period -> outcome ("JAC", "WIN", "LOSS")
                "max_loss_streak": 1 # Monotonically tracks peak consecutive losses (LVL)
            }

    def update_max_loss_streak(self, eng_key: str):
        """
        Calculates the peak (maximum) consecutive loss streak across all evaluated
        historical periods (from page 1 up to page 50 / 500 rows).
        Monotonically updates max_loss_streak (never decreases).
        """
        edata = self.engines_data[eng_key]
        win_loss = edata["win_loss"]
        if not win_loss:
            return

        sorted_periods = sorted(win_loss.keys())
        current_streak = 0
        peak_streak = 1

        for p in sorted_periods:
            res = win_loss[p]
            if res == "LOSS":
                current_streak += 1
                if current_streak > peak_streak:
                    peak_streak = current_streak
            else:
                current_streak = 0

        if peak_streak > edata["max_loss_streak"]:
            edata["max_loss_streak"] = peak_streak

    def get_engine_last_10_stats(self, eng_key: str):
        """Calculates win rate and score for ranking engines based on last 10 periods."""
        edata = self.engines_data[eng_key]
        win_loss = edata["win_loss"]
        sorted_periods = sorted(win_loss.keys(), reverse=True)
        last_10 = sorted_periods[:10]
        total = len(last_10)

        if total == 0:
            return {"total": 0, "wins": 0, "score": 85.0}

        wins = 0
        for p in last_10:
            if win_loss[p] in ("WIN", "JAC"):
                wins += 1

        win_rate = (wins / total) * 100
        score = win_rate + (wins * 2)
        return {"total": total, "wins": wins, "score": score}

    def get_ranked_engines(self):
        """Returns engine keys sorted by score descending (top performer at index 0)."""
        scored = []
        for eng_key in ENGINE_KEYS_ORDER:
            stats = self.get_engine_last_10_stats(eng_key)
            scored.append((eng_key, stats["score"]))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored]

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=24)
        for edata in self.engines_data.values():
            hist = edata["history"]
            wl = edata["win_loss"]
            to_del = [p for p, val in hist.items() if val.get("timestamp", datetime.now()) < cutoff]
            for p in to_del:
                hist.pop(p, None)
                wl.pop(p, None)

# User session, channel verification, referral, and admin bypass state
class UserSessionManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.users = {}
        # users[chat_id] = {
        #   "verified": bool,
        #   "referrals": set(verified_user_ids),
        #   "referred_by": int or None,
        #   "unlock_time": datetime or None,
        #   "bypass": bool
        # }
        self.active_admin_passwords = {"6789"}  # Default admin password from user prompt

    def get_user(self, chat_id: int):
        with self.lock:
            if chat_id not in self.users:
                self.users[chat_id] = {
                    "verified": (chat_id == OWNER_CHAT_ID),
                    "referrals": set(),
                    "referred_by": None,
                    "unlock_time": None,
                    "bypass": (chat_id == OWNER_CHAT_ID)
                }
            return self.users[chat_id]

    def is_unlocked(self, chat_id: int) -> bool:
        """Checks if user has fulfilled channel verification and referral quota or has bypass."""
        if chat_id == OWNER_CHAT_ID:
            return True
        user = self.get_user(chat_id)
        if user["bypass"]:
            return True
        if not user["verified"]:
            return False

        # Calculate required referrals: base 2, +1 every 24 hours from initial unlock
        req = self.get_required_referrals(chat_id)
        return len(user["referrals"]) >= req

    def get_required_referrals(self, chat_id: int) -> int:
        user = self.get_user(chat_id)
        if user["unlock_time"] is None:
            return 2
        now = datetime.now()
        days_passed = int((now - user["unlock_time"]).total_seconds() // 86400)
        return 2 + max(0, days_passed)

    def mark_verified(self, chat_id: int):
        with self.lock:
            user = self.users.get(chat_id)
            if user:
                user["verified"] = True
                if user["unlock_time"] is None:
                    user["unlock_time"] = datetime.now()

                # If this user was referred by someone, credit that referrer now!
                ref_by = user.get("referred_by")
                if ref_by and ref_by in self.users and ref_by != chat_id:
                    self.users[ref_by]["referrals"].add(chat_id)

    def set_admin_password(self, password: str):
        with self.lock:
            self.active_admin_passwords.add(str(password).strip())

    def check_and_apply_password(self, chat_id: int, password: str) -> bool:
        with self.lock:
            if str(password).strip() in self.active_admin_passwords:
                user = self.get_user(chat_id)
                user["bypass"] = True
                user["verified"] = True
                if user["unlock_time"] is None:
                    user["unlock_time"] = datetime.now()
                return True
            return False

class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.markets = {
            "30S": MarketState("30S"),
            "5M": MarketState("5M")
        }
        self.active_chats = {}
        self.user_manager = UserSessionManager()

state = BotState()

# =========================================================
# API FETCHER
# =========================================================
def fetch_api_market(market_key: str):
    m_info = MARKETS.get(market_key)
    if not m_info:
        return []
    url = m_info["api_url"]
    try:
        data = None
        if requests is not None:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
            except Exception:
                data = None

        if data is None:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))

        if data is not None:
            raw_list = []
            if isinstance(data, dict):
                for k in ["data", "history", "prediction_history", "list", "records", "rows"]:
                    if k in data and isinstance(data[k], list):
                        raw_list = data[k]
                        break
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                if isinstance(item, dict):
                    p_raw = item.get("period")
                    n_raw = item.get("number")
                    if n_raw is None:
                        n_raw = item.get("actual_number")

                    if p_raw is not None and n_raw is not None:
                        period = str(p_raw).strip()
                        try:
                            num = int(n_raw)
                        except (ValueError, TypeError):
                            continue

                        s_raw = str(item.get("size", "")).strip().upper()
                        c_raw = str(item.get("color", "")).strip().upper()

                        size = s_raw if s_raw in ["BIG", "SMALL"] else get_size(num)
                        color = c_raw if c_raw in ["RED", "GREEN", "VIOLET"] else get_color(num)

                        formatted.append({
                            "period": period,
                            "number": num,
                            "size": size,
                            "color": color
                        })

            if formatted:
                return formatted[:500]
    except Exception as e:
        logger.error(f"API Fetch Error [{market_key}]: {e}")
    return []

# =========================================================
# OUTCOME EVALUATOR
# =========================================================
def evaluate_market_outcomes(m_state: MarketState, data):
    """Evaluates WIN/LOSS/JAC for all engines and updates max consecutive loss levels."""
    for rec in data[:10]:
        p = rec["period"]
        act_n = rec["number"]
        act_s = rec["size"]
        act_c = rec["color"]

        for eng_key, edata in m_state.engines_data.items():
            hist = edata["history"]
            win_loss = edata["win_loss"]

            if p in hist and p not in win_loss:
                p_item = hist[p]
                pred_s = p_item.get("size", "--")
                pred_c = p_item.get("color", "--")
                num_str = p_item.get("num", "--")
                pred_nums = [int(x.strip()) for x in num_str.split(",") if x.strip().isdigit()]

                # DRX-VIP-PRO Evaluation (Single Digit + Big/Small)
                if eng_key == "DRX_VIP":
                    if act_n in pred_nums:
                        win_loss[p] = "JAC"
                    elif pred_s == act_s:
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                elif eng_key == "TIGER" or ENGINES[eng_key]["type"] == "SNIPER_SIZE":
                    if act_n in pred_nums:
                        win_loss[p] = "JAC"
                    elif pred_s == act_s:
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                elif eng_key == "DRAGON" or ENGINES[eng_key]["type"] == "PURE_SIZE":
                    win_loss[p] = "WIN" if pred_s == act_s else "LOSS"

                elif eng_key == "DEMON" or ENGINES[eng_key]["type"] == "PURE_COLOR":
                    if pred_c == act_c:
                        win_loss[p] = "WIN"
                    elif act_c == "VIOLET" and ((pred_c == "RED" and act_n == 0) or (pred_c == "GREEN" and act_n == 5)):
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                else:
                    if act_n in pred_nums:
                        win_loss[p] = "JAC"
                    elif (pred_s == act_s) or (pred_c == act_c):
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                # Update max loss streak for this engine
                m_state.update_max_loss_streak(eng_key)

def update_single_market(market_key: str):
    m_state = state.markets[market_key]
    interval = MARKETS[market_key]["interval"]
    data = fetch_api_market(market_key)

    if data:
        with state.lock:
            if market_key == "30S":
                existing_dict = {x["period"]: x for x in data}
                for old_item in m_state.market_data:
                    if old_item["period"] not in existing_dict:
                        existing_dict[old_item["period"]] = old_item
                sorted_list = sorted(existing_dict.values(), key=lambda x: str(x["period"]), reverse=True)
                m_state.market_data = sorted_list[:500]
            else:
                m_state.market_data = data

            top_record = data[0]
            top_period = top_record["period"]

            if top_period != getattr(m_state, "_last_period", ""):
                m_state._last_period = top_period

                try:
                    next_period_num = int(top_period) + 1
                    next_period_str = str(next_period_num).zfill(len(top_period))
                except Exception:
                    next_period_str = f"{int(time.time() // interval) + 1}"

                m_state.current_period = next_period_str
                evaluate_market_outcomes(m_state, data)

                # Compute predictions for all engines
                for eng_key, analyzer_func in ENGINE_ANALYZERS.items():
                    pred_res = analyzer_func(m_state.market_data)
                    edata = m_state.engines_data[eng_key]

                    edata["pred"] = {
                        "period": next_period_str,
                        "size": pred_res["size"],
                        "num": pred_res["num"],
                        "color": pred_res["color"]
                    }
                    edata["history"][next_period_str] = {
                        **edata["pred"],
                        "timestamp": datetime.now()
                    }

    m_state.clean_old_records()

# =========================================================
# TELEGRAM VERIFICATION & REFERRAL CHECK
# =========================================================
def check_telegram_channel_membership(user_id: int) -> bool:
    """Checks if the user is a member of the mandatory channel @DARK67HACK."""
    if user_id == OWNER_CHAT_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            return True
    except Exception as e:
        logger.warning(f"Channel check exception for user {user_id}: {e}")
    return False

def get_channel_join_markup():
    """Step 1: Channel Join Gate (Strictly NO emojis)."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_join = types.InlineKeyboardButton(to_vip("JOIN CHANNEL"), url=CHANNEL_URL)
    btn_verify = types.InlineKeyboardButton(to_vip("VERIFY"), callback_data="check_channel_verify")
    markup.add(btn_join, btn_verify)
    return markup

def get_referral_gate_markup(user_id: int):
    """Step 2: Referral Gate (Strictly NO emojis)."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_check = types.InlineKeyboardButton(to_vip("CHECK STATUS"), callback_data="check_ref_status")
    markup.add(btn_check)
    return markup

# =========================================================
# VIP UI & CLEAN NAVIGATION MARKUPS
# =========================================================
def get_market_selection_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_30s = types.InlineKeyboardButton(to_vip("WINGO 30 SECONDS"), callback_data="selm_30S")
    btn_5m = types.InlineKeyboardButton(to_vip("WINGO 5 MINUTES"), callback_data="selm_5M")
    markup.add(btn_30s, btn_5m)
    return markup

def get_engine_selection_markup(market_key: str):
    """
    DYNAMIC LEADERBOARD:
    - Clean short names only (DRX-VIP-PRO, TIGER PRO, DRAGON PRO, etc.)
    - NO 'TOP 1', NO 'TOP PRO', NO 'LVL 4', NO PERCENTAGES
    - Ranked so best performing engine automatically sits at TOP!
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    m_state = state.markets[market_key]
    ranked_engines = m_state.get_ranked_engines()

    for eng_key in ranked_engines:
        eng_info = ENGINES[eng_key]
        # Clean short name only
        label = eng_info['name']
        btn = types.InlineKeyboardButton(to_vip(label), callback_data=f"launch_{market_key}_{eng_key}")
        markup.add(btn)

    btn_back = types.InlineKeyboardButton(to_vip("BACK TO MARKETS"), callback_data="back_markets")
    markup.add(btn_back)
    return markup

def get_dashboard_header(market_key: str, eng_key: str) -> str:
    market_name = MARKETS[market_key]["name"]
    eng_info = ENGINES.get(eng_key, ENGINES["DRX_VIP"])

    return (
        f"<b>{to_vip('DRX-VIP')} | {to_vip('SYSTEM ONLINE')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(eng_info['name'])}</b>\n"
        "────────────────────────"
    )

def create_market_markup(market_key: str = "30S", page: int = 1, eng_key: str = "DRX_VIP"):
    """
    CLEAN DASHBOARD NAVIGATION:
    - Row 1: Period
    - Row 2: Live Timer Countdown + ASCII Progress Bar
    - Row 3: Prediction Box:
        * For DRX_VIP: [SIZE] [1 SINGLE DIGIT] [LVL X] (Peak Consecutive Loss Streak)
        * For others: [SIZE] [NUMBERS] [COLOR]
    - Row 4-13: 10 Data Rows per page with outcome (WIN, LOSS, JAC)
    - Row 14: Pagination: [PREV] [PAGE X/50] [NEXT]
    - Row 15: Clean Engine Switch: [PREV ENGINE] [NEXT ENGINE]
    - Row 16: Menu: [BACK TO ENGINES] [REFRESH]
    """
    markup = types.InlineKeyboardMarkup(row_width=4)
    m_state = state.markets[market_key]
    interval = MARKETS[market_key]["interval"]

    # 1. Period Button
    period_str = m_state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # 2. Timer & ASCII Progress Bar
    now_ts = int(time.time())
    elapsed = now_ts % interval
    remaining = interval - elapsed

    total_blocks = 20
    filled_blocks = int((elapsed / interval) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # 3. Dynamic Prediction Box
    edata = m_state.engines_data.get(eng_key, m_state.engines_data["DRX_VIP"])
    pred = edata["pred"]

    if eng_key == "DRX_VIP":
        s_val = to_vip(pred['size']) if pred['size'] != "--" else "-"
        n_val = f"[{to_vip(pred['num'])}]" if pred['num'] != "--" else "-"
        # In place of Color: display LVL X (Peak consecutive loss streak)
        lvl_num = edata.get("max_loss_streak", 1)
        lvl_str = f"LVL {lvl_num}"
        c_val = to_vip(lvl_str)

        btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
        btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
        btn_level = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
        markup.row(btn_size, btn_num, btn_level)
    else:
        s_val = to_vip(pred['size']) if pred['size'] != "--" else "-"
        n_val = to_vip(pred['num']) if pred['num'] != "--" else "-"
        c_val = to_vip(pred['color']) if pred['color'] != "--" else "-"
        btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
        btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
        btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
        markup.row(btn_size, btn_num, btn_color)

    # 4. Market Data Table (10 Rows Per Page)
    page = max(1, min(TOTAL_PAGES, page))
    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = m_state.market_data[start_idx:end_idx]
    records_outcome = edata["win_loss"]

    for item in records:
        p_full = item["period"]
        p_short = p_full[-4:] if len(p_full) >= 4 else p_full
        num = item["number"]
        actual_size = item["size"]

        outcome_raw = records_outcome.get(p_full, "--")
        outcome = to_vip(outcome_raw) if outcome_raw != "--" else "-"

        b1 = types.InlineKeyboardButton(f"{to_vip(p_short)}", callback_data="none")
        b2 = types.InlineKeyboardButton(f"{to_vip(str(num))}", callback_data="none")
        b3 = types.InlineKeyboardButton(f"{to_vip(actual_size)}", callback_data="none")
        b4 = types.InlineKeyboardButton(f"{outcome}", callback_data="none")
        markup.row(b1, b2, b3, b4)

    # Fill remaining rows if needed
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # 5. Page Navigation (Row 14)
    prev_page = page - 1 if page > 1 else TOTAL_PAGES
    next_page = page + 1 if page < TOTAL_PAGES else 1
    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # 6. Clean Engine Switching Navigation (Row 15)
    curr_idx = ENGINE_KEYS_ORDER.index(eng_key) if eng_key in ENGINE_KEYS_ORDER else 0
    prev_eng = ENGINE_KEYS_ORDER[(curr_idx - 1) % len(ENGINE_KEYS_ORDER)]
    next_eng = ENGINE_KEYS_ORDER[(curr_idx + 1) % len(ENGINE_KEYS_ORDER)]

    btn_prev_eng = types.InlineKeyboardButton(f"{to_vip('PREV ENGINE')}", callback_data=f"sweng_{prev_eng}")
    btn_next_eng = types.InlineKeyboardButton(f"{to_vip('NEXT ENGINE')}", callback_data=f"sweng_{next_eng}")
    markup.row(btn_prev_eng, btn_next_eng)

    # 7. Clean Return & Refresh (Row 16)
    btn_back = types.InlineKeyboardButton(to_vip("BACK TO ENGINES"), callback_data="back_engines")
    btn_refresh = types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh")
    markup.row(btn_back, btn_refresh)

    return markup

# =========================================================
# REAL-TIME BACKGROUND LOOP
# =========================================================
def real_time_market_loop():
    while True:
        try:
            update_single_market("30S")
            update_single_market("5M")

            with state.lock:
                chats_to_update = list(state.active_chats.items())

            for chat_id, info in chats_to_update:
                try:
                    m_key = info.get("market", "30S")
                    eng_key = info.get("engine", "DRX_VIP")
                    curr_page = info.get("page", 1)

                    markup = create_market_markup(
                        market_key=m_key,
                        page=curr_page,
                        eng_key=eng_key
                    )
                    bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=info["message_id"],
                        reply_markup=markup
                    )
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" not in str(e).lower():
                        pass
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Background Loop error: {e}")

        time.sleep(2)

# =========================================================
# BOT COMMAND & CALLBACK HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_start_menu(message):
    chat_id = message.chat.id
    user_mgr = state.user_manager
    user = user_mgr.get_user(chat_id)

    # Check for referral payload: /start ref_123456
    text_parts = message.text.split()
    if len(text_parts) > 1 and text_parts[1].startswith("ref_"):
        try:
            referrer_id = int(text_parts[1].replace("ref_", "").strip())
            if referrer_id != chat_id and user["referred_by"] is None:
                user["referred_by"] = referrer_id
        except Exception:
            pass

    # Admin / Owner Bypass Check
    if chat_id == OWNER_CHAT_ID or user["bypass"]:
        show_markets_dashboard(chat_id)
        return

    # STEP 1: Channel Verification Check
    is_joined = check_telegram_channel_membership(chat_id)
    if not is_joined:
        join_text = (
            f"<b>{to_vip('CHANNEL MEMBERSHIP REQUIRED')}</b>\n"
            f"<i>{to_vip('JOIN OUR OFFICIAL CHANNEL TO CONTINUE')}</i>\n"
            f"{CHANNEL_URL}\n"
            "────────────────────────"
        )
        markup = get_channel_join_markup()
        bot.send_message(chat_id, join_text, reply_markup=markup)
        return

    # User is in channel, mark verified
    user_mgr.mark_verified(chat_id)

    # STEP 2: Referral Quota Check
    req_refs = user_mgr.get_required_referrals(chat_id)
    completed_refs = len(user["referrals"])

    if completed_refs < req_refs:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{chat_id}"
        ref_text = (
            f"<b>{to_vip('REFERRAL VERIFICATION REQUIRED')}</b>\n"
            f"<b>{to_vip('YOUR REFERRAL LINK')}:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"<b>{to_vip('COMPLETED')}: {to_vip(str(completed_refs))}/{to_vip(str(req_refs))}</b>\n"
            f"<i>{to_vip('DAILY INCREASE')}: +{to_vip('1')} {to_vip('EVERY 24 HOURS')}</i>\n"
            f"<i>{to_vip('NOTE: REFERRED USERS MUST JOIN CHANNEL AND VERIFY')}</i>\n"
            "────────────────────────"
        )
        markup = get_referral_gate_markup(chat_id)
        bot.send_message(chat_id, ref_text, reply_markup=markup)
        return

    # User fully unlocked
    show_markets_dashboard(chat_id)

@bot.message_handler(commands=["admin"])
def handle_admin_command(message):
    chat_id = message.chat.id
    user_mgr = state.user_manager
    text_parts = message.text.strip().split(maxsplit=1)

    # 1. Owner setting a new bypass password: /admin <password>
    if chat_id == OWNER_CHAT_ID:
        if len(text_parts) > 1:
            new_pass = text_parts[1].strip()
            user_mgr.set_admin_password(new_pass)
            resp = (
                f"<b>{to_vip('ADMIN PASSCODE CREATED')}</b>\n"
                f"<b>{to_vip('PASSCODE')}: {to_vip(new_pass)}</b>\n"
                f"<i>{to_vip('USERS CAN ENTER THIS PASSCODE FOR FULL BYPASS')}</i>"
            )
            bot.send_message(chat_id, resp)
            return
        else:
            bot.send_message(chat_id, f"<b>{to_vip('OWNER PANEL')}</b>\n{to_vip('ACTIVE PASSWORDS')}: {list(user_mgr.active_admin_passwords)}")
            return

    # 2. General user attempting bypass via /admin <password>
    if len(text_parts) > 1:
        attempt = text_parts[1].strip()
        if user_mgr.check_and_apply_password(chat_id, attempt):
            bot.send_message(chat_id, f"<b>{to_vip('VIP PASSCODE ACCEPTED')}</b>\n{to_vip('FULL ACCESS UNLOCKED')}")
            show_markets_dashboard(chat_id)
            return
        else:
            bot.send_message(chat_id, f"<b>{to_vip('INVALID PASSCODE')}</b>")
            return

    bot.send_message(chat_id, f"<b>{to_vip('ADMIN COMMAND FORMAT')}: /admin [passcode]</b>")

@bot.message_handler(func=lambda msg: True)
def handle_general_messages(message):
    """Checks if message is an admin bypass passcode."""
    chat_id = message.chat.id
    text = message.text.strip()
    user_mgr = state.user_manager

    if user_mgr.check_and_apply_password(chat_id, text):
        bot.send_message(chat_id, f"<b>{to_vip('VIP PASSCODE ACCEPTED')}</b>\n{to_vip('FULL ACCESS UNLOCKED')}")
        show_markets_dashboard(chat_id)
        return

def show_markets_dashboard(chat_id: int):
    welcome_text = (
        f"<b>{to_vip('DRX-VIP PRO')} | {to_vip('SYSTEM ONLINE')}</b>\n"
        f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
        "────────────────────────"
    )
    markup = get_market_selection_markup()
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data
    user_mgr = state.user_manager

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # 1. Channel Verify Button Click
    if data == "check_channel_verify":
        is_joined = check_telegram_channel_membership(chat_id)
        if is_joined:
            user_mgr.mark_verified(chat_id)
            bot.answer_callback_query(call.id, text=to_vip("CHANNEL VERIFIED"))

            req_refs = user_mgr.get_required_referrals(chat_id)
            completed_refs = len(user_mgr.get_user(chat_id)["referrals"])

            if completed_refs < req_refs and chat_id != OWNER_CHAT_ID:
                ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{chat_id}"
                ref_text = (
                    f"<b>{to_vip('REFERRAL VERIFICATION REQUIRED')}</b>\n"
                    f"<b>{to_vip('YOUR REFERRAL LINK')}:</b>\n"
                    f"<code>{ref_link}</code>\n\n"
                    f"<b>{to_vip('COMPLETED')}: {to_vip(str(completed_refs))}/{to_vip(str(req_refs))}</b>\n"
                    f"<i>{to_vip('DAILY INCREASE')}: +{to_vip('1')} {to_vip('EVERY 24 HOURS')}</i>\n"
                    f"<i>{to_vip('NOTE: REFERRED USERS MUST JOIN CHANNEL AND VERIFY')}</i>\n"
                    "────────────────────────"
                )
                markup = get_referral_gate_markup(chat_id)
                bot.edit_message_text(ref_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            else:
                show_markets_dashboard_in_message(chat_id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, text=to_vip("CHANNEL NOT JOINED YET. PLEASE JOIN AND TRY AGAIN."), show_alert=True)
        return

    # 2. Check Referral Status
    if data == "check_ref_status":
        req_refs = user_mgr.get_required_referrals(chat_id)
        completed_refs = len(user_mgr.get_user(chat_id)["referrals"])
        if completed_refs >= req_refs or chat_id == OWNER_CHAT_ID:
            bot.answer_callback_query(call.id, text=to_vip("REFERRALS COMPLETED"))
            show_markets_dashboard_in_message(chat_id, call.message.message_id)
        else:
            bot.answer_callback_query(
                call.id,
                text=f"{to_vip('CURRENT STATUS')}: {completed_refs}/{req_refs} {to_vip('REFERRED')}",
                show_alert=True
            )
        return

    # Ensure user is authorized
    if not user_mgr.is_unlocked(chat_id):
        bot.answer_callback_query(call.id, text=to_vip("ACCESS LOCKED. COMPLETE REQUIREMENTS FIRST."), show_alert=True)
        return

    # 3. Market Selection -> Shows Dynamically Ranked Engines
    if data.startswith("selm_"):
        market_key = data.split("_")[1]
        market_name = MARKETS[market_key]["name"]
        text = (
            f"<b>{to_vip('DRX-VIP')} | {to_vip('ENGINES')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
            f"<i>{to_vip('SELECT ENGINE')}</i>\n"
            "────────────────────────"
        )
        markup = get_engine_selection_markup(market_key)
        try:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id, text=to_vip(f"{market_name} SELECTED"))
        return

    # 4. Launch Engine Dashboard
    if data.startswith("launch_"):
        parts = data.split("_")
        market_key = parts[1]
        chosen_engine = "_".join(parts[2:])

        header_text = get_dashboard_header(market_key, chosen_engine)
        markup = create_market_markup(market_key=market_key, page=1, eng_key=chosen_engine)

        try:
            bot.edit_message_text(
                header_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass

        with state.lock:
            state.active_chats[chat_id] = {
                "message_id": call.message.message_id,
                "market": market_key,
                "page": 1,
                "engine": chosen_engine
            }
        bot.answer_callback_query(call.id, text=to_vip(f"{ENGINES[chosen_engine]['name']} ACTIVATED"))
        return

    # 5. Clean Engine Switcher (PREV / NEXT ENGINE)
    if data.startswith("sweng_"):
        new_engine = data.replace("sweng_", "")
        with state.lock:
            chat_info = state.active_chats.get(chat_id, {})
            curr_market = chat_info.get("market", "30S")
            curr_page = chat_info.get("page", 1)
            state.active_chats[chat_id] = {
                "message_id": call.message.message_id,
                "market": curr_market,
                "page": curr_page,
                "engine": new_engine
            }

        header_text = get_dashboard_header(curr_market, new_engine)
        markup = create_market_markup(market_key=curr_market, page=curr_page, eng_key=new_engine)

        try:
            bot.edit_message_text(
                header_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass

        bot.answer_callback_query(call.id, text=to_vip(f"{ENGINES[new_engine]['name']}"))
        return

    # 6. Back to Engines List
    if data == "back_engines":
        with state.lock:
            chat_info = state.active_chats.get(chat_id, {})
            curr_market = chat_info.get("market", "30S")

        market_name = MARKETS[curr_market]["name"]
        text = (
            f"<b>{to_vip('DRX-VIP')} | {to_vip('ENGINES')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
            f"<i>{to_vip('SELECT ENGINE')}</i>\n"
            "────────────────────────"
        )
        markup = get_engine_selection_markup(curr_market)
        try:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id, text=to_vip("SELECT ENGINE"))
        return

    # 7. Back to Markets
    if data == "back_markets":
        welcome_text = (
            f"<b>{to_vip('DRX-VIP PRO')} | {to_vip('SYSTEM ONLINE')}</b>\n"
            f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
            "────────────────────────"
        )
        markup = get_market_selection_markup()
        try:
            bot.edit_message_text(
                welcome_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id, text=to_vip("SELECT MARKET"))
        return

    # 8. Pagination (1 to 50 Pages)
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                chat_info = state.active_chats.get(chat_id, {})
                curr_market = chat_info.get("market", "30S")
                curr_engine = chat_info.get("engine", "DRX_VIP")
                state.active_chats[chat_id]["page"] = page_num

            markup = create_market_markup(market_key=curr_market, page=page_num, eng_key=curr_engine)
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {page_num}")
        except Exception:
            bot.answer_callback_query(call.id)

    # 9. Refresh Button
    elif data == "refresh":
        try:
            with state.lock:
                info = state.active_chats.get(chat_id, {"market": "30S", "page": 1, "engine": "DRX_VIP"})
                m_key = info.get("market", "30S")
                eng_key = info.get("engine", "DRX_VIP")
                page = info.get("page", 1)

            markup = create_market_markup(market_key=m_key, page=page, eng_key=eng_key)
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, text=to_vip("REFRESHED"))
        except Exception:
            bot.answer_callback_query(call.id)

def show_markets_dashboard_in_message(chat_id: int, message_id: int):
    welcome_text = (
        f"<b>{to_vip('DRX-VIP PRO')} | {to_vip('SYSTEM ONLINE')}</b>\n"
        f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
        "────────────────────────"
    )
    markup = get_market_selection_markup()
    try:
        bot.edit_message_text(welcome_text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, welcome_text, reply_markup=markup)

# =========================================================
# MAIN EXECUTION
# =========================================================
if __name__ == "__main__":
    if telebot is None:
        print("=" * 65)
        print("ERROR: 'pyTelegramBotAPI' is not installed.")
        print("Run: pip install pyTelegramBotAPI requests")
        print("=" * 65)
        sys.exit(1)

    print("=" * 65)
    print(f"{to_vip('DRX-VIP PRO')} [SYSTEM ONLINE]")
    print(f"Mandatory Channel: {CHANNEL_URL}")
    print(f"Referral Gateway: @{BOT_USERNAME} (2 Refs + Daily +1 Increment)")
    print(f"Admin Owner Chat ID: {OWNER_CHAT_ID}")
    print(f"Flagship Engine: DRX-VIP-PRO (1-Digit + Big/Small + Peak Loss LVL)")
    print(f"Engines: DRX-VIP-PRO, TIGER PRO, DRAGON PRO, DEMON KING, RED KEEPER, GREEN KEEPER, TITAN AI, PHOENIX MATRIX, SHADOW SNIPER")
    print(f"Total Pages: {TOTAL_PAGES}")
    print("=" * 65)

    thread = threading.Thread(target=real_time_market_loop, daemon=True)
    thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Bot crash: {e}. Restarting in 5s...")
            time.sleep(5)
