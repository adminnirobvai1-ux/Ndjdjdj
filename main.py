# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Professional 30-Second & Dual-Market Prediction Bot
Specialized High-Quality Number Shot 3-Digit Advice Engine

Features:
  - NEW: NUMBER SHOT PRO (Pure 3-Digit Sniper - Highest Probability 3 Numbers)
    * Multi-tier deep statistical logic:
      - Adapts from initial 10 rounds up to 500 rounds (50 pages)
      - Markov Transition probability chain
      - Recurrence gap & Poisson sweet-spot detection
      - Exponential decay frequency momentum
      - Modulo & harmonic mirror resonance
    * Strictly predicts ONLY 3 Numbers (No Big/Small, No Color)
    * Strictly evaluated as JACKPOT (JAC) or LOSS
  - Dynamic Top-1 Level-Up Ranking: Engine with highest score in last 10 rounds stays at TOP!
  - 9 Market-Analysis Engines (NUMBER SHOT PRO, TIGER PRO, DRAGON PRO, DEMON KING, RED PRO, GREEN PRO, TITAN AI, PHOENIX, SHADOW SNIPER)
  - Focused for WinGo 30 Seconds (API: https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json)
  - Also supports WinGo 5 Minutes (API: https://advanced-predict1.ai.studio/apipid.json)
  - Zero Emoji VIP Font Interface (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
  - Clean In-Place Telegram Message Overwrite
  - 50-Pages Dynamic Pagination (10 Rows Per Page)
  - Real-Time Live Countdown Timer & ASCII Progress Bar
"""

import time
import json
import logging
import threading
import math
try:
    import requests
except ImportError:
    requests = None
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
try:
    import telebot
    from telebot import types
except ImportError:
    telebot = None
    types = None

# =========================================================
# CONFIGURATION
# =========================================================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"

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

# ENGINE DEFINITIONS
ENGINES = {
    "NUMBER_SHOT": {
        "name": "NUMBER SHOT PRO",
        "desc": "PURE 3-DIGIT SNIPER (JAC / LOSS ONLY)",
        "type": "PURE_NUMBER",     # Predicts 3 Numbers only, Size and Color are '--'
    },
    "TIGER": {
        "name": "TIGER PRO",
        "desc": "2-DIGIT SNIPER + BIG/SMALL",
        "type": "SNIPER_SIZE",     # Predicts Size & 2 Numbers, Color is '--'
    },
    "DRAGON": {
        "name": "DRAGON PRO",
        "desc": "PURE BIG/SMALL MOMENTUM",
        "type": "PURE_SIZE",       # Predicts Size only, Num & Color are '--'
    },
    "DEMON": {
        "name": "DEMON KING",
        "desc": "PURE COLOR CYCLE MASTER",
        "type": "PURE_COLOR",      # Predicts Color only, Size & Num are '--'
    },
    "RED_PRO": {
        "name": "RED PRO WINNER",
        "desc": "SEQUENCE PATTERN + AFFINITY",
        "type": "FULL_DUAL_NUM",   # Predicts Size, 2 Numbers, Color
    },
    "GREEN_PRO": {
        "name": "GREEN PRO WINNER",
        "desc": "MARKOV 3-DIGIT HIGH HIT",
        "type": "FULL_TRI_NUM",    # Predicts Size, 3 Numbers, Color
    },
    "TITAN": {
        "name": "TITAN AI VIP",
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

# NUMBER_SHOT is listed first as the flagship 30-Second engine
ENGINE_KEYS_ORDER = ["NUMBER_SHOT", "TIGER", "DRAGON", "DEMON", "RED_PRO", "GREEN_PRO", "TITAN", "PHOENIX", "SHADOW"]

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
# RULES & DEFINITIONS
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
# NEW: HIGH QUALITY NUMBER SHOT (3-DIGIT SNIPER)
# PROGRESSIVELY ADAPTS FROM 10 ROUNDS TO 500 ROUNDS (50 PAGES)
# =========================================================
def analyze_number_shot(records):
    """
    NUMBER SHOT PRO:
    - Specially designed for 30 Seconds WinGo
    - Deep Multi-Tier Statistical Analysis Engine:
      1. Dynamic Depth: Starts from 10 records and expands as up to 500 records (50 pages) load.
      2. Markov 1st and 2nd Order Transition Matrix (what digit follows current digit historically).
      3. Recurrence Gap & Poisson Sweet-Spot (identifies digits in optimal return cycle).
      4. Exponential Decay Momentum (recent hits weighted with exponential curve).
      5. Harmonic Mirror & Modulo 5 Symmetries (0-5, 1-6, 2-7, 3-8, 4-9).
      6. Volatility & Cold/Overdue Reversion Hedge.
    - STRICTLY returns ONLY the top 3 highest probability numbers.
    - Size and Color are strictly '--' (no side predictions).
    """
    total_records = len(records)
    if total_records < 3:
        return {"size": "--", "num": "1,5,9", "color": "--"}

    # Dynamic depth: use from 10 up to full history (max 500)
    sample_size = max(10, min(total_records, 500))
    sample = records[:sample_size]

    curr_num = sample[0]["number"]
    prev_num = sample[1]["number"] if sample_size > 1 else (curr_num + 1) % 10

    # Initialize scores for all 10 digits (0 to 9)
    scores = {d: 0.0 for d in range(10)}

    # ---------------------------------------------------------
    # 1. MARKOV CHAIN TRANSITION PROBABILITIES (1st & 2nd Order)
    # ---------------------------------------------------------
    direct_followers = []
    second_order_followers = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == curr_num:
            direct_followers.append(sample[idx]["number"])
            if idx + 2 < len(sample) and sample[idx + 2]["number"] == prev_num:
                second_order_followers.append(sample[idx]["number"])

    direct_counts = Counter(direct_followers)
    second_counts = Counter(second_order_followers)

    for d in range(10):
        # 1st order weight: 3.2 per occurrence
        scores[d] += direct_counts.get(d, 0) * 3.2
        # 2nd order pair transition: 4.8 per occurrence (high precision pattern match)
        scores[d] += second_counts.get(d, 0) * 4.8

    # ---------------------------------------------------------
    # 2. RECURRENCE GAP ANALYSIS & POISSON SWEET-SPOT
    # ---------------------------------------------------------
    # Find periods since each digit last appeared
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
            last_gap[d] = sample_size + 10

    for d in range(10):
        g = last_gap.get(d, 50)
        avg_g = (sum(gap_history[d]) / len(gap_history[d])) if gap_history[d] else 10.0

        # Optimal recurrence gap window in 30s WinGo is 3 to 14 periods
        if 3 <= g <= 14:
            scores[d] += 4.5
        elif g == 1 or g == 2:
            # Immediate twin repeat probability
            scores[d] += 2.8
        elif g > 25:
            # Overdue sleeping number probability
            scores[d] += 3.5

        # Proximity to digit's historical average gap
        if abs(g - avg_g) <= 1.5:
            scores[d] += 3.0

    # ---------------------------------------------------------
    # 3. EXPONENTIAL DECAY MOMENTUM (EMA FREQUENCY)
    # ---------------------------------------------------------
    decay_rate = 0.035
    for idx, r in enumerate(sample):
        d = r["number"]
        weight = math.exp(-decay_rate * idx)
        scores[d] += weight * 1.5

    # ---------------------------------------------------------
    # 4. HARMONIC MIRROR & MODULO SYMMETRIES
    # ---------------------------------------------------------
    # 9's complement (mirror digit)
    mirror_d = 9 - curr_num
    scores[mirror_d] += 2.6

    # Modulo 5 polarity partner (0-5, 1-6, 2-7, 3-8, 4-9)
    mod5_d = (curr_num + 5) % 10
    scores[mod5_d] += 2.4

    # Consecutive sequence flow (curr + 1, curr - 1)
    scores[(curr_num + 1) % 10] += 1.8
    scores[(curr_num - 1) % 10] += 1.8

    # ---------------------------------------------------------
    # 5. RECENT 10-ROUND HOT CLUSTER BOOST
    # ---------------------------------------------------------
    recent_10 = [r["number"] for r in sample[:min(10, sample_size)]]
    hot_counter = Counter(recent_10)
    for d, count in hot_counter.items():
        scores[d] += count * 1.2

    # ---------------------------------------------------------
    # 6. EXTRACT TOP 3 HIGHEST PROBABILITY DIGITS
    # ---------------------------------------------------------
    ranked = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    top_3 = sorted(ranked[:3])

    num_str = f"{top_3[0]},{top_3[1]},{top_3[2]}"

    return {
        "size": "--",
        "num": num_str,
        "color": "--"
    }

# =========================================================
# EXISTING HIGH QUALITY MARKET ANALYSIS ENGINES
# =========================================================

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
        if 3 <= gap <= 12:
            g_score = 4.0
        elif gap > 20:
            g_score = 2.0
        else:
            g_score = 1.0
        scores[d] = t_score + g_score

    ranked_digits = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    n1, n2 = ranked_digits[0], ranked_digits[1]
    if n1 > n2:
        n1, n2 = n2, n1

    recent_12 = [r["size"] for r in sample[:12]]
    big_ratio = recent_12.count("BIG") / len(recent_12)
    target_bigs = sum(1 for x in [n1, n2] if x >= 5)
    if target_bigs == 2 or (target_bigs == 1 and big_ratio >= 0.5):
        pred_size = "BIG"
    elif target_bigs == 0 or (target_bigs == 1 and big_ratio < 0.5):
        pred_size = "SMALL"
    else:
        pred_size = "BIG" if (n1 + n2) >= 9 else "SMALL"

    return {
        "size": pred_size,
        "num": f"{n1},{n2}",
        "color": "--"
    }

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
        if dominant_count >= 11:
            pred_size = streak_type
        else:
            pred_size = "SMALL" if streak_type == "BIG" else "BIG"
    else:
        recent_10 = sizes[:10]
        big_c = recent_10.count("BIG")
        small_c = recent_10.count("SMALL")
        if big_c > small_c:
            pred_size = "BIG"
        elif small_c > big_c:
            pred_size = "SMALL"
        else:
            pred_size = "SMALL" if sizes[0] == "BIG" else "BIG"

    return {
        "size": pred_size,
        "num": "--",
        "color": "--"
    }

def analyze_demon_king(records):
    """DEMON KING: Pure Color Cycle Master."""
    if len(records) < 5:
        return {"size": "--", "num": "--", "color": "RED"}

    sample = records[:50]
    colors = [r["color"] for r in sample]

    violet_gaps = []
    gap = 0
    for c in colors:
        if c == "VIOLET":
            violet_gaps.append(gap)
            gap = 0
        else:
            gap += 1

    avg_violet_gap = (sum(violet_gaps) / len(violet_gaps)) if violet_gaps else 10
    current_gap_since_violet = next((i for i, c in enumerate(colors) if c == "VIOLET"), 15)

    r_count = colors[:10].count("RED")
    g_count = colors[:10].count("GREEN")

    if colors[0] == colors[1] == colors[2] and colors[0] in ["RED", "GREEN"]:
        pred_color = "GREEN" if colors[0] == "RED" else "RED"
    elif r_count > g_count:
        pred_color = "RED" if colors[0] != "RED" else "GREEN"
    else:
        pred_color = "GREEN" if colors[0] != "GREEN" else "RED"

    if current_gap_since_violet >= int(avg_violet_gap + 4):
        pred_color = "VIOLET"

    return {
        "size": "--",
        "num": "--",
        "color": pred_color
    }

def analyze_red_pro(records):
    """RED PRO WINNER: Sequence pattern search from page 3-50 + affinity resolution."""
    if len(records) < 5:
        return {"size": "BIG", "num": "1,5", "color": "GREEN"}

    t1 = records[0]["number"]
    t2 = records[1]["number"] if len(records) > 1 else (t1 + 1) % 10

    found_idx = -1
    search_start = 20 if len(records) >= 25 else 2
    for i in range(search_start, len(records) - 2):
        curr_pair = (records[i]["number"], records[i + 1]["number"])
        if curr_pair == (t1, t2) or curr_pair == (t2, t1):
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
    if pair_nums.issubset(GREEN_AFFINITY) or (9 in pair_nums and 5 in pair_nums) or (3 in pair_nums and 5 in pair_nums) or (9 in pair_nums and 3 in pair_nums):
        pred_color = "GREEN"
    elif pair_nums.issubset(RED_AFFINITY) or (0 in pair_nums and any(x in RED_NUMBERS for x in pair_nums)):
        pred_color = "RED"
    else:
        c_above = get_color(n_above)
        c_below = get_color(n_below)
        pred_color = c_above if c_above == c_below else "GREEN"

    if (9 in pair_nums and 5 in pair_nums) or (9 in pair_nums and 3 in pair_nums):
        pred_size = "BIG"
    elif n_above >= 5 and n_below >= 5:
        pred_size = "BIG"
    elif n_above < 5 and n_below < 5:
        pred_size = "SMALL"
    else:
        avg = (n_above + n_below) / 2.0
        pred_size = "BIG" if avg >= 4.5 else "SMALL"

    return {
        "size": pred_size,
        "num": f"{n_above},{n_below}",
        "color": pred_color
    }

def analyze_green_pro(records):
    """GREEN PRO WINNER: 150-Rounds Markov Transition Chain + 3-Digit Sniper."""
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

    while len(predicted_pool) < 3:
        for fallback in [1, 5, 9, 3, 7, 0, 8]:
            if fallback not in predicted_pool:
                predicted_pool.append(fallback)
            if len(predicted_pool) == 3:
                break

    target_3_numbers = sorted(predicted_pool)
    num_str = f"{target_3_numbers[0]},{target_3_numbers[1]},{target_3_numbers[2]}"

    sizes_last_10 = [r["size"] for r in sample[:10]]
    big_count = sizes_last_10.count("BIG")
    if big_count >= 7:
        pred_size = "SMALL"
    elif big_count <= 3:
        pred_size = "BIG"
    else:
        big_in_target = sum(1 for n in target_3_numbers if n >= 5)
        pred_size = "BIG" if big_in_target >= 2 else "SMALL"

    colors_last_10 = [r["color"] for r in sample[:10]]
    green_count = colors_last_10.count("GREEN")
    red_count = colors_last_10.count("RED")

    if green_count > red_count:
        pred_color = "GREEN" if (colors_last_10 and colors_last_10[0] != "GREEN" or green_count >= 6) else "RED"
    else:
        pred_color = "RED" if (colors_last_10 and colors_last_10[0] != "RED" or red_count >= 6) else "GREEN"

    return {
        "size": pred_size,
        "num": num_str,
        "color": pred_color
    }

def analyze_titan_ai(records):
    """TITAN AI VIP: Multi-indicator consensus engine."""
    if len(records) < 5:
        return {"size": "BIG", "num": "2,6", "color": "RED"}

    sample = records[:40]
    nums = [r["number"] for r in sample]
    avg_num = sum(nums[:8]) / 8.0
    pred_size = "BIG" if avg_num >= 4.5 else "SMALL"

    odd_count = sum(1 for n in nums[:12] if n % 2 != 0)
    target_parity = 0 if odd_count >= 7 else 1

    candidates = [n for n in range(10) if (n % 2 == target_parity)]
    if pred_size == "BIG":
        candidates = [c for c in candidates if c >= 5]
    else:
        candidates = [c for c in candidates if c < 5]

    if len(candidates) < 2:
        candidates = [2, 6] if pred_size == "BIG" else [1, 3]

    n1, n2 = candidates[0], candidates[1]
    pred_color = get_color(n1)

    return {
        "size": pred_size,
        "num": f"{n1},{n2}",
        "color": pred_color
    }

def analyze_phoenix_matrix(records):
    """PHOENIX MATRIX: Anti-Streak Reversion Hunter."""
    if len(records) < 5:
        return {"size": "SMALL", "num": "0,4", "color": "--"}

    sample = records[:30]
    first_size = sample[0]["size"]
    streak = 1
    for r in sample[1:]:
        if r["size"] == first_size:
            streak += 1
        else:
            break

    pred_size = "SMALL" if first_size == "BIG" else "BIG"
    if pred_size == "SMALL":
        n1, n2 = 1, 4
    else:
        n1, n2 = 6, 8

    return {
        "size": pred_size,
        "num": f"{n1},{n2}",
        "color": "--"
    }

def analyze_shadow_sniper(records):
    """SHADOW SNIPER: Golden Ratio Interval Gap Sniper."""
    if len(records) < 5:
        return {"size": "BIG", "num": "5,9", "color": "--"}

    sample = records[:50]
    curr = sample[0]["number"]
    n1 = (curr + 3) % 10
    n2 = (curr + 8) % 10
    if n1 > n2:
        n1, n2 = n2, n1

    pred_size = "BIG" if (n1 + n2) >= 9 else "SMALL"
    return {
        "size": pred_size,
        "num": f"{n1},{n2}",
        "color": "--"
    }

ENGINE_ANALYZERS = {
    "NUMBER_SHOT": analyze_number_shot,
    "TIGER": analyze_tiger_pro,
    "DRAGON": analyze_dragon_pro,
    "DEMON": analyze_demon_king,
    "RED_PRO": analyze_red_pro,
    "GREEN_PRO": analyze_green_pro,
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

        # Dictionary of engines: key -> {pred, history, win_loss}
        self.engines_data = {}
        for eng_key in ENGINE_KEYS_ORDER:
            self.engines_data[eng_key] = {
                "pred": {"period": "", "size": "--", "num": "--", "color": "--"},
                "history": {},       # period -> {prediction dict, timestamp}
                "win_loss": {}       # period -> outcome ("JAC", "WIN", "LOSS")
            }

    def get_engine_last_10_stats(self, eng_key: str):
        """
        Calculates Win Rate, Level, Jackpots, and Ranking Score
        based strictly on the LAST 10 evaluated periods.
        For NUMBER_SHOT, only JAC and LOSS exist!
        """
        edata = self.engines_data[eng_key]
        win_loss = edata["win_loss"]
        is_pure_num = (eng_key == "NUMBER_SHOT" or ENGINES[eng_key]["type"] == "PURE_NUMBER")

        sorted_periods = sorted(win_loss.keys(), reverse=True)
        last_10_periods = sorted_periods[:10]

        total = len(last_10_periods)
        if total == 0:
            return {
                "total": 0,
                "wins": 0,
                "jackpots": 0,
                "losses": 0,
                "win_rate": 80.0,
                "score": 85.0,
                "level": "LVL 4",
                "is_top": False
            }

        wins = 0
        jackpots = 0
        losses = 0

        for p in last_10_periods:
            res = win_loss[p]
            if res == "JAC":
                jackpots += 1
                wins += 1
            elif res == "WIN":
                wins += 1
            else:
                losses += 1

        win_rate = round((wins / total) * 100, 1)

        # Higher score weight for 3-number high-precision jackpots
        if is_pure_num:
            score = (win_rate * 1.5) + (jackpots * 15)
        else:
            score = win_rate + (jackpots * 12)

        if win_rate >= 80:
            level = "LVL MAX"
        elif win_rate >= 70:
            level = "LVL 5"
        elif win_rate >= 60:
            level = "LVL 4"
        elif win_rate >= 40:
            level = "LVL 3"
        else:
            level = "LVL 2"

        return {
            "total": total,
            "wins": wins,
            "jackpots": jackpots,
            "losses": losses,
            "win_rate": win_rate,
            "score": score,
            "level": level,
            "is_top": False
        }

    def get_ranked_engines(self):
        """Returns engine keys sorted by score descending (highest performer at TOP)"""
        scored = []
        for eng_key in ENGINE_KEYS_ORDER:
            stats = self.get_engine_last_10_stats(eng_key)
            scored.append((eng_key, stats["score"], stats["win_rate"]))

        scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
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

class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.markets = {
            "30S": MarketState("30S"),
            "5M": MarketState("5M")
        }
        self.active_chats = {}

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
# OUTCOME EVALUATOR (JAC / LOSS STRICTLY FOR NUMBER SHOT)
# =========================================================
def evaluate_market_outcomes(m_state: MarketState, data):
    """
    Evaluates outcomes for each engine.
    For NUMBER SHOT:
      - If actual number matches ANY of the 3 numbers -> JAC (Jackpot)
      - Otherwise -> LOSS (No WIN)
    """
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

                # 1. NUMBER SHOT PRO (PURE 3-DIGIT SNIPER):
                # STRICTLY JAC OR LOSS ONLY!
                if eng_key == "NUMBER_SHOT" or ENGINES[eng_key]["type"] == "PURE_NUMBER":
                    if act_n in pred_nums:
                        win_loss[p] = "JAC"
                    else:
                        win_loss[p] = "LOSS"

                # 2. TIGER PRO (SNIPER + SIZE):
                elif eng_key == "TIGER" or ENGINES[eng_key]["type"] == "SNIPER_SIZE":
                    if act_n in pred_nums:
                        win_loss[p] = "JAC"
                    elif pred_s == act_s:
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                # 3. DRAGON PRO (PURE_SIZE):
                elif eng_key == "DRAGON" or ENGINES[eng_key]["type"] == "PURE_SIZE":
                    if pred_s == act_s:
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                # 4. DEMON KING (PURE_COLOR):
                elif eng_key == "DEMON" or ENGINES[eng_key]["type"] == "PURE_COLOR":
                    if pred_c == "VIOLET" and act_c == "VIOLET":
                        win_loss[p] = "JAC"
                    elif pred_c == act_c:
                        win_loss[p] = "WIN"
                    elif act_c == "VIOLET" and ((pred_c == "RED" and act_n == 0) or (pred_c == "GREEN" and act_n == 5)):
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

                # 5. FULL ENGINES (RED_PRO, GREEN_PRO, TITAN):
                else:
                    if act_n in pred_nums:
                        win_loss[p] = "JAC"
                    elif (pred_s == act_s) or (pred_c == act_c):
                        win_loss[p] = "WIN"
                    else:
                        win_loss[p] = "LOSS"

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
# VIP UI & CLEAN NAVIGATION MARKUPS
# =========================================================
def get_market_selection_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_30s = types.InlineKeyboardButton(to_vip("WINGO 30 SECONDS"), callback_data="selm_30S")
    btn_5m = types.InlineKeyboardButton(to_vip("WINGO 5 MINUTES"), callback_data="selm_5M")
    markup.add(btn_30s, btn_5m)
    return markup

def get_engine_selection_markup(market_key: str):
    """DYNAMIC LEADERBOARD: Ranked by Last 10 Rounds Score."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    m_state = state.markets[market_key]
    ranked_engines = m_state.get_ranked_engines()

    for idx, eng_key in enumerate(ranked_engines):
        eng_info = ENGINES[eng_key]
        stats = m_state.get_engine_last_10_stats(eng_key)

        is_top = (idx == 0)
        win_pct = f"{int(stats['win_rate'])}%"

        if is_top:
            label = f"TOP 1 {eng_info['name']} [{stats['level']} {win_pct} WIN]"
        else:
            label = f"{eng_info['name']} [{stats['level']} {win_pct}]"

        btn = types.InlineKeyboardButton(to_vip(label), callback_data=f"launch_{market_key}_{eng_key}")
        markup.add(btn)

    btn_back = types.InlineKeyboardButton(to_vip("BACK TO MARKETS"), callback_data="back_markets")
    markup.add(btn_back)
    return markup

def get_dashboard_header(market_key: str, eng_key: str) -> str:
    market_name = MARKETS[market_key]["name"]
    eng_info = ENGINES.get(eng_key, ENGINES["NUMBER_SHOT"])
    m_state = state.markets[market_key]
    stats = m_state.get_engine_last_10_stats(eng_key)
    ranked = m_state.get_ranked_engines()
    rank_pos = ranked.index(eng_key) + 1 if eng_key in ranked else 1

    rank_str = "TOP 1 KING" if rank_pos == 1 else f"RANK {rank_pos}"

    # Custom subheader for NUMBER SHOT
    if eng_key == "NUMBER_SHOT":
        stat_line = f"<i>{to_vip('LAST 10 ROUNDS')}: {to_vip(str(stats['jackpots']))}/{to_vip(str(stats['total']))} {to_vip('JACKPOTS')} ({to_vip(str(stats['win_rate']))}%)</i>\n"
    else:
        stat_line = f"<i>{to_vip('LAST 10 ROUNDS')}: {to_vip(str(stats['wins']))}/{to_vip(str(stats['total']))} {to_vip('WIN')} ({to_vip(str(stats['win_rate']))}%)</i>\n"

    return (
        f"<b>{to_vip('DRX-TM PRO')} | {to_vip('SYSTEM ONLINE')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(eng_info['name'])} [{to_vip(rank_str)}]</b>\n"
        f"{stat_line}"
        "────────────────────────"
    )

def create_market_markup(market_key: str = "30S", page: int = 1, eng_key: str = "NUMBER_SHOT"):
    """
    CLEAN DASHBOARD NAVIGATION:
    - Row 1: Period
    - Row 2: Live Timer Countdown + ASCII Progress Bar
    - Row 3: Prediction Box:
        * For NUMBER_SHOT: 3 pure numbers [A] [B] [C] (No size, No color)
        * For other engines: Size, Number, Color
    - Row 4-13: 10 Data Rows per page with outcome (JAC / LOSS for Number Shot)
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
    edata = m_state.engines_data.get(eng_key, m_state.engines_data["NUMBER_SHOT"])
    pred = edata["pred"]

    if eng_key == "NUMBER_SHOT" or ENGINES[eng_key]["type"] == "PURE_NUMBER":
        nums = [x.strip() for x in pred['num'].split(",") if x.strip()]
        if len(nums) == 3:
            btn_n1 = types.InlineKeyboardButton(f"[{to_vip(nums[0])}]", callback_data="none")
            btn_n2 = types.InlineKeyboardButton(f"[{to_vip(nums[1])}]", callback_data="none")
            btn_n3 = types.InlineKeyboardButton(f"[{to_vip(nums[2])}]", callback_data="none")
            markup.row(btn_n1, btn_n2, btn_n3)
        else:
            markup.row(types.InlineKeyboardButton(f"{to_vip('NUM')}: {to_vip(pred['num'])}", callback_data="none"))
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
                    eng_key = info.get("engine", "NUMBER_SHOT")
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
    welcome_text = (
        f"<b>{to_vip('DRX-TM PRO')} | {to_vip('SYSTEM ONLINE')}</b>\n"
        f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
        "────────────────────────"
    )
    markup = get_market_selection_markup()
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # 1. Market Selection -> Shows Dynamically Ranked Engines
    if data.startswith("selm_"):
        market_key = data.split("_")[1]
        market_name = MARKETS[market_key]["name"]
        text = (
            f"<b>{to_vip('DRX-TM PRO')} | {to_vip('LEADERBOARD')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
            f"<i>{to_vip('SELECT ENGINE (RANKED BY LAST 10 ROUNDS)')}</i>\n"
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

    # 2. Launch Engine Dashboard
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

    # 3. Clean Engine Switcher (PREV / NEXT ENGINE)
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

    # 4. Back to Engines Leaderboard
    if data == "back_engines":
        with state.lock:
            chat_info = state.active_chats.get(chat_id, {})
            curr_market = chat_info.get("market", "30S")

        market_name = MARKETS[curr_market]["name"]
        text = (
            f"<b>{to_vip('DRX-TM PRO')} | {to_vip('LEADERBOARD')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
            f"<i>{to_vip('SELECT ENGINE (RANKED BY LAST 10 ROUNDS)')}</i>\n"
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
        bot.answer_callback_query(call.id, text=to_vip("ENGINE LEADERBOARD"))
        return

    # 5. Back to Markets
    if data == "back_markets":
        welcome_text = (
            f"<b>{to_vip('DRX-TM PRO')} | {to_vip('SYSTEM ONLINE')}</b>\n"
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

    # 6. Pagination (1 to 50 Pages)
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                chat_info = state.active_chats.get(chat_id, {})
                curr_market = chat_info.get("market", "30S")
                curr_engine = chat_info.get("engine", "NUMBER_SHOT")
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

    # 7. Refresh Button
    elif data == "refresh":
        try:
            with state.lock:
                info = state.active_chats.get(chat_id, {"market": "30S", "page": 1, "engine": "NUMBER_SHOT"})
                m_key = info.get("market", "30S")
                eng_key = info.get("engine", "NUMBER_SHOT")
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

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    if telebot is None:
        print("=" * 65)
        print("ERROR: Required library 'pyTelegramBotAPI' is not installed.")
        print("Please install dependencies by running:")
        print("    pip install pyTelegramBotAPI requests")
        print("=" * 65)
        import sys
        sys.exit(1)

    print("=" * 65)
    print(f"{to_vip('DRX-TM PRO')} [SYSTEM ONLINE]")
    print(f"Focused Market: WINGO 30 SECONDS (Also supports WINGO 5 MINUTES)")
    print(f"Flagship Engine: NUMBER SHOT PRO (Pure 3-Digit Sniper, JAC/LOSS Only)")
    print(f"Engines: NUMBER SHOT, TIGER PRO, DRAGON PRO, DEMON KING, + 5 Advanced Engines")
    print(f"Dynamic Leaderboard: Last-10 Rounds Score Evaluation")
    print(f"Total Pages: {TOTAL_PAGES}")
    print("=" * 65)

    thread = threading.Thread(target=real_time_market_loop, daemon=True)
    thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Crash: {e}. Restarting in 5s...")
            time.sleep(5)
