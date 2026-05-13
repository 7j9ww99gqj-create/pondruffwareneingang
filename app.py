from __future__ import annotations

import base64
import io
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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

PRICE_BASE_COATING_MULTIPLIER = 1.2
PRICE_EXCEL_PI = 3.141
PRICE_COATING_FACTORS = {
    "Duplex Meta-VA": 1.40,
    "Duplex Meta-CAX": 1.50,
    "Meta-S": 1.40,
    "AlCrN": 1.40,
    "TiCN": 1.10,
    "TiN": 1.10,
    "CrN": 1.10,
    "CrN-RB": 1.40,
    "CrN-DLC": 1.60,
    "TiaLN": 1.40,
}
PRICE_COATINGS = list(PRICE_COATING_FACTORS.keys())
PRICE_TABLE = [
    [1000, 2.55645940598109], [2000, 1.27822970299055],
    [3000, 0.971454574272815], [6000, 0.843631603973761],
    [10000, 0.81806700991395], [15000, 0.766937821794328],
    [20000, 0.715808633674706], [25000, 0.664679445555084],
    [30000, 0.613550257435462], [40000, 0.511291881196219],
    [50000, 0.460162693076597], [60000, 0.429485180204824],
    [70000, 0.409033504956975], [80000, 0.342565560401466],
    [150000, 0.32722680396558], [200000, 0.306775128717731],
    [250000, 0.301662209905769], [300000, 0.296549291093807],
    [400000, 0.291436372281845], [500000, 0.28121053465792],
    [600000, 0.270984697033996], [700000, 0.265871778222034],
    [800000, 0.245420102974185], [900000, 0.235194265350261],
    [950000, 0.230081346538298], [1000000, 0.214742590102412],
    [1100000, 0.199403833666525], [1200000, 0.189177996042601],
    [1300000, 0.178952158418676], [1400000, 0.168726320794752],
    [1500000, 0.16361340198279], [1600000, 0.153387564358866],
    [1700000, 0.143161726734941], [1800000, 0.138048807922979],
    [1900000, 0.132935889111017], [2000000, 0.11759713267513],
    [2500000, 0.102258376239244], [3000000, 0.0971454574272815],
    [3500000, 0.0869196198033572], [4000000, 0.081806700991395],
    [4500000, 0.0766937821794328], [5000000, 0.0715808633674706],
    [6500000, 0.0664679445555084], [7500000, 0.0613550257435462],
    [10000000, 0.056242106931584], [35000000, 0.0511291881196219],
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
        .stTextInput [data-baseweb="input"],
        .stNumberInput [data-baseweb="input"],
        .stTextArea [data-baseweb="textarea"],
        .stSelectbox [data-baseweb="select"] {
            background:#111821!important;
            border:1px solid rgba(255,255,255,.22)!important;
            border-radius:14px!important;
            color:#f7fafc!important;
        }
        .stTextInput [data-baseweb="input"] > div,
        .stNumberInput [data-baseweb="input"] > div,
        .stTextArea [data-baseweb="textarea"] > div,
        .stSelectbox [data-baseweb="select"] > div {
            background:#111821!important;
            color:#f7fafc!important;
            border-color:rgba(255,255,255,.22)!important;
            border-radius:14px!important;
        }
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox [data-baseweb="select"] *,
        [data-baseweb="menu"] * {
            color:#f7fafc!important;
            -webkit-text-fill-color:#f7fafc!important;
        }
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            background:#111821!important;
            caret-color:#ffffff!important;
        }
        .stTextInput input::placeholder,
        .stNumberInput input::placeholder,
        .stTextArea textarea::placeholder {
            color:#95a3b5!important;
            -webkit-text-fill-color:#95a3b5!important;
            opacity:1!important;
        }
        .stTextInput input:disabled,
        .stNumberInput input:disabled,
        .stTextArea textarea:disabled,
        .stSelectbox [aria-disabled="true"] {
            background:#18212b!important;
            color:#d8dee8!important;
            -webkit-text-fill-color:#d8dee8!important;
            opacity:1!important;
        }
        .stTextInput input:-webkit-autofill,
        .stNumberInput input:-webkit-autofill {
            box-shadow:0 0 0 1000px #111821 inset!important;
            -webkit-text-fill-color:#f7fafc!important;
            caret-color:#ffffff!important;
        }
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {
            background:#111821!important;
            color:#f7fafc!important;
        }
        button[aria-label="Increment"],
        button[aria-label="Decrement"] {
            background:#1b2632!important;
            color:#f7fafc!important;
        }
        [data-testid="stFileUploader"] section {
            background:#111821!important;
            border-color:rgba(255,255,255,.22)!important;
            color:#f7fafc!important;
        }
        [data-testid="stFileUploader"] section *,
        [data-testid="stFileUploader"] label {
            color:#f7fafc!important;
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


def price_default_factor(coating: str) -> float:
    return float(PRICE_COATING_FACTORS.get(coating, 1.0))


def normalize_price_coating(value: str) -> str:
    if not value:
        return "TiCN"

    v = str(value).strip().lower()
    mapping = {
        "meta-s": "Meta-S",
        "metas": "Meta-S",
        "crn": "CrN",
        "crn-rb": "CrN-RB",
        "crn rb": "CrN-RB",
        "crn-dlc": "CrN-DLC",
        "crn dlc": "CrN-DLC",
        "duplex meta-va": "Duplex Meta-VA",
        "duplex meta va": "Duplex Meta-VA",
        "duplex meta-cax": "Duplex Meta-CAX",
        "duplex meta cax": "Duplex Meta-CAX",
        "duplex cax": "Duplex Meta-CAX",
        "alcrn": "AlCrN",
        "tin": "TiN",
        "ticn": "TiCN",
        "tialn": "TiaLN",
    }
    return mapping.get(v, "TiCN")


def price_lookup_rate(volume: float) -> float:
    if volume <= 0:
        return 0.0
    rate = PRICE_TABLE[0][1]
    for threshold, candidate in PRICE_TABLE:
        if volume >= threshold:
            rate = candidate
        else:
            break
    return float(rate)


def money(value: float) -> float:
    return round(float(value or 0.0) + 1e-12, 2)


def normalize_price_customer(value: str) -> str:
    customer = str(value or "").strip()
    if "pondruff" in customer.lower():
        return ""
    return customer


def blank_price_position(shape: str = "Eckig") -> Dict:
    return {
        "description": "",
        "article_no": "",
        "position_no": "",
        "order_no": "",
        "cost_center": "",
        "purchase_order": "",
        "quantity": 1,
        "shape": shape,
        "coating": "TiCN",
        "factor": price_default_factor("TiCN"),
        "diameter": 0.0,
        "length": 0.0,
        "width": 0.0,
        "height": 0.0,
        "discount": 0.0,
        "note": "",
        "source": "manuell",
    }


def normalize_price_position(data: Dict) -> Dict:
    pos = blank_price_position("Rund" if str(data.get("shape", "")).strip().lower() in ["rund", "round", "zylindrisch"] else "Eckig")
    coating = normalize_price_coating(str(data.get("coating") or data.get("beschichtung") or pos["coating"]))
    pos["description"] = str(data.get("description") or data.get("article_description") or data.get("artikelbezeichnung") or "").strip()
    pos["article_no"] = str(data.get("article_no") or data.get("artikelnummer") or "").strip()
    pos["position_no"] = str(data.get("position_no") or data.get("positionsnummer") or data.get("pos_nr") or data.get("pos") or "").strip()
    pos["order_no"] = str(data.get("order_no") or data.get("auftragsnummer") or data.get("auftrag") or "").strip()
    pos["cost_center"] = str(data.get("cost_center") or data.get("kostenstelle") or "").strip()
    pos["purchase_order"] = str(data.get("purchase_order") or data.get("bestellnummer") or data.get("bestell_nr") or "").strip()
    pos["quantity"] = safe_int(data.get("quantity") or data.get("menge"), 1)
    pos["shape"] = "Rund" if pos["shape"] == "Rund" else "Eckig"
    pos["coating"] = coating
    pos["factor"] = safe_float(data.get("factor") or data.get("r4_factor"), price_default_factor(coating))
    pos["diameter"] = safe_float(data.get("diameter") or data.get("durchmesser"), 0.0)
    pos["length"] = safe_float(data.get("length") or data.get("laenge") or data.get("länge"), 0.0)
    pos["width"] = safe_float(data.get("width") or data.get("breite"), 0.0)
    pos["height"] = safe_float(data.get("height") or data.get("hoehe") or data.get("höhe"), 0.0)
    pos["discount"] = max(0.0, min(100.0, safe_float(data.get("discount") or data.get("rabatt"), 0.0)))
    pos["note"] = str(data.get("note") or data.get("hinweis") or data.get("notes") or "").strip()
    pos["source"] = str(data.get("source") or "ki").strip()
    if pos["shape"] == "Rund":
        pos["width"] = 0.0
        pos["height"] = 0.0
    else:
        pos["diameter"] = 0.0
    return pos


def calc_price_position(pos: Dict) -> Dict:
    coating = normalize_price_coating(pos.get("coating", "TiCN"))
    factor = safe_float(pos.get("factor"), price_default_factor(coating))
    quantity = safe_int(pos.get("quantity"), 1)
    discount = max(0.0, min(100.0, safe_float(pos.get("discount"), 0.0)))
    shape = "Rund" if str(pos.get("shape", "Eckig")).lower() == "rund" else "Eckig"

    if shape == "Rund":
        diameter = safe_float(pos.get("diameter"), 0.0)
        length = safe_float(pos.get("length"), 0.0)
        volume = (diameter * diameter) * PRICE_EXCEL_PI / 4 * length
    else:
        length = safe_float(pos.get("length"), 0.0)
        width = safe_float(pos.get("width"), 0.0)
        height = safe_float(pos.get("height"), 0.0)
        volume = length * width * height

    multiplier = 1.0 if coating == "TiN" else PRICE_BASE_COATING_MULTIPLIER
    unit_price = price_lookup_rate(volume) * volume / 1000 * multiplier * factor if volume > 0 and factor > 0 else 0.0
    normal_total = money(unit_price * quantity)
    final_total = money(normal_total * (1 - discount / 100))
    return {
        "volume": volume,
        "unit_price": money(unit_price),
        "normal_total": normal_total,
        "final_total": final_total,
        "discount_amount": money(normal_total - final_total),
    }


def normalize_price_ocr_result(data: Dict) -> Dict:
    positions = data.get("positions") or data.get("items") or []
    clean_positions = [normalize_price_position(pos) for pos in positions if isinstance(pos, dict)]
    return {
        "delivery_id": str(data.get("delivery_id") or data.get("id") or "").strip(),
        "customer": normalize_price_customer(str(data.get("customer") or "")),
        "project": str(data.get("project") or data.get("description") or "").strip(),
        "purchase_order": str(data.get("purchase_order") or data.get("bestellnummer") or data.get("bestell_nr") or "").strip(),
        "confidence": max(0, min(100, safe_int(data.get("confidence"), 80))),
        "ocr_note": str(data.get("ocr_note") or data.get("note") or "GPT-4.1 hat die Positionen fuer den Preisrechner vorbereitet.").strip(),
        "positions": clean_positions,
    }


def price_dimension_text(pos: Dict) -> str:
    if pos.get("shape") == "Rund":
        diameter = safe_float(pos.get("diameter"), 0.0)
        length = safe_float(pos.get("length"), 0.0)
        return f"Ø {diameter:g} x {length:g} mm"

    length = safe_float(pos.get("length"), 0.0)
    width = safe_float(pos.get("width"), 0.0)
    height = safe_float(pos.get("height"), 0.0)
    return f"{length:g} x {width:g} x {height:g} mm"


def wiso_compact_dimension_text(pos: Dict) -> str:
    if pos.get("shape") == "Rund":
        diameter = safe_float(pos.get("diameter"), 0.0)
        length = safe_float(pos.get("length"), 0.0)
        return f"Ø{diameter:g}x{length:g}mm"

    length = safe_float(pos.get("length"), 0.0)
    width = safe_float(pos.get("width"), 0.0)
    height = safe_float(pos.get("height"), 0.0)
    return f"{length:g}x{width:g}x{height:g}mm"


def wiso_short_description_text(pos: Dict) -> str:
    description = str(pos.get("description") or "Beschichtung").strip()
    description = re.sub(r"^pondruck?f[-\s]*[a-z0-9]+\s+beschichtung\s*", "", description, flags=re.IGNORECASE)
    description = re.split(r",?\s*material\s*:", description, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    description = re.split(r",?\s*ma[ßs]e\s*:", description, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return description or "Beschichtung"


def money_de(value: float) -> str:
    return f"{money(value):.2f}".replace(".", ",")


def wiso_description_for_price_position(pos: Dict, is_last: bool, global_purchase_order: str = "") -> str:
    description = wiso_short_description_text(pos)
    coating = normalize_price_coating(pos.get("coating", "TiCN"))
    lines = [f"{description} {wiso_compact_dimension_text(pos)} {coating} beschichtet."]

    if pos.get("order_no"):
        lines.append(f"Auftrags.-Nr. {pos['order_no']}")
    if pos.get("cost_center"):
        lines.append(f"Kostenstelle: {pos['cost_center']}")

    purchase_order = (pos.get("purchase_order") or global_purchase_order) if is_last else ""
    if purchase_order:
        lines.append(f"Ihre Bestell.-Nr. {purchase_order}")

    return "\n".join(lines)


def wiso_import_description_for_position(pos: Dict, is_last: bool, global_purchase_order: str = "") -> str:
    description = wiso_short_description_text(pos)
    coating = normalize_price_coating(pos.get("coating", "TiCN"))
    lines = [f"{description} {wiso_compact_dimension_text(pos)} {coating} beschichtet."]

    if pos.get("order_no"):
        lines.append(f"Ihre Auftrags.-Nr. {pos['order_no']}")
    if pos.get("cost_center"):
        lines.append(f"Kostenstelle: {pos['cost_center']}")

    purchase_order = (pos.get("purchase_order") or global_purchase_order) if is_last else ""
    if purchase_order:
        lines.append(f"Ihre Bestell.-Nr. {purchase_order}")

    return "\n".join(lines)


def build_wiso_price_order(customer: str, project: str, positions: list[Dict], global_purchase_order: str = "") -> Dict:
    clean_positions = [normalize_price_position(pos) for pos in positions]
    rows = []

    for idx, pos in enumerate(clean_positions, start=1):
        result = calc_price_position(pos)
        quantity = safe_int(pos.get("quantity"), 1)
        single_after_discount = money(result["final_total"] / max(quantity, 1))
        rows.append(
            {
                "Pos.": f"{idx:02d}",
                "Menge": quantity,
                "Artikel-Nr.": pos.get("article_no", ""),
                "Einheit": "",
                "Beschreibung": wiso_description_for_price_position(
                    pos,
                    is_last=idx == len(clean_positions),
                    global_purchase_order=global_purchase_order,
                ),
                "Liefertermin": "",
                "Listenpreis": f"{result['unit_price']:.2f}",
                "Rabatt (%)": f"{safe_float(pos.get('discount'), 0.0):g}",
                "Einzelpreis": f"{single_after_discount:.2f}",
                "Gesamtpreis": f"{result['final_total']:.2f}",
                "_wiso_import_description": wiso_import_description_for_position(
                    pos,
                    is_last=idx == len(clean_positions),
                    global_purchase_order=global_purchase_order,
                ),
            }
        )

    total = money(sum(float(row["Gesamtpreis"]) for row in rows))
    order_name = project or f"Preisauftrag {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    return {
        "id": f"PREIS-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().strftime("%d.%m.%Y, %H:%M"),
        "customer": customer,
        "project": project,
        "purchase_order": global_purchase_order,
        "name": order_name,
        "total": total,
        "rows": rows,
    }


def wiso_order_tsv(order: Dict) -> str:
    headers = ["Pos.", "Menge", "Artikel-Nr.", "Einheit", "Beschreibung", "Liefertermin", "Listenpreis", "Rabatt (%)", "Einzelpreis", "Gesamtpreis"]
    lines = ["\t".join(headers)]
    for row in order.get("rows", []):
        lines.append("\t".join(str(row.get(header, "")) for header in headers))
    return "\n".join(lines)


def tsv_cell(value) -> str:
    text = str(value if value is not None else "").replace("\r\n", "\n").replace("\r", "\n")
    if any(ch in text for ch in ['\t', '\n', '"']):
        return '"' + text.replace('"', '""') + '"'
    return text


def wiso_clipboard_columns() -> list[str]:
    return ["Menge", "Artikel-Nr.", "Einheit", "Beschreibung", "Liefertermin", "Listenpreis", "Rabatt (%)", "Einzelpreis", "Gesamtpreis"]


def wiso_clipboard_value(row: Dict, column: str) -> str:
    value = row.get(column, "")
    if column in ["Listenpreis", "Einzelpreis", "Gesamtpreis"]:
        return str(value).replace(".", ",")
    return str(value if value is not None else "")


def wiso_clipboard_tsv(order: Dict) -> str:
    columns = wiso_clipboard_columns()
    lines = []
    for row in order.get("rows", []):
        values = [tsv_cell(wiso_clipboard_value(row, column)) for column in columns]
        lines.append("\t".join(values))
    return "\r\n".join(lines)


def wiso_clipboard_plain_tsv(order: Dict) -> str:
    columns = wiso_clipboard_columns()
    lines = []
    for row in order.get("rows", []):
        values = []
        for column in columns:
            value = wiso_clipboard_value(row, column)
            if column == "Beschreibung":
                value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " / ")
            values.append(value.replace("\t", " "))
        lines.append("\t".join(values))
    return "\r\n".join(lines)


def wiso_clipboard_html(order: Dict) -> str:
    columns = ["Menge", "Artikel-Nr.", "Einheit", "Beschreibung", "Liefertermin", "Listenpreis", "Rabatt (%)", "Einzelpreis", "Gesamtpreis"]
    rows = []
    for row in order.get("rows", []):
        cells = []
        for column in columns:
            value = html.escape(wiso_clipboard_value(row, column))
            if column == "Beschreibung":
                value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
            cells.append(f"<td>{value}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def wiso_copy_button(order: Dict, key: str) -> None:
    tsv_payload = json.dumps(wiso_clipboard_tsv(order))
    plain_payload = json.dumps(wiso_clipboard_plain_tsv(order))
    html_payload = json.dumps(wiso_clipboard_html(order))
    components.html(
        f"""
        <button id="copy-{key}" style="
          width:100%;
          min-height:44px;
          border-radius:14px;
          border:1px solid rgba(229,9,9,.5);
          background:linear-gradient(180deg,#f01212,#b80000);
          color:white;
          font-weight:800;
          cursor:pointer;
        ">WISO Copy</button>
        <script>
        const btn = document.getElementById("copy-{key}");
        const text = {tsv_payload};
        const plainText = {plain_payload};
        const htmlText = {html_payload};
        btn.addEventListener("click", async () => {{
          try {{
            if (window.ClipboardItem) {{
              await navigator.clipboard.write([
                new ClipboardItem({{
                  "text/html": new Blob([htmlText], {{ type: "text/html" }}),
                  "text/plain": new Blob([text], {{ type: "text/plain" }})
                }})
              ]);
            }} else {{
              await navigator.clipboard.writeText(text);
            }}
            btn.textContent = "WISO Daten kopiert";
          }} catch (err) {{
            const area = document.createElement("textarea");
            area.value = plainText;
            document.body.appendChild(area);
            area.select();
            document.execCommand("copy");
            area.remove();
            btn.textContent = "WISO Daten kopiert";
          }}
        }});
        </script>
        """,
        height=56,
    )


WISO_API_BASE_URL = "https://api.meinbuero.de/openapi"
WISO_LEGACY_API_BASE_URL = "https://api.meinbuero.de"
WISO_SECRET_KEYS = {
    "api_key": "WISO_MEINBUERO_API_KEY",
    "api_secret": "WISO_MEINBUERO_API_SECRET",
    "ownership_id": "WISO_MEINBUERO_OWNERSHIP_ID",
}


class WisoApiError(Exception):
    pass


def secret_text(key: str) -> str:
    try:
        return str(st.secrets.get(key, "")).strip()
    except Exception:
        return ""


def wiso_missing_secrets() -> list[str]:
    return [secret_key for secret_key in WISO_SECRET_KEYS.values() if not secret_text(secret_key)]


def wiso_json_request(
    method: str,
    path: str,
    payload: Optional[Dict] = None,
    token: str = "",
    basic_auth: str = "",
    base_url: str = WISO_API_BASE_URL,
    form_payload: Optional[Dict] = None,
) -> Dict:
    url = f"{base_url}{path}"
    if form_payload is not None:
        data = urllib.parse.urlencode(form_payload).encode("utf-8")
    else:
        data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}

    if form_payload is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if basic_auth:
        headers["Authorization"] = f"Basic {basic_auth}"

    ownership_id = secret_text(WISO_SECRET_KEYS["ownership_id"])
    if ownership_id:
        headers["x-authorization-ownershipid"] = ownership_id

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            detail_json = json.loads(detail) if detail else {}
        except json.JSONDecodeError:
            detail_json = {}

        api_scopes = detail_json.get("meta", {}).get("apiScopes", [])
        if api_scopes:
            raise WisoApiError(
                "WISO API Zugriff nicht freigeschaltet. Bitte in MeinBuero unter "
                "'Eigene Erweiterungen' bei deiner App die benoetigten API-Zugriffe "
                "fuer Kunden und Auftraege aktivieren und erneut speichern/veroeffentlichen."
            ) from exc

        message = detail_json.get("message") if isinstance(detail_json, dict) else ""
        if message:
            raise WisoApiError(f"WISO API Fehler {exc.code}: {message}") from exc
        raise WisoApiError(f"WISO API Fehler {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise WisoApiError(f"WISO API nicht erreichbar: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise WisoApiError("WISO API hat keine gueltige JSON-Antwort geliefert.") from exc


def wiso_get_token() -> str:
    api_key = secret_text(WISO_SECRET_KEYS["api_key"])
    api_secret = secret_text(WISO_SECRET_KEYS["api_secret"])
    ownership_id = secret_text(WISO_SECRET_KEYS["ownership_id"])
    missing = wiso_missing_secrets()

    if missing:
        raise WisoApiError("WISO Secrets fehlen: " + ", ".join(missing))

    basic = base64.b64encode(f"{api_key}:{api_secret}".encode("utf-8")).decode("ascii")
    attempts = [
        {
            "base_url": WISO_API_BASE_URL,
            "payload": {"ownershipId": ownership_id},
            "form_payload": None,
        },
        {
            "base_url": WISO_LEGACY_API_BASE_URL,
            "payload": None,
            "form_payload": {
                "grant_type": "ownership",
                "ownershipId": ownership_id,
            },
        },
    ]

    errors = []
    for attempt in attempts:
        try:
            response = wiso_json_request(
                "POST",
                "/auth/token",
                payload=attempt["payload"],
                basic_auth=basic,
                base_url=attempt["base_url"],
                form_payload=attempt["form_payload"],
            )
            token = str(response.get("token") or response.get("access_token") or "").strip()
            if token:
                return token
            errors.append(f"{attempt['base_url']}: Token fehlt in Antwort")
        except WisoApiError as exc:
            errors.append(f"{attempt['base_url']}: {exc}")

    raise WisoApiError("WISO Token konnte nicht geholt werden. " + " | ".join(errors))


def get_wiso_token() -> str:
    return wiso_get_token()


def get_orders() -> Dict:
    token = get_wiso_token()
    errors = []
    query = urllib.parse.urlencode({"offset": 0, "limit": 20})
    for base_url, path in [
        (WISO_API_BASE_URL, f"/order?{query}"),
        (WISO_API_BASE_URL, f"/orders?{query}"),
    ]:
        try:
            return wiso_json_request("GET", path, token=token, base_url=base_url)
        except WisoApiError as exc:
            errors.append(f"{base_url}: {exc}")
    raise WisoApiError("WISO Auftraege konnten nicht geladen werden. " + " | ".join(errors))


def compact_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def extract_wiso_data_list(response: Dict) -> list[Dict]:
    data = response.get("data", [])
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        nested = data.get("data", [])
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return [data]
    return []


def wiso_find_customer_id(customer_name: str, token: str) -> tuple[Optional[str], list[str]]:
    search = customer_name.strip()
    if not search:
        raise WisoApiError("Kein Kunde im Preisauftrag vorhanden.")

    query = urllib.parse.urlencode({"limit": 20, "offset": 0, "orderBy": "name", "search": search})
    response = wiso_json_request("GET", f"/customer?{query}", token=token)
    customers = extract_wiso_data_list(response)
    needle = compact_match_text(search)
    candidates = []

    for customer in customers:
        name = str(customer.get("name") or customer.get("companyName") or customer.get("lastName") or "").strip()
        if name:
            candidates.append(name)
        haystack = compact_match_text(name)
        if needle and (needle == haystack or needle in haystack or haystack in needle):
            customer_id = customer.get("id")
            if customer_id:
                return str(customer_id), candidates

    if len(customers) == 1 and customers[0].get("id"):
        return str(customers[0]["id"]), candidates

    return None, candidates


def float_from_wiso_value(value, default: float = 0.0) -> float:
    text = str(value if value is not None else "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return default


def wiso_import_description(row: Dict) -> str:
    full_description = str(row.get("_wiso_import_description") or row.get("Beschreibung") or "").strip()
    if not full_description:
        return ""

    lines = [line.strip() for line in full_description.splitlines() if line.strip()]
    if not lines:
        return ""

    formatted = [lines[0]]
    for line in lines[1:]:
        formatted.append(line)
    return "\n".join(formatted)


def wiso_order_position_payload(row: Dict) -> Dict:
    description = wiso_import_description(row)
    article_no = str(row.get("Artikel-Nr.") or "").strip()
    first_line = description.splitlines()[0].strip() if description else ""
    title = (article_no or first_line or "Pondruff Beschichtung")[:80]
    price_net = float_from_wiso_value(row.get("Einzelpreis"), 0.0)
    if price_net <= 0:
        price_net = float_from_wiso_value(row.get("Listenpreis"), 0.0)

    return {
        "amount": safe_int(row.get("Menge"), 1),
        "title": title,
        "description": description,
        "showDescription": True,
        "unit": "Stk.",
        "priceNet": price_net,
        "priceGross": money(price_net * 1.19),
        "vatPercent": 19,
        "discountPercent": 0,
        "metaData": {"type": "custom"},
    }


def build_wiso_api_order_payload(order: Dict, customer_id: str) -> Dict:
    payload = {
        "customerId": int(customer_id) if str(customer_id).isdigit() else customer_id,
        "positions": [wiso_order_position_payload(row) for row in order.get("rows", [])],
    }

    return payload


def create_wiso_meinbuero_order(order: Dict) -> Dict:
    token = wiso_get_token()
    customer_id, candidates = wiso_find_customer_id(str(order.get("customer", "")), token)
    if not customer_id:
        hint = f" Gefundene Treffer: {', '.join(candidates)}." if candidates else ""
        raise WisoApiError(f"Kunde '{order.get('customer', '')}' wurde in WISO nicht eindeutig gefunden.{hint}")

    payload = build_wiso_api_order_payload(order, customer_id)
    response = wiso_json_request("POST", "/order/", payload, token=token)
    return {"customer_id": customer_id, "payload": payload, "response": response}


def wiso_api_button(order: Dict, key: str) -> None:
    missing = wiso_missing_secrets()
    if missing:
        st.warning(
            "WISO Direktimport ist vorbereitet, aber diese Streamlit Secrets fehlen noch: "
            + ", ".join(missing)
        )
        return

    if st.button("Auftrag direkt in WISO erstellen", key=f"wiso_api_order_{key}", use_container_width=True):
        try:
            with st.spinner("WISO-Kunde wird gesucht und Auftrag wird erstellt..."):
                result = create_wiso_meinbuero_order(order)
            response = result.get("response", {})
            data = response.get("data") if isinstance(response, dict) else {}
            order_number = ""
            order_id = ""
            if isinstance(data, dict):
                order_number = str(data.get("number") or "")
                order_id = str(data.get("id") or "")
            st.success(
                "WISO-Auftrag wurde erstellt"
                + (f" (Nr. {order_number})" if order_number else "")
                + (f" (ID {order_id})" if order_id and not order_number else "")
                + "."
            )
        except WisoApiError as exc:
            st.error(str(exc))
            try:
                token = wiso_get_token()
                customer_id, _ = wiso_find_customer_id(str(order.get("customer", "")), token)
                if customer_id:
                    st.caption("WISO Payload zur Kontrolle")
                    st.json(build_wiso_api_order_payload(order, customer_id))
            except Exception:
                pass


def load_wiso_price_orders() -> list[Dict]:
    orders = list(st.session_state.get("wiso_price_orders", []))
    sb = get_supabase()
    if not sb:
        return orders

    try:
        res = sb.table("wiso_preisauftraege").select("*").order("created_at", desc=True).execute()
        cloud_orders = [row.get("order_data") for row in (res.data or []) if row.get("order_data")]
        seen = {order.get("id") for order in orders}
        for order in cloud_orders:
            if order.get("id") not in seen:
                orders.append(order)
                seen.add(order.get("id"))
        st.session_state.wiso_price_orders = orders
    except Exception:
        pass
    return orders


def save_wiso_price_order(order: Dict) -> bool:
    st.session_state.wiso_price_orders = [
        existing for existing in st.session_state.get("wiso_price_orders", [])
        if existing.get("id") != order.get("id")
    ]
    st.session_state.wiso_price_orders.insert(0, order)

    sb = get_supabase()
    if not sb:
        return True

    try:
        sb.table("wiso_preisauftraege").insert(
            {
                "order_id": order.get("id", ""),
                "customer": order.get("customer", ""),
                "purchase_order": order.get("purchase_order", ""),
                "order_data": order,
            }
        ).execute()
    except Exception:
        pass
    return True


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



def real_ocr_price_positions(uploaded_files) -> Dict:
    files = uploaded_files or []
    if not isinstance(files, list):
        files = [files]

    if not files:
        st.warning("Bitte zuerst ein oder mehrere Dokumente hochladen.")
        return normalize_price_ocr_result({"positions": []})

    if not openai_ready():
        st.warning("OPENAI_API_KEY fehlt oder openai Paket ist nicht installiert. Es wird eine Demo-Position erzeugt.")
        return normalize_price_ocr_result(
            {
                "delivery_id": f"LS-{datetime.now().strftime('%H%M%S')}",
                "customer": "Musterkunde",
                "project": "Demo-Erkennung",
                "purchase_order": "B-2026-001",
                "confidence": 70,
                "ocr_note": "Demo-Erkennung: API-Key fehlt. Bitte Werte pruefen.",
                "positions": [
                    {
                        "description": "Demo Rundteil",
                        "article_no": "",
                        "order_no": "2026050061",
                        "cost_center": "006",
                        "quantity": 4,
                        "shape": "Rund",
                        "diameter": 49,
                        "length": 20,
                        "coating": "TiCN",
                    }
                ],
            }
        )

    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        prompt = f"""
Du liest einen Lieferschein oder ein Produktionsdokument fuer einen Preisrechner aus.

Gib NUR gueltiges JSON zurueck. Kein Markdown, keine Erklaerung.

Ziel:
- Erkenne Kundennamen und Lieferscheinnummer, falls vorhanden.
- Wir sind die Firma Pondruff und koennen niemals der Kunde sein.
- Wenn irgendwo Pondruff als Firmenname auftaucht, ignoriere Pondruff als Kunde.
- Wenn in Bestellung/Lieferschein ein anderer Firmenname auftaucht, uebernimm diesen als customer.
- Erkenne ALLE Positionen auf allen Bildern.
- Lies die Bilder nacheinander und fuehre die erkannten Positionen in einem gemeinsamen Array zusammen.
- Jede Position soll fuer den Preisrechner vorbereitet werden.
- Wenn Dokumente mehrere Positionen enthalten, gib mehrere Eintraege im Array "positions" zurueck.
- Erkenne je Position Artikelnummer, Positionsnummer, Auftragsnummer, Kostenstelle und Bestellnummer, falls vorhanden.
- Falls eine Bestellnummer nur global auf dem Dokument steht, gib sie oben als purchase_order zurueck.

Regeln:
- Fuer runde Teile nutze shape = "Rund" und fuelle diameter + length.
- Fuer eckige Teile nutze shape = "Eckig" und fuelle length + width + height.
- Wenn nur zwei Masse bei Rundteilen sichtbar sind, nimm Durchmesser und Laenge.
- Wenn Mengen nicht sicher sind, setze quantity auf 1.
- Wenn Beschichtung nicht klar lesbar ist, versuche eine beste Zuordnung.
- Erlaubte Beschichtungen fuer den Preisrechner: {", ".join(PRICE_COATINGS)}.
- Falls eine Position keine klaren Masse hat, setze die fehlenden Zahlen auf 0.
- note darf kurze OCR-Hinweise enthalten, z. B. "Masse unsicher".

JSON Schema:
{{
  "delivery_id": "string",
  "customer": "string",
  "project": "string",
  "purchase_order": "string",
  "confidence": 0,
  "ocr_note": "string",
  "positions": [
    {{
      "description": "string",
      "article_no": "string",
      "position_no": "string",
      "order_no": "string",
      "cost_center": "string",
      "purchase_order": "string",
      "quantity": 1,
      "shape": "Rund oder Eckig",
      "diameter": 0,
      "length": 0,
      "width": 0,
      "height": 0,
      "coating": "string",
      "discount": 0,
      "note": "string"
    }}
  ]
}}
"""

        content = [{"type": "input_text", "text": prompt}]
        for idx, uploaded_file in enumerate(files, start=1):
            image_bytes = uploaded_file.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            content.append({"type": "input_text", "text": f"Dokumentbild {idx}:"})
            content.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{image_base64}"})

        response = client.responses.create(
            model="gpt-4.1",
            input=[{"role": "user", "content": content}],
        )

        text = response.output_text.strip()
        json_text = clean_json_text(text)
        data = json.loads(json_text)
        return normalize_price_ocr_result(data)
    except Exception as e:
        st.error(f"GPT-4.1 Preis-OCR fehlgeschlagen: {e}")
        st.info("Es wurden keine Positionen uebernommen.")
        return normalize_price_ocr_result({"positions": []})


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
    if "price_ai_result" not in st.session_state:
        st.session_state.price_ai_result = None
    if "price_positions" not in st.session_state:
        st.session_state.price_positions = []
    if "price_customer" not in st.session_state:
        st.session_state.price_customer = ""
    if "price_project" not in st.session_state:
        st.session_state.price_project = ""
    if "price_purchase_order" not in st.session_state:
        st.session_state.price_purchase_order = ""
    if "wiso_price_orders" not in st.session_state:
        st.session_state.wiso_price_orders = []
    if "price_manual_mode" not in st.session_state:
        st.session_state.price_manual_mode = False
    if "price_global_discount" not in st.session_state:
        st.session_state.price_global_discount = 0.0


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



def validate_entry(entry: Dict, has_receipt: bool, has_parts: bool, has_packaging: bool) -> list[str]:
    errors = []

    if not has_receipt:
        errors.append("Lieferschein-Foto fehlt.")
    if not has_parts:
        errors.append("Bauteilfoto fehlt.")
    if not has_packaging:
        errors.append("Verpackungsfoto fehlt.")

    if not str(entry.get("id", "")).strip():
        errors.append("Lieferscheinnummer fehlt.")
    if not str(entry.get("customer", "")).strip():
        errors.append("Kunde fehlt.")
    if not str(entry.get("article_no", "")).strip():
        errors.append("Artikelnummer fehlt.")
    if not str(entry.get("description", "")).strip():
        errors.append("Artikelbezeichnung fehlt.")
    if int(entry.get("quantity", 0) or 0) <= 0:
        errors.append("Menge muss groesser als 0 sein.")

    if entry.get("shape") == "Rund":
        if float(entry.get("diameter", 0) or 0) <= 0:
            errors.append("Bei rundem Bauteil muss der Durchmesser eingetragen sein.")
        if float(entry.get("length", 0) or 0) <= 0:
            errors.append("Bei rundem Bauteil muss die Laenge eingetragen sein.")
    else:
        if float(entry.get("length", 0) or 0) <= 0:
            errors.append("Laenge muss eingetragen sein.")
        if float(entry.get("width", 0) or 0) <= 0:
            errors.append("Breite muss eingetragen sein.")
        if float(entry.get("height", 0) or 0) <= 0:
            errors.append("Hoehe muss eingetragen sein.")

    if entry.get("coated") == "Ja" and entry.get("coating") in ["", "-", "Keine", None]:
        errors.append("Beschichtung ist auf Ja gesetzt, aber keine Beschichtung ausgewaehlt.")

    if entry.get("polished") == "Ja" and float(entry.get("polishing_price", 0) or 0) < 0:
        errors.append("Polierpreis darf nicht negativ sein.")

    return errors


def make_entry_report_html(entry: Dict) -> bytes:
    title = f"Wareneingang {entry.get('id', entry.get('delivery_id', ''))}"
    rows = [
        ("Lieferschein", entry.get("id", entry.get("delivery_id", ""))),
        ("Datum", entry.get("date", "")),
        ("Bediener", entry.get("operator", "")),
        ("Kunde", entry.get("customer", "")),
        ("Artikelnummer", entry.get("article_no", "")),
        ("Artikelbezeichnung", entry.get("description", "")),
        ("Menge", entry.get("quantity", "")),
        ("Form", entry.get("shape", "")),
        ("Masse", entry_dimensions(entry)),
        ("Poliert", entry.get("polished", "")),
        ("Polierpreis", f"{float(entry.get('polishing_price', 0) or 0):.2f} EUR"),
        ("Beschichtet", entry.get("coated", "")),
        ("Beschichtung", entry.get("coating", "")),
        ("OCR Sicherheit", f"{entry.get('ocr_confidence', 0)}%"),
        ("Hinweise", entry.get("notes", "")),
    ]

    row_html = "".join(
        f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in rows
    )

    image_blocks = ""
    for label, key in [("Lieferschein", "receipt_url"), ("Bauteile", "parts_url"), ("Verpackung", "packaging_url")]:
        url = entry.get(key, "")
        if url:
            image_blocks += f"""
            <div class="imgbox">
                <h2>{html.escape(label)}</h2>
                <img src="{html.escape(url)}" />
            </div>
            """

    doc = f"""
    <!doctype html>
    <html lang="de">
    <head>
      <meta charset="utf-8">
      <title>{html.escape(title)}</title>
      <style>
        body {{ font-family: Arial, sans-serif; background:#101114; color:#fff; padding:32px; }}
        .wrap {{ max-width: 980px; margin: 0 auto; }}
        h1 {{ color:#ff3333; }}
        table {{ width:100%; border-collapse:collapse; background:#191d24; border-radius:16px; overflow:hidden; }}
        th, td {{ text-align:left; padding:12px 14px; border-bottom:1px solid #333; vertical-align:top; }}
        th {{ width:220px; color:#bbb; }}
        .imgbox {{ margin-top:24px; background:#191d24; border-radius:16px; padding:18px; }}
        img {{ max-width:100%; border-radius:12px; border:1px solid #333; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <h1>{html.escape(title)}</h1>
        <table>{row_html}</table>
        {image_blocks}
      </div>
    </body>
    </html>
    """
    return doc.encode("utf-8")


def statistics_page() -> None:
    st.markdown("## Statistik")
    entries = current_entries()

    if not entries:
        st.info("Noch keine Daten vorhanden.")
        return

    df = pd.DataFrame(entries)

    total_entries = len(entries)
    total_qty = sum(int(e.get("quantity", 0) or 0) for e in entries)
    open_count = sum(1 for e in entries if e.get("status") != "Abgeschlossen")
    coated_count = sum(1 for e in entries if e.get("coated") == "Ja")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Wareneingaenge", total_entries)
    c2.metric("Bauteile gesamt", total_qty)
    c3.metric("Offene Faelle", open_count)
    c4.metric("Beschichtet", coated_count)

    st.markdown("### Nach Bediener")
    if "operator" in df.columns:
        st.bar_chart(df["operator"].fillna("-").value_counts())

    st.markdown("### Nach Beschichtung")
    if "coating" in df.columns:
        st.bar_chart(df["coating"].fillna("Keine").value_counts())

    st.markdown("### Nach Kunde")
    if "customer" in df.columns:
        st.dataframe(df["customer"].fillna("-").value_counts().reset_index().rename(columns={"customer": "Kunde", "count": "Anzahl"}), use_container_width=True, hide_index=True)


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

        entry_preview = {
            "id": delivery_id,
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
        }
        validation_errors = validate_entry(entry_preview, receipt is not None, parts is not None, packaging is not None)
        if validation_errors:
            st.error("Bitte vor dem Speichern pruefen:")
            for error in validation_errors:
                st.warning(error)
            st.stop()

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
    entries = current_entries()

    f1, f2, f3, f4 = st.columns(4)
    q = f1.text_input("Suche", placeholder="Kunde, LS, Artikelnummer, Bediener")
    customer_filter = f2.selectbox("Kunde", ["Alle"] + sorted({str(e.get("customer", "-")) for e in entries}))
    operator_filter = f3.selectbox("Bediener", ["Alle"] + sorted({str(e.get("operator", "-")) for e in entries}))
    status_filter = f4.selectbox("Status", ["Alle"] + sorted({str(e.get("status", "-")) for e in entries}))

    filtered = entries

    if q:
        filtered = [e for e in filtered if q.lower() in " ".join(map(str, e.values())).lower()]
    if customer_filter != "Alle":
        filtered = [e for e in filtered if str(e.get("customer", "-")) == customer_filter]
    if operator_filter != "Alle":
        filtered = [e for e in filtered if str(e.get("operator", "-")) == operator_filter]
    if status_filter != "Alle":
        filtered = [e for e in filtered if str(e.get("status", "-")) == status_filter]

    st.caption(f"{len(filtered)} Treffer")

    for e in filtered:
        with st.expander(f"{e.get('id', e.get('delivery_id', ''))} Â· {e.get('customer', '')} Â· {e.get('article_no', '')}", expanded=False):
            entry_card(e, compact=False)

            st.markdown("### Grosse Bildansicht")
            tabs = st.tabs(["Lieferschein", "Bauteile", "Verpackung", "Bericht"])
            with tabs[0]:
                show_image_or_placeholder(e.get("receipt_url", ""), "demo_lieferschein.png", "Lieferschein")
            with tabs[1]:
                show_image_or_placeholder(e.get("parts_url", ""), "demo_bauteile.png", "Bauteile")
            with tabs[2]:
                show_image_or_placeholder(e.get("packaging_url", ""), "demo_verpackung.png", "Verpackung")
            with tabs[3]:
                report = make_entry_report_html(e)
                st.download_button(
                    "HTML-Bericht herunterladen",
                    data=report,
                    file_name=f"wareneingang_{e.get('id', e.get('delivery_id', 'bericht'))}.html",
                    mime="text/html",
                    key=f"report_{e.get('uuid', e.get('id', e.get('delivery_id', '')))}",
                )

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

    tab_orders, tab_entries = st.tabs(["Auftraege", "Wareneingaenge"])

    with tab_orders:
        orders = load_wiso_price_orders()
        st.markdown("### Auftraege aus dem Preis Rechner")
        if not orders:
            st.info("Noch keine Auftragstabelle gespeichert. Im Preis Rechner Positionen erfassen und 'WISO-Auftrag speichern' druecken.")
        else:
            labels = [
                f"{order.get('created_at', '')} - {order.get('customer', '')} - {order.get('purchase_order', '')}"
                for order in orders
            ]
            selected_label = st.selectbox("Auftrag auswaehlen", labels, key="office_price_order_select")
            selected_order = orders[labels.index(selected_label)]
            st.metric("Gesamt netto", f"{float(selected_order.get('total', 0.0)):.2f} EUR")
            df_order = pd.DataFrame(selected_order.get("rows", []))
            st.dataframe(df_order, use_container_width=True, hide_index=True)
            st.caption("Diesen Tab-Block kannst du direkt markieren/kopieren und in WISO als Positionsdaten weiterverwenden.")
            wiso_copy_button(selected_order, key="office")
            wiso_api_button(selected_order, key="office")
            st.code(wiso_order_tsv(selected_order), language="text")
            st.download_button(
                "Auftrag als CSV exportieren",
                data=df_order.to_csv(index=False, sep=";").encode("utf-8-sig"),
                file_name=f"{selected_order.get('id', 'preisauftrag')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with tab_entries:
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
            st.info("Noch keine KI-Suche gestartet. Lade links ein Bauteilfoto hoch und starte die Suche. Danach werden die besten Treffer angezeigt.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        st.markdown("### Top-Trefferliste")

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


def wiso_order_block(entry: Dict) -> str:
    lines = [
        "WISO AUFTRAGSDATEN",
        "------------------",
        f"Lieferschein: {entry.get('id', entry.get('delivery_id', ''))}",
        f"Datum Wareneingang: {entry.get('date', '')}",
        f"Erfasst von: {entry.get('operator', '-')}",
        "",
        f"Kunde: {entry.get('customer', '')}",
        f"Artikelnummer: {entry.get('article_no', '')}",
        f"Artikelbezeichnung: {entry.get('description', '')}",
        f"Menge: {entry.get('quantity', '')}",
        f"MaÃe: {entry_dimensions(entry)}",
        "",
        f"Poliert: {entry.get('polished', 'Nein')}",
        f"Preis Polieren: {float(entry.get('polishing_price', 0) or 0):.2f} EUR",
        f"Beschichtet: {entry.get('coated', 'Nein')}",
        f"Beschichtung: {entry.get('coating', 'Keine')}",
        "",
        f"Hinweise: {entry.get('notes', '')}",
    ]
    return "\n".join(lines)


def wiso_order_csv_row(entry: Dict) -> Dict:
    return {
        "Kunde": entry.get("customer", ""),
        "Artikelnummer": entry.get("article_no", ""),
        "Artikelbezeichnung": entry.get("description", ""),
        "Menge": entry.get("quantity", ""),
        "Form": entry.get("shape", ""),
        "Masse": entry_dimensions(entry),
        "Poliert": entry.get("polished", "Nein"),
        "Preis Polieren": f"{float(entry.get('polishing_price', 0) or 0):.2f}",
        "Beschichtet": entry.get("coated", "Nein"),
        "Beschichtung": entry.get("coating", "Keine"),
        "Lieferschein": entry.get("id", entry.get("delivery_id", "")),
        "Datum Wareneingang": entry.get("date", ""),
        "Bediener": entry.get("operator", "-"),
        "Hinweise": entry.get("notes", ""),
    }


def make_wiso_order_html(entry: Dict) -> bytes:
    block = wiso_order_block(entry)
    doc = f"""
    <!doctype html>
    <html lang="de">
    <head>
      <meta charset="utf-8">
      <title>WISO Ãbergabe {html.escape(str(entry.get('id', entry.get('delivery_id', ''))))}</title>
      <style>
        body {{ font-family: Arial, sans-serif; background:#101114; color:#fff; padding:32px; }}
        .wrap {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ color:#ff3333; }}
        pre {{ background:#191d24; border:1px solid #333; border-radius:16px; padding:20px; white-space:pre-wrap; line-height:1.5; }}
        .hint {{ color:#bbb; margin-bottom:20px; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <h1>WISO Ãbergabe</h1>
        <p class="hint">Diesen Datenblock im BÃ¼ro prÃ¼fen und in WISO Ã¼bernehmen.</p>
        <pre>{html.escape(block)}</pre>
      </div>
    </body>
    </html>
    """
    return doc.encode("utf-8")


def wiso_handover() -> None:
    st.markdown("## WISO Ãbergabe")
    st.markdown(
        "Hier kann das BÃ¼ro einen Wareneingang auswÃ¤hlen und die Daten direkt fÃ¼r WISO vorbereiten."
    )

    entries = current_entries()
    if not entries:
        st.info("Noch keine WareneingÃ¤nge vorhanden.")
        return

    search = st.text_input("Suchen", placeholder="Kunde, Lieferschein oder Artikelnummer")
    filtered = entries
    if search:
        filtered = [e for e in entries if search.lower() in " ".join(map(str, e.values())).lower()]

    if not filtered:
        st.warning("Keine passenden WareneingÃ¤nge gefunden.")
        return

    labels = [
        f"{e.get('id', e.get('delivery_id', ''))} Â· {e.get('customer', '')} Â· {e.get('article_no', '')}"
        for e in filtered
    ]
    selected_label = st.selectbox("Wareneingang fÃ¼r WISO auswÃ¤hlen", labels)
    selected_index = labels.index(selected_label)
    entry = filtered[selected_index]

    st.markdown("### Vorschau")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kunde", entry.get("customer", "-"))
    c2.metric("Artikel", entry.get("article_no", "-"))
    c3.metric("Menge", entry.get("quantity", "-"))
    c4.metric("Beschichtung", entry.get("coating", "-"))

    st.markdown("### Copy/Paste Datenblock")
    st.caption("Im Codefeld rechts oben auf Copy klicken und dann in WISO einfÃ¼gen.")
    st.code(wiso_order_block(entry), language="text")

    st.markdown("### Tabellarische WISO-Zeile")
    df_one = pd.DataFrame([wiso_order_csv_row(entry)])
    st.dataframe(df_one, use_container_width=True, hide_index=True)

    col_a, col_b, col_c = st.columns(3)
    col_a.download_button(
        "CSV fÃ¼r diesen Auftrag",
        data=df_one.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"wiso_auftrag_{entry.get('id', entry.get('delivery_id', 'auftrag'))}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col_b.download_button(
        "HTML Bericht",
        data=make_wiso_order_html(entry),
        file_name=f"wiso_auftrag_{entry.get('id', entry.get('delivery_id', 'auftrag'))}.html",
        mime="text/html",
        use_container_width=True,
    )

    all_df = pd.DataFrame([wiso_order_csv_row(e) for e in filtered])
    col_c.download_button(
        "CSV alle Treffer",
        data=all_df.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="wiso_auftraege_aus_wareneingang.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("### Bilder zum GegenprÃ¼fen")
    img1, img2, img3 = st.columns(3)
    with img1:
        show_image_or_placeholder(entry.get("receipt_url", ""), "demo_lieferschein.png", "Lieferschein")
    with img2:
        show_image_or_placeholder(entry.get("parts_url", ""), "demo_bauteile.png", "Bauteile")
    with img3:
        show_image_or_placeholder(entry.get("packaging_url", ""), "demo_verpackung.png", "Verpackung")

    st.markdown("### SpÃ¤tere API-Anbindung")
    st.info(
        "Dieser Bereich ist so vorbereitet, dass spÃ¤ter ein Button 'Direkt an WISO senden' ergÃ¤nzt werden kann, "
        "falls eure WISO-Version eine passende API oder Import-Schnittstelle nutzt."
    )


def price_calculator_page() -> None:
    st.markdown("## Preis Rechner")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    top_left, top_right = st.columns([1.2, 0.8])

    with top_left:
        uploaded_files = st.file_uploader(
            "Dokumente hochladen",
            type=["png", "jpg", "jpeg"],
            key="price_upload",
            accept_multiple_files=True,
        )
        if uploaded_files:
            st.caption(f"{len(uploaded_files)} Datei(en) bereit zum Auslesen.")

        global_discount = st.number_input(
            "Rabatt / Prozente fuer alle Positionen",
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.get("price_global_discount", 0.0)),
            step=1.0,
            key="price_global_discount_input",
        )
        st.session_state.price_global_discount = global_discount

        if st.button("GPT-4.1 Positionen auslesen", use_container_width=True):
            with st.spinner("GPT-4.1 liest das Dokument und erkennt Positionen..."):
                result = real_ocr_price_positions(uploaded_files)
                st.session_state.price_ai_result = result
                positions = result.get("positions", [])
                for idx, pos in enumerate(positions):
                    pos["discount"] = global_discount
                    if idx == 0:
                        pos["purchase_order"] = pos.get("purchase_order") or result.get("purchase_order", "")
                    else:
                        pos["purchase_order"] = ""
                st.session_state.price_positions = positions
                st.session_state.price_manual_mode = False
                if result.get("customer"):
                    st.session_state.price_customer = result["customer"]
                if result.get("delivery_id"):
                    st.session_state.price_project = result["delivery_id"]
                if result.get("purchase_order"):
                    st.session_state.price_purchase_order = result["purchase_order"]
            st.rerun()

    with top_right:
        if st.button("Preise manuell eintragen", use_container_width=True):
            st.session_state.price_manual_mode = True
            st.session_state.price_ai_result = None
            if not st.session_state.price_positions:
                st.session_state.price_positions = [blank_price_position("Eckig")]
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    positions = st.session_state.price_positions
    show_details = bool(positions) or st.session_state.get("price_manual_mode", False)
    if not show_details:
        return

    ai = st.session_state.get("price_ai_result")
    if ai:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.text_input("Kunde", value=st.session_state.get("price_customer", ""), disabled=True, key="price_customer_readonly")
        c2.text_input("Bestellnummer", value=st.session_state.get("price_purchase_order", ""), disabled=True, key="price_purchase_order_readonly")
        if ai.get("ocr_note"):
            st.info(ai["ocr_note"])
        wiso_preview = build_wiso_price_order(
            st.session_state.price_customer,
            st.session_state.price_project,
            positions,
            st.session_state.price_purchase_order,
        )
        st.markdown("### WISO-Vorschau")
        st.dataframe(pd.DataFrame(wiso_preview["rows"]), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("price_manual_mode", False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        customer = st.text_input("Kunde / Firma", value=st.session_state.get("price_customer", ""), key="price_customer_input")
        project = st.text_input("Projekt / Lieferschein", value=st.session_state.get("price_project", ""), key="price_project_input")
        purchase_order = st.text_input("Bestell.-Nr.", value=st.session_state.get("price_purchase_order", ""), key="price_purchase_order_input")
        st.session_state.price_customer = normalize_price_customer(customer)
        st.session_state.price_project = project
        st.session_state.price_purchase_order = purchase_order
        st.markdown('</div>', unsafe_allow_html=True)

    controls = st.columns(3)
    if controls[0].button("+ Runde Position", use_container_width=True):
        pos = blank_price_position("Rund")
        pos["discount"] = st.session_state.price_global_discount
        st.session_state.price_positions.append(pos)
        st.rerun()
    if controls[1].button("+ Eckige Position", use_container_width=True):
        pos = blank_price_position("Eckig")
        pos["discount"] = st.session_state.price_global_discount
        st.session_state.price_positions.append(pos)
        st.rerun()
    if controls[2].button("Positionen leeren", use_container_width=True):
        st.session_state.price_positions = []
        st.session_state.price_ai_result = None
        st.session_state.price_manual_mode = False
        st.rerun()

    if not positions:
        st.info("Noch keine Positionen vorhanden. Du kannst manuell Positionen anlegen oder ein Dokument auslesen lassen.")
        return

    total_normal = 0.0
    total_final = 0.0
    summary_rows = []
    updated_positions = []
    remove_index = None

    for idx, original in enumerate(positions):
        pos = normalize_price_position(original)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        header = st.columns([1.6, 1, 0.7])
        title = pos.get("description") or f"Position {idx + 1}"
        header[0].markdown(f"### Position {idx + 1}: {title}")
        header[1].markdown(f"**Quelle:** {pos.get('source', 'manuell').capitalize()}")
        if header[2].button("Loeschen", key=f"remove_price_pos_{idx}", use_container_width=True):
            remove_index = idx

        row1 = st.columns(5)
        pos["description"] = row1[0].text_input("Bezeichnung", value=pos["description"], key=f"price_desc_{idx}")
        pos["article_no"] = row1[0].text_input("Artikel-Nr.", value=pos.get("article_no", ""), key=f"price_article_no_{idx}")
        pos["quantity"] = row1[1].number_input("Stueckzahl", min_value=1, value=int(pos["quantity"]), step=1, key=f"price_qty_{idx}")
        pos["shape"] = row1[2].selectbox("Form", ["Eckig", "Rund"], index=0 if pos["shape"] == "Eckig" else 1, key=f"price_shape_{idx}")
        pos["coating"] = row1[3].selectbox(
            "Schicht",
            PRICE_COATINGS,
            index=PRICE_COATINGS.index(pos["coating"]) if pos["coating"] in PRICE_COATINGS else PRICE_COATINGS.index("TiCN"),
            key=f"price_coating_{idx}",
        )
        pos["factor"] = row1[4].number_input(
            "R4-Faktor",
            min_value=0.0,
            value=float(pos["factor"] or price_default_factor(pos["coating"])),
            step=0.1,
            key=f"price_factor_{idx}",
        )

        row2 = st.columns(5)
        if pos["shape"] == "Rund":
            pos["diameter"] = row2[0].number_input("Durchmesser (mm)", min_value=0.0, value=float(pos["diameter"]), step=0.1, key=f"price_d_{idx}")
            pos["length"] = row2[1].number_input("Laenge (mm)", min_value=0.0, value=float(pos["length"]), step=0.1, key=f"price_l_round_{idx}")
            pos["width"] = 0.0
            pos["height"] = 0.0
            row2[2].metric("Excel-Zelle", "S25 / T25")
            row2[3].metric("Volumenbasis", "Rund")
        else:
            pos["length"] = row2[0].number_input("Laenge (mm)", min_value=0.0, value=float(pos["length"]), step=0.1, key=f"price_l_rect_{idx}")
            pos["width"] = row2[1].number_input("Breite (mm)", min_value=0.0, value=float(pos["width"]), step=0.1, key=f"price_w_{idx}")
            pos["height"] = row2[2].number_input("Hoehe (mm)", min_value=0.0, value=float(pos["height"]), step=0.1, key=f"price_h_{idx}")
            pos["diameter"] = 0.0
            row2[3].metric("Excel-Zelle", "S10 / T10")
            row2[4].metric("Volumenbasis", "Eckig")

        row3 = st.columns(3)
        pos["discount"] = row3[0].number_input("Rabatt %", min_value=0.0, max_value=100.0, value=float(pos["discount"]), step=1.0, key=f"price_discount_{idx}")
        pos["position_no"] = row3[1].text_input("Positionsnummer", value=pos.get("position_no", ""), key=f"price_position_no_{idx}")
        pos["order_no"] = row3[2].text_input("Auftrags.-Nr.", value=pos.get("order_no", ""), key=f"price_order_no_{idx}")

        row4 = st.columns(3)
        pos["cost_center"] = row4[0].text_input("Kostenstelle", value=pos.get("cost_center", ""), key=f"price_cost_center_{idx}")
        if idx == 0:
            pos["purchase_order"] = row4[1].text_input("Bestell.-Nr.", value=pos.get("purchase_order", "") or st.session_state.price_purchase_order, key=f"price_purchase_order_pos_{idx}")
            st.session_state.price_purchase_order = pos["purchase_order"]
        else:
            pos["purchase_order"] = ""
            row4[1].caption("Bestell.-Nr. wird fuer WISO nur in der letzten Position ausgegeben.")

        row5 = st.columns(3)
        pos["note"] = row5[0].text_input("Notiz", value=pos["note"], key=f"price_note_{idx}")
        default_factor = price_default_factor(pos["coating"])
        row5[1].caption(f"Standardfaktor fuer {pos['coating']}: {default_factor:.2f}")

        result = calc_price_position(pos)
        total_normal += result["normal_total"]
        total_final += result["final_total"]
        positions[idx] = pos
        updated_positions.append(pos)

        result_cols = st.columns(4)
        result_cols[0].metric("Preis / Stk.", f"{result['unit_price']:.2f} EUR")
        result_cols[1].metric("Normalpreis", f"{result['normal_total']:.2f} EUR")
        result_cols[2].metric("Rabatt", f"{result['discount_amount']:.2f} EUR")
        result_cols[3].metric("Preis nach Rabatt", f"{result['final_total']:.2f} EUR")

        summary_rows.append(
            {
                "Pos.": idx + 1,
                "Bezeichnung": pos.get("description") or "-",
                "Artikel-Nr.": pos.get("article_no", ""),
                "Form": pos["shape"],
                "Schicht": pos["coating"],
                "Faktor": pos["factor"],
                "Stk.": pos["quantity"],
                "Preis Netto": result["final_total"],
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if remove_index is not None:
        del st.session_state.price_positions[remove_index]
        st.rerun()

    st.session_state.price_positions = updated_positions

    discount_sum = money(total_normal - total_final)
    net = money(total_final)
    vat = money(net * 0.19)
    gross = money(net + vat)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Gesamt")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Normalpreis", f"{money(total_normal):.2f} EUR")
    s2.metric("Rabatt gesamt", f"{discount_sum:.2f} EUR")
    s3.metric("Positionen", len(positions))
    s4.metric("Netto", f"{net:.2f} EUR")
    s5.metric("Brutto", f"{gross:.2f} EUR")
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    summary_text = "\n".join(
        [
            "Pondruff Preis Rechner",
            f"Kunde: {st.session_state.price_customer}",
            f"Projekt/Lieferschein: {st.session_state.price_project}",
            "",
        ]
        + [
            f"{row['Pos.']}. {row['Bezeichnung']} | {row['Form']} | {row['Schicht']} | Faktor {row['Faktor']:.2f} | {row['Stk.']} Stk. | {row['Preis Netto']:.2f} EUR"
            for row in summary_rows
        ]
        + [
            "",
            f"Netto: {net:.2f} EUR",
            f"MwSt. 19%: {vat:.2f} EUR",
            f"Brutto: {gross:.2f} EUR",
        ]
    )
    st.code(summary_text, language="text")

    wiso_order = build_wiso_price_order(
        st.session_state.price_customer,
        st.session_state.price_project,
        updated_positions,
        st.session_state.price_purchase_order,
    )
    st.markdown("### WISO-Vorschau")
    st.dataframe(pd.DataFrame(wiso_order["rows"]), use_container_width=True, hide_index=True)
    wiso_copy_button(wiso_order, key="price")
    wiso_api_button(wiso_order, key="price")
    st.code(wiso_order_tsv(wiso_order), language="text")
    if st.button("Start: WISO-Auftrag speichern", use_container_width=True):
        save_wiso_price_order(wiso_order)
        st.success("WISO-Auftrag wurde unter Buero / WISO > Auftraege gespeichert.")
    st.markdown('</div>', unsafe_allow_html=True)


def setup_help() -> None:
    st.markdown("## Supabase + OpenAI Setup")

    st.markdown("### 1. Streamlit Secrets")
    st.code("""
SUPABASE_URL = "https://DEIN-PROJEKT.supabase.co"
SUPABASE_ANON_KEY = "DEIN-ANON-KEY"
OPENAI_API_KEY = "sk-..."
WISO_MEINBUERO_API_KEY = "..."
WISO_MEINBUERO_API_SECRET = "..."
WISO_MEINBUERO_OWNERSHIP_ID = "..."
    """, language="toml")

    st.markdown("### 1b. WISO API testen")
    missing = wiso_missing_secrets()
    if missing:
        st.info("Zum WISO-Test fehlen noch Secrets: " + ", ".join(missing))
    elif st.button("WISO testen", use_container_width=True):
        try:
            with st.spinner("WISO-Auftraege werden geladen..."):
                data = get_orders()
            st.success("WISO API antwortet.")
            st.write(data)
        except WisoApiError as exc:
            st.error(str(exc))

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

create table if not exists wiso_preisauftraege (
  uuid uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default now(),
  order_id text,
  customer text,
  purchase_order text,
  order_data jsonb
);

alter table wiso_preisauftraege enable row level security;

drop policy if exists "allow authenticated read wiso orders" on wiso_preisauftraege;
drop policy if exists "allow authenticated insert wiso orders" on wiso_preisauftraege;

create policy "allow authenticated read wiso orders"
on wiso_preisauftraege for select
to authenticated
using (true);

create policy "allow authenticated insert wiso orders"
on wiso_preisauftraege for insert
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
        ["Dashboard", "Neuer Wareneingang", "Preis Rechner", "Archiv", "Buero / WISO", "WISO Ãbergabe", "KI-Suche", "Statistik", "Setup"],
    )

    if page == "Dashboard":
        dashboard()
    elif page == "Neuer Wareneingang":
        capture()
    elif page == "Preis Rechner":
        price_calculator_page()
    elif page == "Archiv":
        archive()
    elif page == "Buero / WISO":
        office()
    elif page == "WISO Ãbergabe":
        wiso_handover()
    elif page == "KI-Suche":
        ai_search()
    elif page == "Statistik":
        statistics_page()
    else:
        setup_help()


if __name__ == "__main__":
    main()
