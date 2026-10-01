# Raqam bo'yicha Video Yetkazish Boti

Foydalanuvchi botga raqam yuboradi (masalan `1`, `2`, `15`) — bot Telegram kanalidagi mos
videoni topib, foydalanuvchiga jo'natadi. Videolar kanalda saqlanadi, bot ularni faqat
ko'chirib (copy) yuboradi.

## 1. Kanal va bot sozlash

1. Telegram'da yangi **kanal** yarating (public yoki private — farqi yo'q) va videolaringizni
   shu yerga joylang.
2. [@BotFather](https://t.me/BotFather) orqali bot yarating, tokenni oling.
3. Botni kanalga **administrator** sifatida qo'shing (kamida "Post Messages" huquqisiz ham
   ishlaydi, lekin admin bo'lishi shart — aks holda bot kanal ichidagi xabarlarni o'qiy olmaydi).
4. Kanal ID'sini oling — eng oson yo'li: kanalga biror xabar yuborib, uni
   [@userinfobot](https://t.me/userinfobot) yoki [@getidsbot](https://t.me/getidsbot)ga forward
   qiling, u sizga kanalning raqamli ID'sini beradi (odatda `-100` bilan boshlanadi).
5. O'zingizning shaxsiy Telegram ID'ingizni ham xuddi shu bot orqali oling — bu `ADMIN_ID`
   bo'ladi (faqat siz raqamlarni videolarga bog'lay olasiz).

## 2. O'rnatish

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="sizning_tokeningiz"
export CHANNEL_ID="-100xxxxxxxxxx"
export ADMIN_ID="sizning_user_id_ingiz"
python video_delivery_bot.py
```

Doim ishlab turishi uchun botni Railway, Render yoki VPS'ga joylashtiring.

## 3. Videolarga raqam bog'lash

1. Admin sifatida kanaldagi videoni **botga forward qiling** (kanaldan to'g'ridan-to'g'ri
   forward, boshqa joydan emas).
2. Bot sizdan shu videoga qaysi raqamni berishni so'raydi.
3. Raqamni oddiy xabar sifatida yozing (masalan `7`) — bot uni saqlab qo'yadi.
4. Barcha bog'langan raqamlarni ko'rish uchun botga `/list` yuboring (faqat admin uchun
   ishlaydi).

## 4. Foydalanuvchi tomonidan ishlatilishi

Har qanday foydalanuvchi botga raqam yuborsa (masalan `7`), bot mos videoni kanaldan olib,
to'g'ridan-to'g'ri o'sha foydalanuvchiga jo'natadi.

## 5. Kompyuter yoqiq turmasa ham 24/7 ishlashi uchun (Render.com, tekin)

Bot kodi shunday yozilganki, Render'ga joylasangiz avtomatik "webhook" rejimiga o'tadi —
alohida sozlash shart emas.

1. Shu fayllarni (`video_delivery_bot.py`, `requirements.txt`) GitHub'da yangi repository
   (masalan `kino-bot`) ochib, shu yerga yuklang.
2. [render.com](https://render.com)da bepul ro'yxatdan o'ting (kredit karta so'ramaydi),
   GitHub akkauntingizni ulang.
3. Dashboard'da **New → Web Service** tanlang, yaratgan repositoryingizni tanlang.
4. Sozlamalarda:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python video_delivery_bot.py`
5. **Environment** bo'limida quyidagi o'zgaruvchilarni qo'shing: `TELEGRAM_BOT_TOKEN`,
   `CHANNEL_ID`, `ADMIN_ID` (3-punktdagi kabi).
6. **Create Web Service** tugmasini bosing — bir necha daqiqada bot ishga tushadi va
   kompyuteringiz o'chiq bo'lsa ham 24/7 ishlab turadi.
7. (Tavsiya) Render'ning bepul tarifi 15 daqiqa xabar kelmasa "uxlab qoladi", birinchi
   xabarga sekinroq javob berishi mumkin. Buni oldini olish uchun
   [UptimeRobot](https://uptimerobot.com)da bepul monitor yarating va Render bergan
   URL'ingizni (masalan `https://kino-bot.onrender.com`) har 10-14 daqiqada "ping"
   qilib turishini sozlang.

## Eslatmalar

- Bog'lanishlar `video_map.json` faylida saqlanadi. Serverni qayta ishga tushirsangiz ham bu
  fayl saqlanib qoladi (agar hosting'ingiz disk saqlashni qo'llab-quvvatlasa). Katta hajmda
  ishlatmoqchi bo'lsangiz, buni SQLite yoki boshqa bazaga ko'chirish tavsiya etiladi.
- `copy_message` funksiyasi videoni "forwarded from" belgisisiz, xuddi bot o'zi yuborayotgandek
  jo'natadi.
- Kanal **private** bo'lsa ham bot ishlayveradi, chunki bot admin sifatida a'zo — foydalanuvchi
  kanalga a'zo bo'lishi shart emas, faqat bot bilan gaplashadi.

---

# Instagram izohlariga avtomatik link yuborish

`instagram_comment_bot.py` — kimdir Instagram postingiz ostiga izoh yozsa, bot o'sha odamga
**Direct** orqali link yuboradi va izohga "✅ Linkni Direct'ga yubordim!" deb javob yozadi.

Qaysi link yuborilishi:

1. Izohda `instagram_links.json`dagi kalit so'z bo'lsa (masalan `kino`) — o'sha link.
2. Izohda raqam bo'lsa (masalan `7`) va `TELEGRAM_BOT_USERNAME` berilgan bo'lsa —
   `https://t.me/<bot>?start=7`. Foydalanuvchi linkni bossa, Telegram bot unga **7-videoni
   darhol** yuboradi.
3. Aks holda `DEFAULT_LINK` (berilgan bo'lsa), bo'lmasa hech narsa yuborilmaydi.

## 1. Instagram va Meta ilovasini sozlash

1. Instagram akkauntingiz **Professional** (Business yoki Creator) bo'lishi kerak:
   Sozlamalar → Akkaunt turi.
2. [developers.facebook.com](https://developers.facebook.com/apps)da yangi ilova yarating
   (turi: **Business**), unga **Instagram** mahsulotini qo'shing va
   "API setup with Instagram login" bo'limini oching.
3. Instagram akkauntingizni qo'shing va **access token** yarating — bu `IG_ACCESS_TOKEN`.
   Ruxsatlar: `instagram_business_basic`, `instagram_business_manage_comments`,
   `instagram_business_manage_messages`.
4. Shu sahifadagi **Instagram app secret** — bu `IG_APP_SECRET`.
5. Instagram ilovasida: Sozlamalar → Maxfiylik → Xabarlar → **"Connected tools"
   (Ulangan vositalar)** ga ruxsat bering, aks holda Direct xabar yuborilmaydi.

## 2. Serverga joylash (Render.com)

Telegram botdagi kabi **New → Web Service**, lekin alohida servis sifatida:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python instagram_comment_bot.py`
- **Environment**:
  - `IG_ACCESS_TOKEN`, `IG_APP_SECRET`
  - `IG_VERIFY_TOKEN` — o'zingiz o'ylab topgan istalgan so'z (masalan `mening_sirim_123`)
  - `TELEGRAM_BOT_USERNAME` — Telegram botingiz nomi, `@`siz (ixtiyoriy)
  - `DEFAULT_LINK` — mos so'z topilmasa yuboriladigan link (ixtiyoriy)
  - `DM_TEMPLATE` — Direct xabar matni, `{link}` o'rniga link qo'yiladi (ixtiyoriy)
  - `PUBLIC_REPLY` — izohga ochiq javob matni (ixtiyoriy; javob yozilmasin desangiz,
    qiymatini bitta bo'sh joy emas, butunlay bo'sh qilib qo'ying)

## 3. Webhook'ni ulash

1. Meta ilovasida "Configure webhooks" bo'limida:
   - **Callback URL**: `https://<render-manzilingiz>.onrender.com/webhook`
   - **Verify token**: `IG_VERIFY_TOKEN` bilan bir xil so'z
2. **Verify and save** bosing, so'ng **comments** maydoniga obuna bo'ling (Subscribe).
3. Akkaunt uchun webhook'ni yoqing ("Webhook subscription" tugmasi).

## 4. Muhim cheklovlar

- Ilova **Development** rejimida bo'lsa, bot faqat ilovaga "Instagram tester" sifatida
  qo'shilgan akkauntlar izohlariga javob beradi. Hammaga ishlashi uchun ilovani
  **Live** rejimga o'tkazish va yuqoridagi ruxsatlar uchun Meta **App Review**dan o'tish kerak.
- Instagram har bir izohga faqat **bitta** Direct javob yuborishga va faqat izoh yozilganidan
  keyin **7 kun ichida** ruxsat beradi.
- Access token muddati ~60 kun; muddati tugashidan oldin uni yangilab turing.
- Kalit so'z va linklarni `instagram_links.json` faylida o'zgartiring (kichik-katta harf farqi
  yo'q).
