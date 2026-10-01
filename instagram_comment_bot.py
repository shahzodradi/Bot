"""Instagram izohlariga avtomatik link yuboruvchi bot.

Ish tartibi:
1. Kimdir post ostiga izoh yozadi.
2. Bot izohga bir marta ochiq javob yozadi ("Directingizga qarang 📩" va h.k.).
3. Bot o'sha odamga Direct'da tabrik va "🔗 Linkni olish" tugmasini yuboradi.
4. Tugma bosilganda bot odam akkauntga obuna bo'lganini tekshiradi:
   - obuna bo'lmagan bo'lsa — "Avval obuna bo'ling, Qadrdon!" va tugma qaytadan;
   - obuna bo'lgan bo'lsa — linkni yuboradi.
"""
import hashlib
import hmac
import json
import logging
import os
import random
import re
import threading

import requests
from flask import Flask, abort, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bu qiymatlarni muhit o'zgaruvchisi sifatida bering, kodga to'g'ridan-to'g'ri yozmang.
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")  # Instagram user access token
IG_APP_SECRET = os.environ.get("IG_APP_SECRET", "")  # Meta ilovasining Instagram app secret'i
IG_VERIFY_TOKEN = os.environ.get("IG_VERIFY_TOKEN", "")  # webhook tasdiqlash uchun o'zingiz o'ylab topgan so'z
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@")  # masalan: kino_bot
DEFAULT_LINK = os.environ.get("DEFAULT_LINK", "")  # har bir izoh yozganga beriladigan link
GRAPH_API = os.environ.get("IG_GRAPH_API", "https://graph.instagram.com/v21.0")

# Izohga yoziladigan ochiq javoblar — har safar tasodifiy bittasi tanlanadi
PUBLIC_REPLIES = [
    "Directingizga qarang 📩",
    "Jo'natdim ✅",
    "Directingizni tekshiring 👀",
    "Direct'ga yozdim, qarab qo'ying 😉",
    "Yubordim, Direct'ni oching 📬",
]
WELCOME_TEXT = (
    "🎉 Tabriklayman! Siz linkni qo'lga kiritganlar safiga kirdingiz!\n\n"
    "Faqat linkni olish uchun avval bizga obuna bo'ling, so'ng pastdagi tugmani bosing 👇"
)
NOT_FOLLOWING_TEXT = (
    "😊 Siz hali ham obuna bo'lmagansiz. Avval obuna bo'ling, Qadrdon!\n\n"
    "Obuna bo'lgach, tugmani yana bir bor bosing 👇"
)
LINK_TEXT = "✅ Ha, ana endi! Bu link sizga:\n{link}"
BUTTON_TITLE = "🔗 Linkni olish"
PAYLOAD_PREFIX = "GET_LINK:"

LINKS_FILE = "instagram_links.json"
PROCESSED_FILE = "instagram_processed.json"

app = Flask(__name__)
_lock = threading.Lock()


def load_json(path: str, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_link(comment_text: str):
    """Izoh matniga qarab yuboriladigan linkni topadi (topilmasa None)."""
    text = comment_text.strip().lower()
    words = re.findall(r"\w+", text)

    # 1) instagram_links.json'dagi kalit so'zlar: butun izoh yoki izohdagi biror so'z mos kelsa
    links = {k.lower(): v for k, v in load_json(LINKS_FILE, {}).items()}
    if text in links:
        return links[text]
    for word in words:
        if word in links:
            return links[word]

    # 2) Izohda raqam bo'lsa — Telegram botdagi shu raqamli videoga to'g'ridan-to'g'ri link
    if TELEGRAM_BOT_USERNAME:
        number = re.search(r"\d+", text)
        if number:
            return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={number.group()}"

    # 3) Umumiy link
    return DEFAULT_LINK or None


def graph_post(path: str, **kwargs):
    resp = requests.post(
        f"{GRAPH_API}/{path}",
        headers={"Authorization": f"Bearer {IG_ACCESS_TOKEN}"},
        timeout=15,
        **kwargs,
    )
    if not resp.ok:
        logger.error("Instagram API xatosi %s (%s): %s", path, resp.status_code, resp.text)
    return resp.ok


def button_message(text: str, link: str) -> dict:
    """Matn + "Linkni olish" tugmasi. Linkning o'zi tugma ichida yashirin saqlanadi."""
    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "button",
                "text": text,
                "buttons": [
                    {"type": "postback", "title": BUTTON_TITLE, "payload": PAYLOAD_PREFIX + link}
                ],
            },
        }
    }


def send_message(recipient: dict, message: dict):
    return graph_post("me/messages", json={"recipient": recipient, "message": message})


def is_follower(user_id: str) -> bool:
    """Foydalanuvchi bizning akkauntga obuna bo'lganmi?"""
    resp = requests.get(
        f"{GRAPH_API}/{user_id}",
        params={"fields": "is_user_follow_business"},
        headers={"Authorization": f"Bearer {IG_ACCESS_TOKEN}"},
        timeout=15,
    )
    if not resp.ok:
        logger.error("Obunani tekshirib bo'lmadi (%s): %s", resp.status_code, resp.text)
        return False
    return bool(resp.json().get("is_user_follow_business"))


def handle_comment(account_id: str, value: dict):
    comment_id = value.get("id")
    text = value.get("text", "")
    author = value.get("from", {})

    # O'zimizning javoblarimizga reaksiya qilmaymiz (aks holda cheksiz aylana bo'ladi)
    if not comment_id or author.get("id") == account_id:
        return

    with _lock:
        processed = load_json(PROCESSED_FILE, [])
        if comment_id in processed:
            return
        processed.append(comment_id)
        save_json(PROCESSED_FILE, processed[-5000:])

    link = find_link(text)
    if not link:
        logger.info("@%s izohi uchun link topilmadi: %r", author.get("username"), text)
        return

    logger.info("@%s ga Direct yuborilmoqda", author.get("username"))
    # Izohga javob sifatida Direct (Private Reply) — har bir izohga faqat bir marta
    if send_message({"comment_id": comment_id}, button_message(WELCOME_TEXT, link)):
        graph_post(f"{comment_id}/replies", data={"message": random.choice(PUBLIC_REPLIES)})


def handle_postback(sender_id: str, payload: str):
    """Direct'dagi "Linkni olish" tugmasi bosilganda."""
    if not payload.startswith(PAYLOAD_PREFIX):
        return
    link = payload[len(PAYLOAD_PREFIX):]

    if is_follower(sender_id):
        send_message({"id": sender_id}, {"text": LINK_TEXT.format(link=link)})
    else:
        send_message({"id": sender_id}, button_message(NOT_FOLLOWING_TEXT, link))


def signature_is_valid(payload: bytes, header: str) -> bool:
    if not IG_APP_SECRET:
        logger.warning("IG_APP_SECRET berilmagan — webhook imzosi tekshirilmayapti!")
        return True
    expected = "sha256=" + hmac.new(IG_APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


@app.get("/")
def health():
    # UptimeRobot "ping"lari uchun
    return "ok"


@app.get("/webhook")
def verify_webhook():
    """Meta webhook'ni ulashda shu manzilni bir marta tekshiradi."""
    if (request.args.get("hub.mode") == "subscribe"
            and IG_VERIFY_TOKEN
            and request.args.get("hub.verify_token") == IG_VERIFY_TOKEN):
        return request.args.get("hub.challenge", "")
    abort(403)


@app.post("/webhook")
def receive_webhook():
    if not signature_is_valid(request.get_data(), request.headers.get("X-Hub-Signature-256")):
        abort(403)

    # Meta javobni tez kutadi, shuning uchun API so'rovlarini alohida oqimda bajaramiz
    body = request.get_json(silent=True) or {}
    for entry in body.get("entry", []):
        account_id = str(entry.get("id"))
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                threading.Thread(
                    target=handle_comment, args=(account_id, change.get("value", {}))
                ).start()
        for event in entry.get("messaging", []):
            postback = event.get("postback")
            sender_id = event.get("sender", {}).get("id")
            if postback and sender_id and sender_id != account_id:
                threading.Thread(
                    target=handle_postback, args=(sender_id, postback.get("payload", ""))
                ).start()
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
