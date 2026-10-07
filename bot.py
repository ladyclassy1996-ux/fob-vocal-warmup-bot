import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from flask import Flask, request, jsonify

app = Flask(name)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "")
START_DATE = os.environ.get("START_DATE", "2026-10-07")
DAILY_SECRET = os.environ["DAILY_SECRET"]

TIMEZONE = ZoneInfo("Africa/Douala")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


# =========================
# TELEGRAM
# =========================

def telegram(method, data=None):
    response = requests.post(
        f"{TELEGRAM_URL}/{method}",
        json=data or {},
        timeout=30
    )
    return response.json()


# =========================
# SUPABASE
# =========================

def supabase_request(method, endpoint, **kwargs):
    headers = kwargs.pop("headers", {})
    
    final_headers = {
        **SUPABASE_HEADERS,
        **headers
    }

    return requests.request(
        method,
        f"{SUPABASE_URL}/rest/v1/{endpoint}",
        headers=final_headers,
        timeout=30,
        **kwargs
    )


# =========================
# DATE / CHALLENGE DAY
# =========================

def today():
    return datetime.now(TIMEZONE).date()


def challenge_day():
    start = datetime.strptime(
        START_DATE,
        "%Y-%m-%d"
    ).date()

    return (today() - start).days + 1


# =========================
# RECORD COMPLETION
# =========================

def record_completion(user):

    user_id = user["id"]

    username = user.get("username", "")

    full_name = user.get("first_name", "")

    if user.get("last_name"):
        full_name += " " + user["last_name"]

    data = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "completion_date": str(today())
    }

    response = supabase_request(
        "POST",
        "completions",
        json=data,
        headers={
            "Prefer": "resolution=ignore-duplicates"
        }
    )

    return response.ok


# =========================
# USER STATISTICS
# =========================

def get_user_completions(user_id):

    response = supabase_request(
        "GET",
        "completions",
        params={
            "user_id": f"eq.{user_id}",
            "select": "completion_date",
            "order": "completion_date.asc"
        }
    )

    if not response.ok:
        return []

    return [
        row["completion_date"]
        for row in response.json()
    ]


def calculate_streak(dates):

    if not dates:
        return 0

    date_objects = sorted(
        datetime.strptime(
            d,
            "%Y-%m-%d"
        ).date()
        for d in dates
    )

    date_set = set(date_objects)

    streak = 0

    current = today()

    while current in date_set:

        streak += 1

        current -= timedelta(days=1)

    return streak


# =========================
# LEADERBOARD
# =========================

def get_leaderboard():

    response = supabase_request(
        "GET",
        "completions",
        params={
            "select": "user_id,full_name,completion_date",
            "order": "completion_date.asc"
        }
    )

    if not response.ok:
        return "Unable to load leaderboard."

    rows = response.json()

    members = {}

    for row in rows:

        user_id = row["user_id"]

        if user_id not in members:

            members[user_id] = {
                "name": row["full_name"],
                "dates": []
            }

        members[user_id]["dates"].append(
            row["completion_date"]
        )

    ranking = []

    for member in members.values():
[10/7/2026 1:04 PM] Raissa Munoh Melafah: ranking.append({
            "name": member["name"],
            "total": len(member["dates"]),
            "streak": calculate_streak(
                member["dates"]
            )
        })

    ranking.sort(
        key=lambda x: (
            x["streak"],
            x["total"]
        ),
        reverse=True
    )

    text = "🏆 FOB VOCAL WARM-UP LEADERBOARD\n\n"

    if not ranking:
        return text + "No check-ins yet."

    for i, member in enumerate(
        ranking[:10],
        start=1
    ):

        text += (
            f"{i}. {member['name']} — "
            f"{member['total']} days "
            f"🔥 {member['streak']}-day streak\n"
        )

    return text


# =========================
# DAILY MESSAGE
# =========================

def send_daily_message():

    if not GROUP_CHAT_ID:

        return {
            "error": "GROUP_CHAT_ID is not configured"
        }

    day = challenge_day()

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ I COMPLETED TODAY'S WARM-UP",
                    "callback_data": "completed"
                }
            ]
        ]
    }

    text = (
        f"🎤 DAY {day} — "
        "15-MINUTE VOCAL WARM-UP\n\n"
        "Complete your 15-minute "
        "vocal warm-up today.\n\n"
        "When you are finished, tap "
        "the button below to check in.\n\n"
        "Let's stay consistent! 🔥"
    )

    return telegram(
        "sendMessage",
        {
            "chat_id": GROUP_CHAT_ID,
            "text": text,
            "reply_markup": keyboard
        }
    )


