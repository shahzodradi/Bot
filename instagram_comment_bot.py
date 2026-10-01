"""Instagram izohlariga avtomatik link yuboruvchi bot.

Kimdir Instagram postingiz ostiga izoh yozsa (masalan `7` yoki `kino`), bot o'sha odamga
Direct (shaxsiy xabar) orqali mos linkni yuboradi va ixtiyoriy ravishda izohga ochiq javob
qoldiradi. Instagram API (Instagram Login) webhook'lari va "Private Replies" ishlatiladi.
"""
import hashlib
import hmac
import json
import logging
import os
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
DEFAULT_LINK = os.environ.get("DEFAULT_LINK", "")  # mos kalit so'z topilmasa yuboriladigan link
PUBLIC_REPLY = os.environ.get("PUBLIC_REPLY", "✅ Linkni Direct'ga yubordim!")  # bo'sh qoldirilsa izohga javob yozilmaydi
DM_TEMPLATE = os.environ.get("DM_TEMPLATE", "Salom! Siz so'ragan link: {link}")
GRAPH_API = os.environ.get("IG_GRAPH_API", "https://graph.instagram.com/v21.0")

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


def send_private_reply(comment_id: str, text: str):
    """Izoh muallifiga Direct orqali xabar yuboradi (har bir izohga faqat bir marta, 7 kun ichida)."""
    resp = requests.post(
        f"{GRAPH_API}/me/messages",
        headers={"Authorization": f"Bearer {IG_ACCESS_TOKEN}"},
        json={"recipient": {"comment_id": comment_id}, "message": {"text": text}},
        timeout=15,
    )
    if not resp.ok:
        logger.error("Direct xabar yuborilmadi (%s): %s", resp.status_code, resp.text)
    return resp.ok


def send_public_reply(comment_id: str, text: str):
    """Izohning o'ziga ochiq javob yozadi."""
    resp = requests.post(
        f"{GRAPH_API}/{comment_id}/replies",
        headers={"Authorization": f"Bearer {IG_ACCESS_TOKEN}"},
        data={"message": text},
        timeout=15,
    )
    if not resp.ok:
        logger.error("Izohga javob yozilmadi (%s): %s", resp.status_code, resp.text)


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

    logger.info("@%s ga link yuborilmoqda: %s", author.get("username"), link)
    if send_private_reply(comment_id, DM_TEMPLATE.format(link=link)) and PUBLIC_REPLY:
        send_public_reply(comment_id, PUBLIC_REPLY)


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

    body = request.get_json(silent=True) or {}
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            # Meta javobni tez kutadi, shuning uchun API so'rovlarini alohida oqimda bajaramiz
            threading.Thread(
                target=handle_comment, args=(str(entry.get("id")), change.get("value", {}))
            ).start()
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
