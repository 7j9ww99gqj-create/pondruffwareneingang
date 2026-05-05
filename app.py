from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"
USERS = ["Kevin", "Tim", "Frank", "Julian", "Tobi", "Christian"]


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
    labels = ["Lieferschein", "Bauteile", "Verpackung", "KI-Zuordnung"]
    for i, label in enumerate(labels):
        y = 320 + i * 100
        d.rounded_rectangle((1040, y, 1460, y + 70), radius=20, fill=(29, 35, 44), outline=(230, 0, 0), width=3)
        d.text((1080, y + 18), label, fill=(255, 255, 255), font=small)
    img.save(path)


def ensure_assets() -> None:
    items = {
        "wareneingang.png": ("Digitaler Wareneingang mit KI", "Lieferschein erkennen. Bauteile spaeter per Foto zuordnen."),
        "demo_lieferschein.png": ("Lieferschein", "KI liest Kunde, Lieferant, Artikelnummer, Menge und Masse."),
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
        .bad {background:rgba(229,9,9,.18); color:#ffb8b8; border:1px solid rgba(229,9,9,.4)}
        .ai {background:rgba(77,163,255,.14); color:#b8dcff; border:1px solid rgba(77,163,255,.4)}
        .ai-box {background:linear-gradient(135deg,rgba(12,34,58,.95),rgba(28,18,20,.95)); border:1px solid rgba(77,163,255,.35); border-radius:24px; padding:20px; margin-bottom:16px;}
        .stButton>button,.stDownloadButton>button {border-radius:14px!important; background:linear-gradient(180deg,#f01212,#b80000)!important; color:white!important; font-weight:800!important; border:1px solid rgba(229,9,9,.5)!important;}
        .stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]>div {background-color:rgba(255,255,255,.055)!important; color:white!important; border-color:rgba(255,255,255,.13)!important; border-radius:14px!important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def img_bytes(name: str) -> bytes:
    return (ASSETS / name).read_bytes()


def to_img(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def file_bytes(file) -> Optional[bytes]:
    return file.getvalue() if file is not None else None


def status_html(status: str) -> str:
    css_class = "ok" if status in ["Abgeschlossen", "Gespeichert"] else "warn" if "Pruefung" in status or "PrÃ¼fung" in status else "bad"
    return f'<span class="status {css_class}">{status}</span>'


def ai_html(text: str) -> str:
    return f'<span class="status ai">KI {text}</span>'


def fake_ocr(file=None) -> Dict:
    """Demo-OCR. Spaeter hier echte KI/OCR anbinden."""
    return {
        "id": f"LS-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%H%M%S')}",
        "customer": "Mustertechnik GmbH",
        "supplier": "Elektronik Komponenten AG",
        "article_no": "ART-123456",
        "description": "Praezisionsteil XY",
        "quantity": 25,
        "length": 120.50,
        "width": 80.25,
        "height": 45.00,
        "polished": "Ja",
        "coated": "Ja",
        "coating": "Harteloxal",
        "layer": "Schwarz / 25 um",
        "confidence": 94,
    }


def init_data() -> None:
    if "entries" in st.session_state:
        return
    st.session_state.ai_result = None
    st.session_state.entries = [
        {
            "id": "LS-2024-04578", "date": "24.05.2024, 09:15", "operator": "Kevin",
            "customer": "Mustertechnik GmbH", "supplier": "Elektronik Komponenten AG",
            "article_no": "ART-123456", "description": "Praezisionsteil XY", "quantity": 25,
            "length": 120.50, "width": 80.25, "height": 45.00,
            "polished": "Ja", "coated": "Ja", "coating": "Harteloxal", "layer": "Schwarz / 25 um",
            "notes": "Keine Kanten brechen. Ware vollstaendig erfasst.", "status": "Abgeschlossen", "ocr_confidence": 94,
            "receipt_img": img_bytes("demo_lieferschein.png"), "parts_img": img_bytes("demo_bauteile.png"), "packaging_img": img_bytes("demo_verpackung.png"), "match": 92,
        },
        {
            "id": "LS-2024-04577", "date": "24.05.2024, 08:32", "operator": "Tim",
            "customer": "ABC Engineering", "supplier": "Fraesteile Nord GmbH",
            "article_no": "ART-987654", "description": "Gehaeuseteil AB", "quantity": 10,
            "length": 95.00, "width": 60.00, "height": 30.00,
            "polished": "Nein", "coated": "Ja", "coating": "Pulverbeschichtung", "layer": "RAL 9005 / 80 um",
            "notes": "Oberflaeche pruefen, kleiner Kratzer an Verpackung.", "status": "Pruefung offen", "ocr_confidence": 88,
            "receipt_img": img_bytes("demo_lieferschein.png"), "parts_img": img_bytes("demo_bauteile.png"), "packaging_img": img_bytes("demo_verpackung.png"), "match": 67,
        },
    ]


def hero() -> None:
    import base64
    b64 = base64.b64encode(img_bytes("wareneingang.png")).decode("utf-8")
    st.markdown(f"""
    <div class="hero">
      <img src="data:image/png;base64,{b64}" />
      <div class="hero-text">
        <h1>Digitaler Wareneingang mit KI</h1>
        <p>Lieferschein fotografieren, Daten automatisch erkennen, Bauteile spaeter per Foto wieder zuordnen.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)


def metrics() -> None:
    entries = st.session_state.entries
    total_qty = sum(int(e["quantity"]) for e in entries)
    open_count = sum(1 for e in entries if e["status"] != "Abgeschlossen")
    avg_ocr = round(sum(e.get("ocr_confidence", 0) for e in entries) / max(len(entries), 1))
    cols = st.columns(4)
    data = [("Wareneingaenge", len(entries), "digital erfasst"), ("Bauteile", total_qty, "Stueck gesamt"), ("Offen", open_count, "zu pruefen"), ("OCR Ã", f"{avg_ocr}%", "KI-Erkennung")]
    for col, (label, value, hint) in zip(cols, data):
        col.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-hint">{hint}</div></div>', unsafe_allow_html=True)


def entry_card(e: Dict, compact: bool = False) -> None:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    top = st.columns([2, 1])
    top[0].markdown(f"### {e['id']}")
    top[0].markdown(f"**{e['customer']}** Â· {e['date']} Â· Bediener: **{e.get('operator','-')}**")
    top[1].markdown(status_html(e["status"]), unsafe_allow_html=True)
    top[1].markdown(ai_html(f"OCR {e.get('ocr_confidence',0)}%"), unsafe_allow_html=True)
    c = st.columns(5)
    c[0].metric("Artikel", e["article_no"])
    c[1].metric("Menge", f"{e['quantity']} Stk.")
    c[2].metric("Masse", f"{e['length']} x {e['width']} x {e['height']}")
    c[3].metric("Poliert", e["polished"])
    c[4].metric("Schicht", e["coating"])
    if not compact:
        i1, i2, i3 = st.columns(3)
        i1.image(to_img(e["receipt_img"]), caption="Lieferschein", use_container_width=True)
        i2.image(to_img(e["parts_img"]), caption="Bauteile", use_container_width=True)
        i3.image(to_img(e["packaging_img"]), caption="Verpackung", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def dashboard() -> None:
    hero()
    metrics()
    st.write("")
    left, right = st.columns([1.2, .8])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Letzte Wareneingaenge")
        for e in st.session_state.entries[:3]:
            entry_card(e, compact=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Neuer optimierter Ablauf")
        st.markdown("""
        1. Lieferschein fotografieren  
        2. KI liest die Daten aus  
        3. Bauteile fotografieren  
        4. Verpackung fotografieren  
        5. Mitarbeiter prueft die Daten  
        6. Bediener auswaehlen und speichern  
        7. Buero kopiert Daten fuer WISO  
        8. Spaeter per Bauteilfoto wiederfinden
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
    st.write("Die Demo liest beispielhaft Daten aus dem Lieferschein und fuellt die Felder vor. In der echten Version kommt hier OCR/KI rein.")
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
    st.markdown("### 3. Daten pruefen und ergaenzen")
    col1, col2, col3 = st.columns(3)
    with col1:
        delivery_id = st.text_input("Lieferscheinnummer", value=d["id"])
        customer = st.text_input("Kunde", value=d["customer"])
        supplier = st.text_input("Lieferant", value=d["supplier"])
        article_no = st.text_input("Artikelnummer", value=d["article_no"])
    with col2:
        description = st.text_input("Bezeichnung", value=d["description"])
        quantity = st.number_input("Menge", min_value=1, value=int(d["quantity"]), step=1)
        length = st.number_input("Laenge (mm)", value=float(d["length"]))
        width = st.number_input("Breite (mm)", value=float(d["width"]))
    with col3:
        height = st.number_input("Hoehe (mm)", value=float(d["height"]))
        polished = st.radio("Poliert?", ["Ja", "Nein"], index=0 if d["polished"] == "Ja" else 1, horizontal=True)
        coated = st.radio("Beschichtet?", ["Ja", "Nein"], index=0 if d["coated"] == "Ja" else 1, horizontal=True)
        coating = st.selectbox("Beschichtung", ["Harteloxal", "Pulverbeschichtung", "Verzinkt", "Brueniert", "Keine"], index=0)
        layer = st.selectbox("Farbe / Schichtdicke", ["Schwarz / 25 um", "RAL 9005 / 80 um", "Transparent / 15 um", "Silber / 20 um", "-"], index=0)
    notes = st.text_area("Hinweise", value="Daten wurden per KI vorbereitet und vom Mitarbeiter geprueft.")
    operator = st.selectbox("Bediener auswaehlen", USERS, index=0)

    missing = []
    if receipt is None: missing.append("Lieferschein")
    if parts is None: missing.append("Bauteile")
    if packaging is None: missing.append("Verpackung")
    if missing:
        st.warning("Noch fehlende Pflichtfotos: " + ", ".join(missing))

    if st.button("Wareneingang speichern", use_container_width=True):
        st.session_state.entries.insert(0, {
            "id": delivery_id, "date": datetime.now().strftime("%d.%m.%Y, %H:%M"), "operator": operator,
            "customer": customer, "supplier": supplier, "article_no": article_no, "description": description,
            "quantity": int(quantity), "length": float(length), "width": float(width), "height": float(height),
            "polished": polished, "coated": coated, "coating": coating if coated == "Ja" else "-", "layer": layer if coated == "Ja" else "-",
            "notes": notes, "status": "Gespeichert", "ocr_confidence": int(d.get("confidence", 0)),
            "receipt_img": file_bytes(receipt) or img_bytes("demo_lieferschein.png"),
            "parts_img": file_bytes(parts) or img_bytes("demo_bauteile.png"),
            "packaging_img": file_bytes(packaging) or img_bytes("demo_verpackung.png"),
            "match": 92,
        })
        st.session_state.ai_result = None
        st.success(f"Wareneingang {delivery_id} wurde von {operator} gespeichert.")
    st.markdown('</div>', unsafe_allow_html=True)


def archive() -> None:
    st.markdown("## Archiv")
    q = st.text_input("Suche nach Kunde, Lieferschein, Artikelnummer oder Bediener")
    entries = st.session_state.entries
    if q:
        entries = [e for e in entries if q.lower() in " ".join(map(str, e.values())).lower()]
    for e in entries:
        entry_card(e)


def wiso_text(e: Dict) -> str:
    return "\t".join([e["id"], e["date"], e.get("operator", "-"), e["customer"], e["supplier"], e["article_no"], e["description"], str(e["quantity"]), f"{e['length']} x {e['width']} x {e['height']} mm", e["polished"], e["coated"], e["coating"], e["layer"], e["notes"]])


def office() -> None:
    st.markdown("## Buero / WISO")
    rows = []
    for e in st.session_state.entries:
        rows.append({"Lieferschein": e["id"], "Datum": e["date"], "Bediener": e.get("operator", "-"), "Kunde": e["customer"], "Artikelnummer": e["article_no"], "Menge": e["quantity"], "Masse": f"{e['length']} x {e['width']} x {e['height']} mm", "Beschichtung": e["coating"], "OCR": f"{e.get('ocr_confidence', 0)}%"})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    selected = st.selectbox("Datensatz fuer WISO auswaehlen", [e["id"] for e in st.session_state.entries])
    entry = next(e for e in st.session_state.entries if e["id"] == selected)
    st.code(wiso_text(entry), language="text")
    st.download_button("CSV exportieren", data=df.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name="wareneingang_wiso.csv", mime="text/csv")


def ai_search() -> None:
    st.markdown("## KI-Suche")
    left, right = st.columns([.85, 1.15])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        uploaded = st.file_uploader("Foto vom unbekannten Bauteil", type=["png", "jpg", "jpeg"], key="ai_search")
        st.image(uploaded if uploaded else ASSETS / "demo_suchteil.png", caption="Suchbild", use_container_width=True)
        start = st.button("KI-Suche starten", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        best = st.session_state.entries[0]
        st.success(f"Bester Treffer: {best['id']} - {best['customer']} - {best['match']}%")
        entry_card(best)
        st.markdown("**KI-Begruendung:** aehnliche Form, Oberflaeche, Verpackungsbild und Lieferscheindaten passen zusammen.")
        st.markdown('</div>', unsafe_allow_html=True)


def presentation() -> None:
    st.markdown("## Praesentationsbilder")
    for i in range(1, 9):
        with st.expander(f"Slide {i}"):
            st.image(ASSETS / f"slide_{i}.png", use_container_width=True)


def tech() -> None:
    st.markdown("## Echte KI spaeter anbinden")
    st.markdown("""
    Diese Demo simuliert OCR und Bild-KI. Fuer die echte Version:

    - Lieferschein-OCR: Azure Document Intelligence, Google Vision oder OpenAI Vision
    - Bildsuche: CLIP-Embeddings + Vektordatenbank
    - Cloud: Supabase Storage + PostgreSQL
    - Login: Supabase Auth
    - Treffer immer als Vorschlag anzeigen und vom Mitarbeiter bestaetigen lassen
    """)


def main() -> None:
    ensure_assets()
    css()
    init_data()
    st.sidebar.image(ASSETS / "sidebar.png", use_container_width=True)
    st.sidebar.markdown("### Pondruff / WE")
    page = st.sidebar.radio("Navigation", ["Dashboard", "Neuer Wareneingang", "Archiv", "Buero / WISO", "KI-Suche", "Praesentation", "Technik"])
    if page == "Dashboard": dashboard()
    elif page == "Neuer Wareneingang": capture()
    elif page == "Archiv": archive()
    elif page == "Buero / WISO": office()
    elif page == "KI-Suche": ai_search()
    elif page == "Praesentation": presentation()
    else: tech()


if __name__ == "__main__":
    main()