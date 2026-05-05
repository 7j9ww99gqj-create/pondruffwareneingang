from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client, Client

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"
BUCKET_NAME = "wareneingang-bilder"

USERS = ["Kevin", "Tim", "Frank", "Julian", "Tobi", "Christian"]
COATINGS = ["Meta-S", "CrN", "CrN-RB", "Duplex Meta cax", "AlCrN", "TiN", "TiaLN", "TiCN", "Keine"]


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
    for i, label in enumerate(["Lieferschein", "Bauteile", "Verpackung", "Cloud Storage"]):
        y = 320 + i * 100
        d.rounded_rectangle((1040, y, 1460, y + 70), radius=20, fill=(29, 35, 44), outline=(230, 0, 0), width=3)
        d.text((1080, y + 18), label, fill=(255, 255, 255), font=small)
    img.save(path)


def ensure_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    items = {
        "wareneingang.png": ("Digitaler Wareneingang mit KI", "Cloud, Login, Bilder und spaeter echte KI."),
        "demo_lieferschein.png": ("Lieferschein", "KI liest Kunde, Lieferant, Artikelnummer, Menge und Masse."),
        "demo_bauteile.png": ("Bauteile", "Bauteile werden mit dem Wareneingang gespeichert."),
        "demo_verpackung.png": ("Verpackung", "Verpackungsmaterial bleibt als Nachweis erhalten."),
        "demo_suchteil.png": ("KI-Suchfoto", "Unbekanntes Bauteil fotografieren und zuordnen."),
        "slide_1.png": ("Praesentation", "Titel und Uebersicht"),
    }
    for name, (title, subtitle) in items.items():
        p = ASSETS / name
        if not p.exists():
            placeholder(p, title, subtitle)


def css() -> None:
    st.markdown("""
        <style>
        .stApp {background: radial-gradient(circle at top right, rgba(180,0,0,.25), transparent 30%), linear-gradient(135deg,#030405,#0b0f13 55%,#030405); color:white;}
        [data-testid="stSidebar"] {background:#060708; border-right:1px solid rgba(255,255,255,.12)}
        h1,h2,h3 {letter-spacing:-.035em}
        .hero {border:1px solid rgba(255,255,255,.12); border-radius:28px; overflow:hidden; box-shadow:0 24px 80px rgba(0,0,0,.45); margin-bottom:20px;}
        .hero img {width:100%; display:block;}
        .hero-text {padding:20px 24px; background:linear-gradient(90deg,rgba(15,18,22,.96),rgba(120,0,0,.28)); border-top:1px solid rgba(255,255,255,.12)}
        .hero-text h1 {margin:0; font-size:34px;}
        .hero-text p {margin:6px 0 0; color:#aeb7c5; font-size:18px;}
        .card {background:rgba(18,22,28,.92); border:1px solid rgba(255,255,255,.12); border-radius:24px; padding:20px; box-shadow:0 18px 60px rgba(0,0,0,.25); margin-bottom:16px;}
        .metric-card {background:rgba(18,22,28,.92); border:1px solid rgba(255,255,255,.12); border-radius:22px; padding:20px;}
        .metric-label {color:#aeb7c5; font-size:14px;}
        .metric-value {font-size:36px; font-weight:900; line-height:1; margin-top:8px;}
        .metric-hint {color:#e50909; font-size:13px; font-weight:800; margin-top:8px;}
        .status {display:inline-flex; padding:7px 11px; border-radius:999px; font-weight:800; font-size:12px; margin:2px;}
        .ok {background:rgba(80,210,60,.16); color:#aaff9b; border:1px solid rgba(80,210,60,.35)}
        .warn {background:rgba(255,176,32,.16); color:#ffd37a; border:1px solid rgba(255,176,32,.35)}
        .ai {background:rgba(77,163,255,.14); color:#b8dcff; border:1px solid rgba(77,163,255,.4)}
        .ai-box {background:linear-gradient(135deg,rgba(12,34,58,.95),rgba(28,18,20,.95)); border:1px solid rgba(77,163,255,.35); border-radius:24px; padding:20px; margin-bottom:16px;}
        .stButton>button,.stDownloadButton>button {border-radius:14px!important; background:linear-gradient(180deg,#f01212,#b80000)!important; color:white!important; font-weight:800!important; border:1px solid rgba(229,9,9,.5)!important;}
        .stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]>div {background-color:rgba(255,255,255,.055)!important; color:white!important; border-color:rgba(255,255,255,.13)!important; border-radius:14px!important;}
        </style>
        """, unsafe_allow_html=True)


def img_bytes(name: str) -> bytes:
    return (ASSETS / name).read_bytes()


def entry_dimensions(e: Dict) -> str:
    if e.get("shape") == "Rund":
        return f"Durchmesser {e.get('diameter', 0)} x Laenge {e.get('length', 0)} mm"
    return f"{e.get('length', 0)} x {e.get('width', 0)} x {e.get('height', 0)} mm"


def status_html(status: str) -> str:
    css_class = "ok" if status in ["Abgeschlossen", "Gespeichert"] else "warn"
    return f'<span class="status {css_class}">{status}</span>'


def ai_html(text: str) -> str:
    return f'<span class="status ai">KI {text}</span>'


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


def login(email: str, password: str) -> bool:
    sb = get_supabase()
    if not sb:
        st.error("Supabase ist noch nicht eingerichtet.")
        return False
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        return True
    except Exception as e:
        st.error(f"Login fehlgeschlagen: {e}")
        return False


def signup(email: str, password: str) -> bool:
    sb = get_supabase()
    if not sb:
        st.error("Supabase ist noch nicht eingerichtet.")
        return False
    try:
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Benutzer erstellt. Danach einloggen. Falls E-Mail-Bestaetigung aktiv ist, bitte E-Mail bestaetigen.")
        return True
    except Exception as e:
        st.error(f"Registrierung fehlgeschlagen: {e}")
        return False


def logout() -> None:
    sb = get_supabase()
    if sb:
        try:
            sb.auth.sign_out()
        except Exception:
            pass
    st.session_state.user = None
    st.session_state.entries_cache = None


def login_screen() -> None:
    ensure_assets()
    css()
    st.image(ASSETS / "wareneingang.png", use_container_width=True)
    st.title("Pondruff / WE Login")
    st.write("Cloud + Login + Bildspeicher Test-Version.")
    if not cloud_ready():
        st.warning("Supabase ist noch nicht verbunden. Bitte Streamlit Secrets eintragen.")
        st.code('SUPABASE_URL = "https://DEIN-PROJEKT.supabase.co"\nSUPABASE_ANON_KEY = "DEIN-ANON-KEY"', language="toml")
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
        "supplier": "Elektronik Komponenten AG",
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
    }


def demo_entries() -> list[Dict]:
    return [{
        "id": "LS-2024-04578", "delivery_id": "LS-2024-04578", "date": "24.05.2024, 09:15", "operator": "Kevin",
        "customer": "Mustertechnik GmbH", "supplier": "Elektronik Komponenten AG", "article_no": "ART-123456",
        "description": "Praezisionsteil XY", "quantity": 25, "shape": "Eckig", "diameter": 0.0,
        "length": 120.50, "width": 80.25, "height": 45.00, "polished": "Ja", "polishing_price": 25.00,
        "coated": "Ja", "coating": "AlCrN", "notes": "Demo-Datensatz", "status": "Abgeschlossen",
        "ocr_confidence": 94, "match": 92, "created_by": "demo", "receipt_url": "", "parts_url": "", "packaging_url": ""
    }]


def load_entries_from_cloud() -> list[Dict]:
    sb = get_supabase()
    if not sb:
        return demo_entries()
    try:
        res = sb.table("wareneingaenge").select("*").order("created_at", desc=True).execute()
        return res.data if res.data else demo_entries()
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


def upload_file_to_storage(file, delivery_id: str, kind: str) -> str:
    """Speichert Bild in Supabase Storage und gibt eine public URL zurueck."""
    if file is None:
        return ""
    sb = get_supabase()
    if not sb:
        return ""
    safe_delivery = delivery_id.replace("/", "-").replace(" ", "-")
    original_name = file.name.replace("/", "-").replace(" ", "-")
    path = f"{safe_delivery}/{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_name}"
    data = file.getvalue()
    content_type = getattr(file, "type", None) or "image/jpeg"
    try:
        sb.storage.from_(BUCKET_NAME).upload(path, data, {"content-type": content_type, "upsert": "true"})
        public = sb.storage.from_(BUCKET_NAME).get_public_url(path)
        return public
    except Exception as e:
        st.error(f"Bild-Upload fehlgeschlagen ({kind}): {e}")
        return ""


def init_data() -> None:
    if "user" not in st.session_state:
        st.session_state.user = None
    if "ai_result" not in st.session_state:
        st.session_state.ai_result = None
    if "entries_cache" not in st.session_state:
        st.session_state.entries_cache = None


def current_entries() -> list[Dict]:
    if st.session_state.entries_cache is None:
        st.session_state.entries_cache = load_entries_from_cloud()
    return st.session_state.entries_cache


def refresh_entries() -> None:
    st.session_state.entries_cache = load_entries_from_cloud()


def hero() -> None:
    import base64
    b64 = base64.b64encode(img_bytes("wareneingang.png")).decode("utf-8")
    st.markdown(f"""
    <div class="hero">
      <img src="data:image/png;base64,{b64}" />
      <div class="hero-text">
        <h1>Digitaler Wareneingang mit Cloud + Bildspeicher</h1>
        <p>Auftraege, Lieferscheine, Bauteile und Verpackungen werden in Supabase gespeichert.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)


def metrics() -> None:
    entries = current_entries()
    total_qty = sum(int(e.get("quantity", 0)) for e in entries)
    image_count = sum(1 for e in entries for key in ["receipt_url", "parts_url", "packaging_url"] if e.get(key))
    avg_ocr = round(sum(e.get("ocr_confidence", 0) for e in entries) / max(len(entries), 1))
    cols = st.columns(4)
    data = [("Wareneingaenge", len(entries), "aus Cloud"), ("Bauteile", total_qty, "Stueck gesamt"), ("Bilder", image_count, "in Storage"), ("OCR", f"{avg_ocr}%", "KI-Erkennung")]
    for col, (label, value, hint) in zip(cols, data):
        col.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-hint">{hint}</div></div>', unsafe_allow_html=True)


def show_image_from_entry(e: Dict, key: str, fallback: str, caption: str) -> None:
    url = e.get(key, "")
    if url:
        st.image(url, caption=caption, use_container_width=True)
    else:
        st.image(ASSETS / fallback, caption=f"{caption} (Demo)", use_container_width=True)


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
            show_image_from_entry(e, "receipt_url", "demo_lieferschein.png", "Lieferschein")
        with i2:
            show_image_from_entry(e, "parts_url", "demo_bauteile.png", "Bauteile")
        with i3:
            show_image_from_entry(e, "packaging_url", "demo_verpackung.png", "Verpackung")
        if e.get("receipt_url") or e.get("parts_url") or e.get("packaging_url"):
            st.markdown("### Bild-Links")
            if e.get("receipt_url"):
                st.link_button("Lieferschein oeffnen", e["receipt_url"])
            if e.get("parts_url"):
                st.link_button("Bauteile oeffnen", e["parts_url"])
            if e.get("packaging_url"):
                st.link_button("Verpackung oeffnen", e["packaging_url"])
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
        - Wareneingaenge in Supabase Tabelle
        - Lieferschein-Bilder in Supabase Storage
        - Bauteil-Bilder in Supabase Storage
        - Verpackungs-Bilder in Supabase Storage
        - WISO Copy/Paste und CSV Export
        """)
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
    st.markdown("### 2. KI-Lieferschein-Erkennung")
    st.write("Demo: Felder werden beispielhaft vorgefuellt. Echte OCR kommt spaeter.")
    if st.button("KI: Lieferschein auslesen", use_container_width=True):
        st.session_state.ai_result = fake_ocr(receipt)
        st.success("KI-Auslesung abgeschlossen. Bitte unten gegenpruefen.")
    ai = st.session_state.get("ai_result")
    if ai:
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Sicherheit", f"{ai['confidence']}%")
        x2.metric("Lieferschein", ai["id"])
        x3.metric("Kunde", ai["customer"])
        x4.metric("Artikel", ai["article_no"])
    st.markdown('</div>', unsafe_allow_html=True)

    d = ai or fake_ocr(None)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 3. Daten pruefen und speichern")
    col1, col2, col3 = st.columns(3)
    with col1:
        delivery_id = st.text_input("Lieferscheinnummer", value=d["id"])
        customer = st.text_input("Kunde", value=d["customer"])
        supplier = st.text_input("Lieferant", value=d["supplier"])
        article_no = st.text_input("Artikelnummer", value=d["article_no"])
    with col2:
        description = st.text_input("Bezeichnung", value=d["description"])
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
    notes = st.text_area("Hinweise", value="Daten wurden per KI vorbereitet und vom Mitarbeiter geprueft.")
    operator = st.selectbox("Bediener auswaehlen", USERS, index=0)

    missing = []
    if receipt is None: missing.append("Lieferschein")
    if parts is None: missing.append("Bauteile")
    if packaging is None: missing.append("Verpackung")
    if missing:
        st.warning("Noch fehlende Pflichtfotos: " + ", ".join(missing))

    if st.button("Auftrag + Bilder in Cloud speichern", use_container_width=True):
        user_email = st.session_state.user.email if st.session_state.user else "unbekannt"
        with st.spinner("Bilder werden in Supabase Storage hochgeladen..."):
            receipt_url = upload_file_to_storage(receipt, delivery_id, "lieferschein")
            parts_url = upload_file_to_storage(parts, delivery_id, "bauteile")
            packaging_url = upload_file_to_storage(packaging, delivery_id, "verpackung")
        entry = {
            "delivery_id": delivery_id, "id": delivery_id, "date": datetime.now().strftime("%d.%m.%Y, %H:%M"),
            "operator": operator, "customer": customer, "supplier": supplier, "article_no": article_no, "description": description,
            "quantity": int(quantity), "shape": shape, "diameter": float(diameter), "length": float(length), "width": float(width), "height": float(height),
            "polished": polished, "polishing_price": float(polishing_price), "coated": coated, "coating": coating,
            "notes": notes, "status": "Gespeichert", "ocr_confidence": int(d.get("confidence", 0)), "match": 92,
            "created_by": user_email, "receipt_url": receipt_url, "parts_url": parts_url, "packaging_url": packaging_url,
        }
        if save_entry_to_cloud(entry):
            st.session_state.ai_result = None
            refresh_entries()
            st.success(f"Wareneingang {delivery_id} inkl. Bilder wurde in der Cloud gespeichert.")
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
    return "\t".join([str(e.get("id", e.get("delivery_id", ""))), str(e.get("date", "")), str(e.get("operator", "-")), str(e.get("customer", "")), str(e.get("supplier", "")), str(e.get("article_no", "")), str(e.get("description", "")), str(e.get("quantity", "")), str(e.get("shape", "Eckig")), entry_dimensions(e), str(e.get("polished", "")), f"{float(e.get('polishing_price', 0)):.2f}", str(e.get("coated", "")), str(e.get("coating", "")), str(e.get("notes", "")), str(e.get("receipt_url", "")), str(e.get("parts_url", "")), str(e.get("packaging_url", ""))])


def office() -> None:
    st.markdown("## Buero / WISO")
    rows = []
    for e in current_entries():
        rows.append({"Lieferschein": e.get("id", e.get("delivery_id", "")), "Datum": e.get("date", ""), "Bediener": e.get("operator", "-"), "Kunde": e.get("customer", ""), "Artikelnummer": e.get("article_no", ""), "Menge": e.get("quantity", 0), "Form": e.get("shape", "Eckig"), "Masse": entry_dimensions(e), "Poliert": e.get("polished", "Nein"), "Polierpreis": f"{float(e.get('polishing_price', 0)):.2f} EUR", "Beschichtet": e.get("coated", "Nein"), "Beschichtung": e.get("coating", "Keine"), "Lieferscheinbild": "Ja" if e.get("receipt_url") else "Nein", "Bauteilbild": "Ja" if e.get("parts_url") else "Nein", "Verpackungsbild": "Ja" if e.get("packaging_url") else "Nein"})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    entries = current_entries()
    selected = st.selectbox("Datensatz fuer WISO auswaehlen", [e.get("id", e.get("delivery_id", "")) for e in entries])
    entry = next(e for e in entries if e.get("id", e.get("delivery_id", "")) == selected)
    st.code(wiso_text(entry), language="text")
    st.download_button("CSV exportieren", data=df.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name="wareneingang_wiso.csv", mime="text/csv")


def ai_search() -> None:
    st.markdown("## KI-Suche")
    left, right = st.columns([.85, 1.15])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        uploaded = st.file_uploader("Foto vom unbekannten Bauteil", type=["png", "jpg", "jpeg"], key="ai_search")
        st.image(uploaded if uploaded else ASSETS / "demo_suchteil.png", caption="Suchbild", use_container_width=True)
        st.button("KI-Suche starten", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        best = current_entries()[0]
        st.success(f"Bester Treffer: {best.get('id', best.get('delivery_id', ''))} - {best.get('customer', '')} - {best.get('match', 92)}%")
        entry_card(best)
        st.markdown("**Demo:** Echte Bild-KI kommt im naechsten Schritt. Die Bilder liegen jetzt aber schon in Supabase Storage.")
        st.markdown('</div>', unsafe_allow_html=True)


def setup_help() -> None:
    st.markdown("## Supabase Setup fuer Tabelle + Bildspeicher")
    st.markdown("### 1. SQL Tabelle ausfuehren")
    st.code("""
create table if not exists wareneingaenge (
  uuid uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default now(),
  delivery_id text,
  id text,
  date text,
  operator text,
  customer text,
  supplier text,
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
    st.markdown("### 2. Storage Bucket erstellen")
    st.markdown(f"In Supabase: **Storage â New bucket** â Name: `{BUCKET_NAME}` â Public bucket aktivieren.")
    st.markdown("### 3. Storage Policies ausfuehren")
    st.code(f"""
insert into storage.buckets (id, name, public)
values ('{BUCKET_NAME}', '{BUCKET_NAME}', true)
on conflict (id) do update set public = true;

create policy "allow authenticated upload wareneingang bilder"
on storage.objects for insert
to authenticated
with check (bucket_id = '{BUCKET_NAME}');

create policy "allow public read wareneingang bilder"
on storage.objects for select
to public
using (bucket_id = '{BUCKET_NAME}');
    """, language="sql")


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
    page = st.sidebar.radio("Navigation", ["Dashboard", "Neuer Wareneingang", "Archiv", "Buero / WISO", "KI-Suche", "Supabase Setup"])
    if page == "Dashboard": dashboard()
    elif page == "Neuer Wareneingang": capture()
    elif page == "Archiv": archive()
    elif page == "Buero / WISO": office()
    elif page == "KI-Suche": ai_search()
    else: setup_help()


if __name__ == "__main__":
    main()
