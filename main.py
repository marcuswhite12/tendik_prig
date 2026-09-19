import os
from pathlib import Path
from email.message import EmailMessage

import aiosmtplib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", SMTP_USER)


class RSVP(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    attend: str = Field(..., max_length=200)
    wishes: str = Field("", max_length=500)   # ← пожелание


app = FastAPI(title="Wedding RSVP")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/rsvp")
async def rsvp(payload: RSVP):
    if not SMTP_USER or not SMTP_PASSWORD:
        raise HTTPException(500, "SMTP не настроен на сервере")

    # ---- Красивое письмо (HTML + plain-text fallback) ----
    plain = (
        "Жаңы жооп!\n\n"
        f"Аты: {payload.name}\n"
        f"Жооп: {payload.attend}\n"
    )
    if payload.wishes:
        plain += f"\nКаалоо-тилек:\n{payload.wishes}\n"

    html = f"""
    <html><body style="font-family: Georgia, serif; background:#f5f0e8; padding:24px;">
      <div style="max-width:520px; margin:0 auto; background:#fff; border-radius:16px;
                  padding:28px; border:1px solid #e0d5c5;
                  box-shadow:0 4px 20px rgba(0,0,0,0.06);">
        <h2 style="color:#1a1a1a; font-family:Georgia; margin:0 0 20px;">
          💌 Жаңы жооп
        </h2>
        <p style="font-size:15px; color:#3a3a3a; margin:8px 0;">
          <b>👤 Аты:</b> {payload.name}
        </p>
        <p style="font-size:15px; color:#3a3a3a; margin:8px 0;">
          <b>✅ Жооп:</b> {payload.attend}
        </p>
        {f'''
        <hr style="border:none; border-top:1px solid #e0d5c5; margin:20px 0;">
        <p style="font-size:13px; color:#c9a96e; letter-spacing:2px;
                  text-transform:uppercase; margin:0 0 8px;">
          💐 Каалоо-тилек
        </p>
        <p style="font-size:15px; font-style:italic; color:#3a3a3a;
                  line-height:1.6; margin:0;">
          {payload.wishes}
        </p>
        ''' if payload.wishes else ''}
      </div>
    </body></html>
    """

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"💌 RSVP: {payload.name}"
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,   # для 587. Для 465 → use_tls=True, start_tls=False
        )
    except Exception as e:
        print("SMTP error:", e)
        raise HTTPException(500, "Не удалось отправить письмо")

    return {"ok": True, "message": "Рахмат! Жооп жөнөтүлдү 💌"}


# Статика — в самом конце!
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")