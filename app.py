from __future__ import annotations

import base64
import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client, Client

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"

BUCKET_NAME = "wareneingang-bilder"

USERS = ["Kevin", "Tim", "Frank", "Julian", "Tobi", "Christian"]

COATINGS = [
    "Meta-S",
    "CrN",
    "CrN-RB",
    "Duplex Meta cax",
    "AlCrN",
    "TiN",
    "TiaLN",
    "TiCN",
    "Keine",
]


def placeholder(path: Path, title: str, subtitle: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 900), (8, 9, 12))
    d = ImageDraw.Draw(img)

    try:
        big = ImageFont.truetype("DejaVuSans-Bold.ttf", 86)
        mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        small = ImageFont.truetype("DejaVuSans.ttf", 34)
    except Exception:
        big = mid = small = ImageFont.load_default()

    d.rounded_rectangle((45, 45, 1555, 855), radius=48, fill=(18, 22, 28), outline=(210, 0, 0), width=5)
    d.text((90, 90), "Pondruff / WE", fill=(255, 255, 255), font=big)
    d.text((90, 220), "WARENEINGANGS-TOOL", fill=(230, 0, 0), font=mid)
    d.line((90, 300, 620, 300), fill=(230, 0, 0), width=7)
    d.text((90, 370), title, fill=(255, 255, 255), font=big)
    d.text((90, 500), subtitle, fill=(190, 198, 205), font=small)

    for i, label in enumerate(["Lieferschein", "Bauteile", "Verpackung", "GPT-4.1 OCR"]):
        y = 320 + i * 100
        d.rounded_rectangle((1040, y, 1460, y + 70), radius=20, fill=(29, 35, 44), outline=(230, 0, 0), width=3)
        d.text((1080, y + 18), label, fill=(255, 255, 255), font=small)

    img.save(path)


def ensure_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    items = {
        "wareneingang.png": ("Digitaler Wareneingang mit KI", "Lieferschein mit GPT-4.1 erkennen. Bilder in Cloud speichern."),
        "demo_lieferschein.png": ("Lieferschein", "GPT-4.1 liest Kunde, Artikelnummer, Menge, Masse und Beschichtung."),
        "demo_bauteile.png": ("Bauteile", "Bauteile werden mit dem Wareneingang gespeichert."),
        "demo_verpackung.png": ("Verpackung", "Verpackungsmaterial bleibt als Nachweis erhalten."),
        "demo_suchteil.png": ("KI-Suchfoto", "Unbekanntes Bauteil fotografieren und zuordnen."),
        "demo_buero.png": ("Buerozugriff", "Daten pruefen und fuer WISO kopieren."),
        "slide_1.png": ("Praesentation", "Titel und Uebersicht"),
        "slide_2.png": ("Problem", "Suchen, Zuordnung, Papier und Rueckfragen"),
        "slide_3.png": ("3 Fotos", "Lieferschein, Ware, Verpackung"),
        "slide_4.png": ("Daten erfassen", "Menge, Masse, Artikelnummer, Beschichtung"),
        "slide_5.png": ("KI-Zuordnung", "Foto machen und passenden Lieferschein finden"),
        "slide_6.png": ("Buero", "Copy und Paste fuer WISO"),
        "slide_7.png": ("Export", "CSV und Datenblock"),
        "slide_8.png": ("Nutzen", "Weniger Fehler, schneller arbeiten"),
    }

    for name, (title, subtitle) in items.items():
        p = ASSETS / name
        if not p.exists():
            placeholder(p, title, subtitle)


def css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
            radial-gradient(circle at top right, rgba(180,0,0,.25), transparent 30%),
            linear-gradient(135deg,#030405,#0b0f13 55%,#030405);
            color:white;
        }
        [data-testid="stSidebar"] {
            background:#060708;
            border-right:1px solid rgba(255,255,255,.12)
        }
        h1,h2,h3 {letter-spacing:-.035em}
        .hero {
            border:1px solid rgba(255,255,255,.12);
            border-radius:28px;
            overflow:hidden;
            box-shadow:0 24px 80px rgba(0,0,0,.45);
            margin-bottom:20px;
        }
        .hero img {width:100%; display:block;}
        .hero-text {
            padding:20px 24px;
            background:linear-gradient(90deg,rgba(15,18,22,.96),rgba(120,0,0,.28));
            border-top:1px solid rgba(255,255,255,.12)
        }
        .hero-text h1 {margin:0; font-size:34px;}
        .hero-text p {margin:6px 0 0; color:#aeb7c5; font-size:18px;}
        .card {
            background:rgba(18,22,28,.92);
            border:1px solid rgba(255,255,255,.12);
            border-radius:24px;
            padding:20px;
            box-shadow:0 18px 60px rgba(0,0,0,.25);
            margin-bottom:16px;
        }
        .metric-card {
            background:rgba(18,22,28,.92);
            border:1px solid rgba(255,255,255,.12);
            border-radius:22px;
            padding:20px;
        }
        .metric-label {color:#aeb7c5; font-size:14px;}
        .metric-value {font-size:36px; font-weight:900; line-height:1; margin-top:8px;}
        .metric-hint {color:#e50909; font-size:13px; font-weight:800; margin-top:8px;}
        .status {
            display:inline-flex;
            padding:7px 11px;
            border-radius:999px;
            font-weight:800;
            font-size:12px;
            margin:2px;
        }
        .ok {background:rgba(80,210,60,.16); color:#aaff9b; border:1px solid rgba(80,210,60,.35)}
        .warn {background:rgba(255,176,32,.16); color:#ffd37a; border:1px solid rgba(255,176,32,.35)}
        .bad {background:rgba(229,9,9,.18); color:#ffb8b8; border:1px solid rgba(229,9,9,.4)}
        .ai {background:rgba(77,163,255,.14); color:#b8dcff; border:1px solid rgba(77,163,255,.4)}
        .ai-box {
            background:linear-gradient(135deg,rgba(12,34,58,.95),rgba(28,18,20,.95));
            border:1px solid rgba(77,163,255,.35);
            border-radius:24px;
            padding:20px;
            margin-bottom:16px;
        }
        .stButton>button,.stDownloadButton>button {
            border-radius:14px!important;
            background:linear-gradient(180deg,#f01212,#b80000)!important;
            color:white!important;
            font-weight:800!important;
            border:1px solid rgba(229,9,9,.5)!important;
        }
        .stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]>div {
            background-color:rgba(255,255,255,.055)!important;
            color:white!important;
            border-color:rgba(255,255,255,.13)!important;
            border-radius:14px!important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def img_bytes(name: str) -> bytes:
    return (ASSETS / name).read_bytes()


def to_img(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def entry_dimensions(e: Dict) -> str:
    if e.get("shape") == "Rund":
        return f"Durchmesser {e.get('diameter', 0)} x Laenge {e.get('length', 0)} mm"
    return f"{e.get('length', 0)} x {e.get('width', 0)} x {e.get('height', 0)} mm"


def status_html(status: str) -> str:
    css_class = "ok" if status in ["Abgeschlossen", "Gespeichert"] else "warn"
    return f'<span class="status {css_class}">{status}</span>'


def ai_html(text: str) -> str:
    return f'<span class="status ai">KI {text}</span>'


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        return st.secrets[name]
    except Exception:
        return default


@st.cache_resource
def get_supabase() -> Optional[Client]:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        return create_client(url, key)
    except Exception:
        return None


def cloud_ready() -> bool:
    return get_supabase() is not None


def openai_ready() -> bool:
    return OpenAI is not None and bool(get_secret("OPENAI_API_KEY"))


def signup(email: str, password: str) -> bool:
    sb = get_supabase()
    if not sb:
        st.error("Supabase ist noch nicht eingerichtet.")
        return False
    try:
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Benutzer erstellt. Falls E-Mail-Bestaetigung aktiv ist, bitte E-Mail bestaetigen.")
        return True
    except Exception as e:
        st.error(f"Registrierung fehlgeschlagen: {e}")
        return False


def login(email: str, password: str) -> bool:
    sb = get_supabase()
    if not sb:
        st.error("Supabase ist noch nicht eingerichtet.")
        return False
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.session_state.access_token = res.session.access_token if res.session else None
        return True
    except Exception as e:
        st.error(f"Login fehlgeschlagen: {e}")
        return False


def logout() -> None:
    sb = get_supabase()
    if sb:
        try:
            sb.auth.sign_out()
        except Exception:
            pass
    st.session_state.user = None
    st.session_state.access_token = None


def login_screen() -> None:
    ensure_assets()
    css()
    st.image(ASSETS / "wareneingang.png", use_container_width=True)
    st.title("Pondruff / WE Login")
    st.write("Version mit Supabase Cloud + Login + GPT-4.1 Lieferschein-Erkennung.")

    if not cloud_ready():
        st.warning("Supabase ist noch nicht verbunden. Bitte Streamlit Secrets eintragen.")
        st.code(
            """
SUPABASE_URL = "https://DEIN-PROJEKT.supabase.co"
SUPABASE_ANON_KEY = "DEIN-ANON-KEY"
OPENAI_API_KEY = "sk-..."
            """.strip(),
            language="toml",
        )
        return

    tab_login, tab_signup = st.tabs(["Einloggen", "Benutzer erstellen"])

    with tab_login:
        email = st.text_input("E-Mail", key="login_email")
        password = st.text_input("Passwort", type="password", key="login_password")
        if st.button("Einloggen", use_container_width=True):
            if login(email, password):
                st.rerun()

    with tab_signup:
        email_new = st.text_input("Neue E-Mail", key="signup_email")
        password_new = st.text_input("Neues Passwort", type="password", key="signup_password")
        if st.button("Benutzer erstellen", use_container_width=True):
            signup(email_new, password_new)


def fake_ocr(file=None) -> Dict:
    return {
        "id": f"LS-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%H%M%S')}",
        "customer": "Mustertechnik GmbH",
        "article_no": "ART-123456",
        "description": "Praezisionsteil XY",
        "quantity": 25,
        "shape": "Eckig",
        "diameter": 0.0,
        "length": 120.50,
        "width": 80.25,
        "height": 45.00,
        "polished": "Ja",
        "polishing_price": 25.00,
        "coated": "Ja",
        "coating": "AlCrN",
        "confidence": 94,
        "ocr_note": "Demo-Erkennung: OpenAI API Key fehlt oder wurde nicht genutzt.",
    }


def normalize_coating(value: str) -> str:
    if not value:
        return "Keine"

    v = str(value).strip().lower()
    mapping = {
        "meta-s": "Meta-S",
        "metas": "Meta-S",
        "crn": "CrN",
        "crn-rb": "CrN-RB",
        "crn rb": "CrN-RB",
        "duplex meta cax": "Duplex Meta cax",
        "duplex meta-cax": "Duplex Meta cax",
        "duplex cax": "Duplex Meta cax",
        "alcrn": "AlCrN",
        "alcrn ": "AlCrN",
        "tin": "TiN",
        "tialn": "TiaLN",
        "tialn ": "TiaLN",
        "ticn": "TiCN",
        "keine": "Keine",
        "nein": "Keine",
        "-": "Keine",
    }

    if v in mapping:
        return mapping[v]

    for coating in COATINGS:
        if v == coating.lower():
            return coating

    return "Keine"


def clean_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        return match.group(0)
    return text


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", ".").replace("mm", "").replace("â¬", "").strip()
        return float(value)
    except Exception:
        return default


def safe_int(value, default: int = 1) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return max(1, int(float(value)))
    except Exception:
        return default


def normalize_ocr_result(data: Dict) -> Dict:
    result = fake_ocr(None)

    result["id"] = str(data.get("id") or data.get("delivery_id") or result["id"])
    result["customer"] = str(data.get("customer") or result["customer"])
    result["article_no"] = str(data.get("article_no") or data.get("artikelnummer") or result["article_no"])
    result["description"] = str(data.get("description") or data.get("article_description") or data.get("artikelbezeichnung") or result["description"])
    result["quantity"] = safe_int(data.get("quantity") or data.get("menge"), result["quantity"])

    shape = str(data.get("shape") or data.get("form") or result["shape"]).strip().capitalize()
    result["shape"] = "Rund" if shape.lower() in ["rund", "round", "zylindrisch"] else "Eckig"

    result["diameter"] = safe_float(data.get("diameter") or data.get("durchmesser"), 0.0)
    result["length"] = safe_float(data.get("length") or data.get("laenge") or data.get("lÃ¤nge"), 0.0)
    result["width"] = safe_float(data.get("width") or data.get("breite"), 0.0)
    result["height"] = safe_float(data.get("height") or data.get("hoehe") or data.get("hÃ¶he"), 0.0)

    result["polished"] = "Ja" if str(data.get("polished") or data.get("poliert") or "Nein").lower() in ["ja", "yes", "true", "1"] else "Nein"
    result["polishing_price"] = safe_float(data.get("polishing_price") or data.get("polierpreis"), 0.0)

    coated_raw = str(data.get("coated") or data.get("beschichtet") or "").lower()
    coating = normalize_coating(str(data.get("coating") or data.get("beschichtung") or "Keine"))
    result["coating"] = coating

    if coated_raw in ["ja", "yes", "true", "1"] or coating != "Keine":
        result["coated"] = "Ja"
    else:
        result["coated"] = "Nein"
        result["coating"] = "Keine"

    result["confidence"] = max(0, min(100, safe_int(data.get("confidence") or data.get("sicherheit"), 80)))
    result["ocr_note"] = str(data.get("ocr_note") or data.get("note") or "GPT-4.1 hat den Lieferschein ausgelesen. Bitte alle Werte gegenprÃ¼fen.")

    return result


def real_ocr_lieferschein(uploaded_file) -> Dict:
    if uploaded_file is None:
        st.warning("Bitte zuerst ein Lieferschein-Foto hochladen.")
        return fake_ocr(None)

    if not openai_ready():
        st.warning("OPENAI_API_KEY fehlt oder openai Paket ist nicht installiert. Demo-Erkennung wird genutzt.")
        return fake_ocr(uploaded_file)

    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        image_bytes = uploaded_file.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = f"""
Du bist ein OCR-Assistent fuer Wareneingangs-Lieferscheine.

Lies den Lieferschein aus dem Bild aus und gib NUR gueltiges JSON zurueck.
Keine Erklaerung, kein Markdown.

Wichtig:
- Lieferant ist NICHT wichtig und soll ignoriert werden.
- Erkenne Kunde, Artikelnummer, Artikelbezeichnung, Menge, Masse und Beschichtung.
- Wenn auf dem Lieferschein eine Beschichtung steht, ordne sie einer der erlaubten Beschichtungen zu.
- Wenn die Form rund ist, setze shape = "Rund" und nutze diameter + length.
- Wenn keine Rundform erkennbar ist, setze shape = "Eckig" und nutze length + width + height.
- Wenn ein Wert nicht erkennbar ist, nutze 0 oder leeren String.
- Beschichtung muss eine dieser Optionen sein: {", ".join(COATINGS)}.

JSON Schema:
{{
  "id": "Lieferscheinnummer",
  "customer": "Kunde",
  "article_no": "Artikelnummer",
  "description": "Artikelbezeichnung",
  "quantity": 1,
  "shape": "Eckig oder Rund",
  "diameter": 0,
  "length": 0,
  "width": 0,
  "height": 0,
  "polished": "Ja oder Nein",
  "polishing_price": 0,
  "coated": "Ja oder Nein",
  "coating": "Meta-S oder CrN oder CrN-RB oder Duplex Meta cax oder AlCrN oder TiN oder TiaLN oder TiCN oder Keine",
  "confidence": 0,
  "ocr_note": "kurzer Hinweis, was erkannt wurde"
}}
"""

        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_base64}",
                        },
                    ],
                }
            ],
        )

        text = response.output_text.strip()
        json_text = clean_json_text(text)
        data = json.loads(json_text)
        return normalize_ocr_result(data)

    except Exception as e:
        st.error(f"GPT-4.1 OCR fehlgeschlagen: {e}")
        st.info("Es wird auf die Demo-Erkennung zurueckgefallen.")
        return fake_ocr(uploaded_file)



def image_bytes_to_data_url(uploaded_file) -> str:
    image_bytes = uploaded_file.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    content_type = uploaded_file.type or "image/jpeg"
    return f"data:{content_type};base64,{image_base64}"


def real_part_ai_search(search_file, entries: list[Dict]) -> list[Dict]:
    """Vergleicht ein Suchfoto mit gespeicherten Bauteilfotos.

    Hinweis:
    Diese einfache Testversion nutzt GPT-4.1 Vision direkt.
    Sie ist perfekt zum Testen mit wenigen Kandidaten.
    Fuer grosse Datenmengen waere spaeter CLIP/Embeddings + Vektordatenbank besser.
    """
    if search_file is None:
        st.warning("Bitte zuerst ein Foto vom unbekannten Bauteil hochladen.")
        return []

    candidates = [e for e in entries if e.get("parts_url")]
    if not candidates:
        st.warning("Noch keine gespeicherten Bauteilbilder in der Cloud gefunden. Bitte erst Wareneingaenge mit Bildern speichern.")
        return []

    if not openai_ready():
        st.warning("OPENAI_API_KEY fehlt. Es wird die Demo-Trefferliste genutzt.")
        return [
            {
                "id": e.get("id", e.get("delivery_id", "")),
                "score": int(e.get("match", 70)),
                "reason": "Demo-Treffer, da OpenAI API Key fehlt.",
            }
            for e in candidates[:5]
        ]

    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        limited = candidates[:6]
        content = [
            {
                "type": "input_text",
                "text": f"""
Du bist ein KI-Assistent fuer Wareneingang und Bauteil-Zuordnung.

Aufgabe:
Vergleiche das erste Bild (Suchbild eines unbekannten Bauteils) mit den nachfolgenden Kandidatenbildern aus gespeicherten Wareneingaengen.

Gib NUR gueltiges JSON zurueck, kein Markdown, keine Erklaerung.

Bewerte:
- Form/Kontur
- Oberflaeche/Beschichtung
- Farbe/Glanz
- sichtbare Geometrie
- allgemeine Aehnlichkeit

JSON Schema:
{{
  "matches": [
    {{
      "id": "Lieferschein-ID aus der Kandidatenliste",
      "score": 0,
      "reason": "kurze Begruendung"
    }}
  ]
}}

Score:
0 = passt gar nicht
100 = sehr sicherer Treffer

Kandidaten-IDs:
{chr(10).join([f"- {e.get('id', e.get('delivery_id', ''))}: Kunde {e.get('customer','')}, Artikel {e.get('article_no','')}, Beschreibung {e.get('description','')}" for e in limited])}
"""
            },
            {"type": "input_text", "text": "Suchbild:"},
            {"type": "input_image", "image_url": image_bytes_to_data_url(search_file)},
        ]

        for e in limited:
            content.append({"type": "input_text", "text": f"Kandidat {e.get('id', e.get('delivery_id', ''))}:"})
            content.append({"type": "input_image", "image_url": e.get("parts_url")})

        response = client.responses.create(
            model="gpt-4.1",
            input=[{"role": "user", "content": content}],
        )

        text = response.output_text.strip()
        json_text = clean_json_text(text)
        data = json.loads(json_text)
        matches = data.get("matches", [])

        clean_matches = []
        valid_ids = {str(e.get("id", e.get("delivery_id", ""))) for e in limited}
        for m in matches:
            mid = str(m.get("id", ""))
            if mid not in valid_ids:
                continue
            clean_matches.append({
                "id": mid,
                "score": max(0, min(100, safe_int(m.get("score"), 0))),
                "reason": str(m.get("reason", "Aehnlichkeit erkannt.")),
            })

        return sorted(clean_matches, key=lambda x: x["score"], reverse=True)

    except Exception as e:
        st.error(f"Bauteil-KI fehlgeschlagen: {e}")
        st.info("Es wird eine Demo-Trefferliste angezeigt.")
        return [
            {
                "id": e.get("id", e.get("delivery_id", "")),
                "score": int(e.get("match", 70)),
                "reason": "Demo-Treffer nach Fehler in der KI-Auswertung.",
            }
            for e in candidates[:5]
        ]

def demo_entries() -> list[Dict]:
    return [
        {
            "id": "LS-2024-04578",
            "delivery_id": "LS-2024-04578",
            "date": "24.05.2024, 09:15",
            "operator": "Kevin",
            "customer": "Mustertechnik GmbH",
            "article_no": "ART-123456",
            "description": "Praezisionsteil XY",
            "quantity": 25,
            "shape": "Eckig",
            "diameter": 0.0,
            "length": 120.50,
            "width": 80.25,
            "height": 45.00,
            "polished": "Ja",
            "polishing_price": 25.00,
            "coated": "Ja",
            "coating": "AlCrN",
            "notes": "Demo-Datensatz",
            "status": "Abgeschlossen",
            "ocr_confidence": 94,
            "match": 92,
            "created_by": "demo",
            "receipt_url": "",
            "parts_url": "",
            "packaging_url": "",
        }
    ]


def upload_to_storage(uploaded_file, folder: str) -> str:
    if uploaded_file is None:
        return ""

    sb = get_supabase()
    if not sb:
        return ""

    try:
        suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
        filename = f"{folder}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{suffix}"
        data = uploaded_file.getvalue()

        content_type = uploaded_file.type or "image/jpeg"
        sb.storage.from_(BUCKET_NAME).upload(
            filename,
            data,
            {"content-type": content_type, "upsert": "false"},
        )

        public_url = sb.storage.from_(BUCKET_NAME).get_public_url(filename)
        return public_url
    except Exception as e:
        st.error(f"Bild konnte nicht in Supabase Storage gespeichert werden: {e}")
        return ""


def load_entries_from_cloud() -> list[Dict]:
    sb = get_supabase()
    if not sb:
        return demo_entries()
    try:
        res = sb.table("wareneingaenge").select("*").order("created_at", desc=True).execute()
        data = res.data or []
        return data if data else demo_entries()
    except Exception as e:
        st.error(f"Cloud-Daten konnten nicht geladen werden: {e}")
        return demo_entries()


def save_entry_to_cloud(entry: Dict) -> bool:
    sb = get_supabase()
    if not sb:
        st.error("Supabase ist nicht eingerichtet.")
        return False
    try:
        sb.table("wareneingaenge").insert(entry).execute()
        return True
    except Exception as e:
        st.error(f"Speichern in Supabase fehlgeschlagen: {e}")
        return False


def init_data() -> None:
    if "user" not in st.session_state:
        st.session_state.user = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "ai_result" not in st.session_state:
        st.session_state.ai_result = None


def current_entries() -> list[Dict]:
    if "entries_cache" not in st.session_state:
        st.session_state.entries_cache = load_entries_from_cloud()
    return st.session_state.entries_cache


def refresh_entries() -> None:
    st.session_state.entries_cache = load_entries_from_cloud()


def hero() -> None:
    b64 = base64.b64encode(img_bytes("wareneingang.png")).decode("utf-8")
    st.markdown(f"""
    <div class="hero">
      <img src="data:image/png;base64,{b64}" />
      <div class="hero-text">
        <h1>Digitaler Wareneingang mit GPT-4.1 OCR</h1>
        <p>Lieferschein fotografieren, wichtige Daten automatisch erkennen und Bilder in Supabase speichern.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)


def metrics() -> None:
    entries = current_entries()
    total_qty = sum(int(e.get("quantity", 0)) for e in entries)
    open_count = sum(1 for e in entries if e.get("status") != "Abgeschlossen")
    avg_ocr = round(sum(e.get("ocr_confidence", 0) for e in entries) / max(len(entries), 1))

    cols = st.columns(4)
    data = [
        ("Wareneingaenge", len(entries), "aus Cloud geladen"),
        ("Bauteile", total_qty, "Stueck gesamt"),
        ("Offen", open_count, "zu pruefen"),
        ("OCR", f"{avg_ocr}%", "GPT-4.1 Erkennung"),
    ]
    for col, (label, value, hint) in zip(cols, data):
        col.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-hint">{hint}</div></div>', unsafe_allow_html=True)


def show_image_or_placeholder(url: str, placeholder_name: str, caption: str) -> None:
    if url:
        st.image(url, caption=caption, use_container_width=True)
    else:
        st.image(ASSETS / placeholder_name, caption=caption, use_container_width=True)


def entry_card(e: Dict, compact: bool = False) -> None:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    top = st.columns([2, 1])
    top[0].markdown(f"### {e.get('id', e.get('delivery_id', '-'))}")
    top[0].markdown(f"**{e.get('customer', '-')}** Â· {e.get('date', '-')} Â· Bediener: **{e.get('operator','-')}**")
    top[1].markdown(status_html(e.get("status", "-")), unsafe_allow_html=True)
    top[1].markdown(ai_html(f"OCR {e.get('ocr_confidence',0)}%"), unsafe_allow_html=True)

    c = st.columns(6)
    c[0].metric("Artikel", e.get("article_no", "-"))
    c[1].metric("Menge", f"{e.get('quantity', 0)} Stk.")
    c[2].metric("Form", e.get("shape", "Eckig"))
    c[3].metric("Masse", entry_dimensions(e))
    c[4].metric("Polieren", f"{e.get('polished', 'Nein')} / {float(e.get('polishing_price', 0)):.2f} EUR")
    c[5].metric("Beschichtung", e.get("coating", "-"))

    if not compact:
        i1, i2, i3 = st.columns(3)
        with i1:
            show_image_or_placeholder(e.get("receipt_url", ""), "demo_lieferschein.png", "Lieferschein")
        with i2:
            show_image_or_placeholder(e.get("parts_url", ""), "demo_bauteile.png", "Bauteile")
        with i3:
            show_image_or_placeholder(e.get("packaging_url", ""), "demo_verpackung.png", "Verpackung")

    st.markdown('</div>', unsafe_allow_html=True)


def dashboard() -> None:
    hero()
    metrics()
    st.write("")
    if st.button("Cloud-Daten neu laden"):
        refresh_entries()
        st.rerun()

    left, right = st.columns([1.2, .8])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Letzte Wareneingaenge")
        for e in current_entries()[:5]:
            entry_card(e, compact=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Aktiv in dieser Version")
        st.markdown("""
        - Login per Supabase Auth
        - Wareneingaenge in Supabase speichern
        - Lieferschein-, Bauteil- und Verpackungsbilder in Supabase Storage
        - GPT-4.1 liest den Lieferschein aus
        - WISO Copy/Paste

        **Wichtig:** KI-Ergebnisse immer gegenpruefen.
        """)
        if openai_ready():
            st.success("OPENAI_API_KEY ist aktiv. GPT-4.1 OCR kann genutzt werden.")
        else:
            st.warning("OPENAI_API_KEY fehlt. App nutzt Demo-Erkennung.")
        st.image(ASSETS / "slide_1.png", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


def capture() -> None:
    st.markdown("## Neuen Wareneingang erfassen")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 1. Pflichtfotos")
    a, b, c = st.columns(3)
    receipt = a.file_uploader("Lieferschein fotografieren", type=["png", "jpg", "jpeg"], key="receipt")
    parts = b.file_uploader("Bauteile fotografieren", type=["png", "jpg", "jpeg"], key="parts")
    packaging = c.file_uploader("Verpackung fotografieren", type=["png", "jpg", "jpeg"], key="packaging")

    p1, p2, p3 = st.columns(3)
    p1.image(receipt if receipt else ASSETS / "demo_lieferschein.png", caption="Lieferschein", use_container_width=True)
    p2.image(parts if parts else ASSETS / "demo_bauteile.png", caption="Bauteile", use_container_width=True)
    p3.image(packaging if packaging else ASSETS / "demo_verpackung.png", caption="Verpackung", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ai-box">', unsafe_allow_html=True)
    st.markdown("### 2. GPT-4.1 Lieferschein-Erkennung")
    st.write("GPT-4.1 liest Kunde, Artikelnummer, Artikelbezeichnung, Menge, MaÃe und Beschichtung aus dem Lieferschein.")

    if st.button("GPT-4.1: Lieferschein auslesen", use_container_width=True):
        with st.spinner("GPT-4.1 liest den Lieferschein aus..."):
            st.session_state.ai_result = real_ocr_lieferschein(receipt)
        st.success("Auslesung abgeschlossen. Bitte unten gegenpruefen.")

    ai = st.session_state.get("ai_result")
    if ai:
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Sicherheit", f"{ai.get('confidence', 0)}%")
        x2.metric("Lieferschein", ai.get("id", "-"))
        x3.metric("Kunde", ai.get("customer", "-"))
        x4.metric("Artikel", ai.get("article_no", "-"))
        if ai.get("ocr_note"):
            st.info(ai["ocr_note"])
    st.markdown('</div>', unsafe_allow_html=True)

    d = ai or fake_ocr(None)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 3. Daten pruefen und speichern")

    col1, col2, col3 = st.columns(3)

    with col1:
        delivery_id = st.text_input("Lieferscheinnummer", value=d["id"])
        customer = st.text_input("Kunde", value=d["customer"])
        article_no = st.text_input("Artikelnummer", value=d["article_no"])
        description = st.text_input("Artikelbezeichnung", value=d["description"])

    with col2:
        quantity = st.number_input("Menge", min_value=1, value=int(d["quantity"]), step=1)
        shape = st.radio("Bauteilform", ["Eckig", "Rund"], index=0 if d.get("shape") == "Eckig" else 1, horizontal=True)

        if shape == "Rund":
            diameter = st.number_input("Durchmesser (mm)", min_value=0.0, value=float(d.get("diameter", 0.0)), step=0.1)
            length = st.number_input("Laenge (mm)", min_value=0.0, value=float(d.get("length", 0.0)), step=0.1)
            width = 0.0
            height = 0.0
        else:
            diameter = 0.0
            length = st.number_input("Laenge (mm)", min_value=0.0, value=float(d.get("length", 0.0)), step=0.1)
            width = st.number_input("Breite (mm)", min_value=0.0, value=float(d.get("width", 0.0)), step=0.1)
            height = st.number_input("Hoehe (mm)", min_value=0.0, value=float(d.get("height", 0.0)), step=0.1)

    with col3:
        polished = st.radio("Poliert?", ["Ja", "Nein"], index=0 if d.get("polished") == "Ja" else 1, horizontal=True)
        polishing_price = st.number_input("Preis Polieren (EUR)", min_value=0.0, value=float(d.get("polishing_price", 0.0)), step=1.0) if polished == "Ja" else 0.0
        coated = st.radio("Beschichtet?", ["Ja", "Nein"], index=0 if d.get("coated") == "Ja" else 1, horizontal=True)

        if coated == "Ja":
            coating_options = COATINGS[:-1]
            default_coating = d.get("coating", "AlCrN")
            index = coating_options.index(default_coating) if default_coating in coating_options else 0
            coating = st.selectbox("Beschichtung", coating_options, index=index)
        else:
            coating = "Keine"

    notes = st.text_area("Hinweise", value="Daten wurden per GPT-4.1 vorbereitet und vom Mitarbeiter geprueft.")
    operator = st.selectbox("Bediener auswaehlen", USERS, index=0)

    missing = []
    if receipt is None:
        missing.append("Lieferschein")
    if parts is None:
        missing.append("Bauteile")
    if packaging is None:
        missing.append("Verpackung")
    if missing:
        st.warning("Noch fehlende Pflichtfotos: " + ", ".join(missing))

    if st.button("In Cloud speichern", use_container_width=True):
        user_email = st.session_state.user.email if st.session_state.user else "unbekannt"

        receipt_url = upload_to_storage(receipt, "lieferscheine")
        parts_url = upload_to_storage(parts, "bauteile")
        packaging_url = upload_to_storage(packaging, "verpackung")

        entry = {
            "delivery_id": delivery_id,
            "id": delivery_id,
            "date": datetime.now().strftime("%d.%m.%Y, %H:%M"),
            "operator": operator,
            "customer": customer,
            "article_no": article_no,
            "description": description,
            "quantity": int(quantity),
            "shape": shape,
            "diameter": float(diameter),
            "length": float(length),
            "width": float(width),
            "height": float(height),
            "polished": polished,
            "polishing_price": float(polishing_price),
            "coated": coated,
            "coating": coating,
            "notes": notes,
            "status": "Gespeichert",
            "ocr_confidence": int(d.get("confidence", 0)),
            "match": 92,
            "created_by": user_email,
            "receipt_url": receipt_url,
            "parts_url": parts_url,
            "packaging_url": packaging_url,
        }

        if save_entry_to_cloud(entry):
            st.session_state.ai_result = None
            refresh_entries()
            st.success(f"Wareneingang {delivery_id} wurde in der Cloud gespeichert.")
    st.markdown('</div>', unsafe_allow_html=True)


def archive() -> None:
    st.markdown("## Archiv")
    q = st.text_input("Suche nach Kunde, Lieferschein, Artikelnummer oder Bediener")
    entries = current_entries()
    if q:
        entries = [e for e in entries if q.lower() in " ".join(map(str, e.values())).lower()]
    for e in entries:
        entry_card(e)


def wiso_text(e: Dict) -> str:
    return "\t".join([
        str(e.get("id", e.get("delivery_id", ""))),
        str(e.get("date", "")),
        str(e.get("operator", "-")),
        str(e.get("customer", "")),
        str(e.get("article_no", "")),
        str(e.get("description", "")),
        str(e.get("quantity", "")),
        str(e.get("shape", "Eckig")),
        entry_dimensions(e),
        str(e.get("polished", "")),
        f"{float(e.get('polishing_price', 0)):.2f}",
        str(e.get("coated", "")),
        str(e.get("coating", "")),
        str(e.get("notes", "")),
    ])


def office() -> None:
    st.markdown("## Buero / WISO")

    rows = []
    for e in current_entries():
        rows.append({
            "Lieferschein": e.get("id", e.get("delivery_id", "")),
            "Datum": e.get("date", ""),
            "Bediener": e.get("operator", "-"),
            "Kunde": e.get("customer", ""),
            "Artikelnummer": e.get("article_no", ""),
            "Artikelbezeichnung": e.get("description", ""),
            "Menge": e.get("quantity", 0),
            "Form": e.get("shape", "Eckig"),
            "Masse": entry_dimensions(e),
            "Poliert": e.get("polished", "Nein"),
            "Polierpreis": f"{float(e.get('polishing_price', 0)):.2f} EUR",
            "Beschichtet": e.get("coated", "Nein"),
            "Beschichtung": e.get("coating", "Keine"),
            "OCR": f"{e.get('ocr_confidence', 0)}%",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    entries = current_entries()
    selected = st.selectbox("Datensatz fuer WISO auswaehlen", [e.get("id", e.get("delivery_id", "")) for e in entries])
    entry = next(e for e in entries if e.get("id", e.get("delivery_id", "")) == selected)

    st.code(wiso_text(entry), language="text")
    st.download_button("CSV exportieren", data=df.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name="wareneingang_wiso.csv", mime="text/csv")


def ai_search() -> None:
    st.markdown("## KI-Suche: Bauteilfoto zu Lieferschein zuordnen")
    st.markdown(
        "Lade ein Foto von einem unbekannten Bauteil hoch. GPT-4.1 vergleicht es mit den gespeicherten Bauteilbildern aus der Cloud."
    )

    left, right = st.columns([0.85, 1.15])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        uploaded = st.file_uploader("Foto vom unbekannten Bauteil", type=["png", "jpg", "jpeg"], key="ai_search")
        st.image(uploaded if uploaded else ASSETS / "demo_suchteil.png", caption="Suchbild", use_container_width=True)
        start = st.button("GPT-4.1 Bauteil-Zuordnung starten", use_container_width=True)
        st.markdown(
            """
            **KI prÃ¼ft:**  
            - Form und Kontur  
            - OberflÃ¤che / Beschichtung  
            - Farbe und Glanz  
            - Ãhnlichkeit zu gespeicherten Bauteilfotos  
            """
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        entries = current_entries()

        if start:
            with st.spinner("GPT-4.1 vergleicht das Bauteilfoto mit gespeicherten WareneingÃ¤ngen..."):
                st.session_state.part_ai_matches = real_part_ai_search(uploaded, entries)

        matches = st.session_state.get("part_ai_matches", [])

        if not matches:
            st.info("Noch keine KI-Suche gestartet. Lade links ein Bauteilfoto hoch und starte die Suche.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        st.markdown("### Trefferliste")

        entry_by_id = {str(e.get("id", e.get("delivery_id", ""))): e for e in entries}

        for i, match in enumerate(matches, start=1):
            entry = entry_by_id.get(str(match["id"]))
            if not entry:
                continue

            score = int(match.get("score", 0))
            if score >= 85:
                st.success(f"Treffer {i}: {entry.get('id', entry.get('delivery_id', ''))} Â· {entry.get('customer', '')} Â· {score}%")
            elif score >= 65:
                st.warning(f"Treffer {i}: {entry.get('id', entry.get('delivery_id', ''))} Â· {entry.get('customer', '')} Â· {score}%")
            else:
                st.info(f"Treffer {i}: {entry.get('id', entry.get('delivery_id', ''))} Â· {entry.get('customer', '')} Â· {score}%")

            st.write(f"**KI-BegrÃ¼ndung:** {match.get('reason', '')}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Artikel", entry.get("article_no", "-"))
            c2.metric("Menge", f"{entry.get('quantity', 0)} Stk.")
            c3.metric("Beschichtung", entry.get("coating", "-"))

            img1, img2, img3 = st.columns(3)
            with img1:
                show_image_or_placeholder(entry.get("receipt_url", ""), "demo_lieferschein.png", "Lieferschein")
            with img2:
                show_image_or_placeholder(entry.get("parts_url", ""), "demo_bauteile.png", "Gespeichertes Bauteilfoto")
            with img3:
                show_image_or_placeholder(entry.get("packaging_url", ""), "demo_verpackung.png", "Verpackung")

            st.markdown("---")

        st.markdown('</div>', unsafe_allow_html=True)

def setup_help() -> None:
    st.markdown("## Supabase + OpenAI Setup")

    st.markdown("### 1. Streamlit Secrets")
    st.code("""
SUPABASE_URL = "https://DEIN-PROJEKT.supabase.co"
SUPABASE_ANON_KEY = "DEIN-ANON-KEY"
OPENAI_API_KEY = "sk-..."
    """, language="toml")

    st.markdown("### 2. Supabase SQL")
    st.code("""
create table if not exists wareneingaenge (
  uuid uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default now(),
  delivery_id text,
  id text,
  date text,
  operator text,
  customer text,
  article_no text,
  description text,
  quantity int,
  shape text,
  diameter numeric,
  length numeric,
  width numeric,
  height numeric,
  polished text,
  polishing_price numeric,
  coated text,
  coating text,
  notes text,
  status text,
  ocr_confidence int,
  match int,
  created_by text,
  receipt_url text,
  parts_url text,
  packaging_url text
);

alter table wareneingaenge enable row level security;

drop policy if exists "allow authenticated read" on wareneingaenge;
drop policy if exists "allow authenticated insert" on wareneingaenge;

create policy "allow authenticated read"
on wareneingaenge for select
to authenticated
using (true);

create policy "allow authenticated insert"
on wareneingaenge for insert
to authenticated
with check (true);
    """, language="sql")

    st.markdown("### 3. Storage Bucket")
    st.markdown(f"Bucket Name: **{BUCKET_NAME}**")
    st.code("""
create policy "allow upload"
on storage.objects
for insert
to authenticated
with check (bucket_id = 'wareneingang-bilder');

create policy "allow read"
on storage.objects
for select
to public
using (bucket_id = 'wareneingang-bilder');
    """, language="sql")

    st.markdown("### Status")
    st.write("Supabase:", "â verbunden" if cloud_ready() else "â fehlt")
    st.write("OpenAI:", "â API Key aktiv" if openai_ready() else "â OPENAI_API_KEY fehlt")


def main() -> None:
    ensure_assets()
    css()
    init_data()

    if st.session_state.user is None:
        login_screen()
        return

    st.sidebar.image(ASSETS / "wareneingang.png", use_container_width=True)
    st.sidebar.markdown("### Pondruff / WE")
    st.sidebar.success(f"Eingeloggt: {st.session_state.user.email}")
    if st.sidebar.button("Abmelden"):
        logout()
        st.rerun()

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Neuer Wareneingang", "Archiv", "Buero / WISO", "KI-Suche", "Setup"],
    )

    if page == "Dashboard":
        dashboard()
    elif page == "Neuer Wareneingang":
        capture()
    elif page == "Archiv":
        archive()
    elif page == "Buero / WISO":
        office()
    elif page == "KI-Suche":
        ai_search()
    else:
        setup_help()


if __name__ == "__main__":
    main()
