from __future__ import annotations

import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from PIL import Image

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"


def create_placeholder_image(path: Path, title: str, subtitle: str = "Demo-Bild") -> None:
    """Erstellt automatisch ein Platzhalterbild, wenn Assets auf Streamlit Cloud fehlen."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1600, 900), (7, 8, 10))
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 84)
            font_mid = ImageFont.truetype("DejaVuSans.ttf", 42)
        except Exception:
            font_big = ImageFont.load_default()
            font_mid = ImageFont.load_default()
        draw.rounded_rectangle((40, 40, 1560, 860), radius=42, outline=(220, 0, 0), width=4, fill=(18, 22, 26))
        draw.text((90, 110), "Pondruff / WE", fill=(255, 255, 255), font=font_big)
        draw.text((620, 110), "WAR,ENEINGANGS-TOOL".replace(",", ""), fill=(230, 0, 0), font=font_mid)
        draw.line((90, 240, 580, 240), fill=(230, 0, 0), width=6)
        draw.text((90, 310), title, fill=(255, 255, 255), font=font_big)
        draw.text((90, 430), subtitle, fill=(190, 198, 205), font=font_mid)
        draw.rounded_rectangle((1020, 210, 1450, 760), radius=34, outline=(80, 85, 90), width=5, fill=(5, 6, 8))
        draw.rounded_rectangle((1060, 260, 1410, 720), radius=22, fill=(18, 22, 26), outline=(60, 65, 70), width=3)
        for i, txt in enumerate(["Lieferschein", "Bauteile", "Verpackung"]):
            y = 310 + i*110
            draw.rounded_rectangle((1090, y, 1380, y+72), radius=16, fill=(28, 34, 40), outline=(230, 0, 0), width=2)
            draw.text((1120, y+18), txt, fill=(255, 255, 255), font=font_mid)
        img.save(path)
    except Exception:
        pass


def ensure_assets() -> None:
    """Macht die App robust: fehlende Bilder werden automatisch erzeugt statt FileNotFoundError."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    needed = {
        "wareneingang.png": ("Digitaler Wareneingang mit KI", "3 Fotos. Alles dokumentiert. KI-gestützt."),
        "demo_lieferschein.png": ("Lieferschein", "Beispiel-Lieferschein für die Demo"),
        "demo_bauteile.png": ("Bauteilfotos", "Beispielbilder der Bauteile"),
        "demo_verpackung.png": ("Verpackungsmaterial", "Verpackung wird mit dokumentiert"),
        "demo_suchteil.png": ("KI-Suchbild", "Unbekanntes Bauteil fotografieren"),
        "demo_buero.png": ("Bürozugriff", "Alle Wareneingänge am PC verfügbar"),
        "slide_1.png": ("Slide 1", "Titel und App-Übersicht"),
        "slide_2.png": ("Slide 2", "Das Problem"),
        "slide_3.png": ("Slide 3", "In 3 Schritten erfassen"),
        "slide_4.png": ("Slide 4", "Daten direkt erfassen"),
        "slide_5.png": ("Slide 5", "KI-Zuordnung"),
        "slide_6.png": ("Slide 6", "Bürozugriff"),
        "slide_7.png": ("Slide 7", "Copy & Paste für WISO"),
        "slide_8.png": ("Slide 8", "Vorteile"),
    }
    for name, (title, subtitle) in needed.items():
        path = ASSETS / name
        if not path.exists():
            create_placeholder_image(path, title, subtitle)


ensure_assets()

st.set_page_config(
    page_title="Pondruff / WE Wareneingangs-Tool",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #050607;
            --card: rgba(18, 22, 26, 0.92);
            --card2: rgba(26, 30, 35, 0.95);
            --line: rgba(255,255,255,.11);
            --text: #f7f7f7;
            --muted: #a6adb5;
            --red: #e50909;
            --green: #50d23c;
            --amber: #ffb020;
        }
        .stApp { background: radial-gradient(circle at top right, rgba(180,0,0,.22), transparent 32%), linear-gradient(135deg, #030405 0%, #0b0f13 52%, #040405 100%); color: var(--text); }
        [data-testid="stSidebar"] { background: #060708; border-right: 1px solid var(--line); }
        h1, h2, h3 { letter-spacing: -.03em; }
        .hero { border: 1px solid var(--line); border-radius: 28px; overflow:hidden; box-shadow: 0 24px 80px rgba(0,0,0,.45); margin-bottom: 1.2rem; }
        .hero img { display:block; width:100%; }
        .subhero { padding: 20px 24px; background: linear-gradient(90deg, rgba(14,16,19,.95), rgba(100,0,0,.28)); border-top: 1px solid var(--line); }
        .subhero h1 { margin:0; font-size: 34px; color:#fff; }
        .subhero p { margin:.35rem 0 0; color:var(--muted); font-size: 18px; }
        .metric-card { background: var(--card); border:1px solid var(--line); border-radius: 24px; padding: 22px; box-shadow: 0 16px 48px rgba(0,0,0,.28); }
        .metric-card .label { color: var(--muted); font-size: 14px; }
        .metric-card .value { color: #fff; font-weight: 900; font-size: 38px; line-height: 1; margin-top:8px; }
        .metric-card .hint { color: var(--red); font-weight: 700; font-size:13px; margin-top:10px; }
        .glass { background: var(--card); border:1px solid var(--line); border-radius: 26px; padding: 22px; box-shadow: 0 18px 70px rgba(0,0,0,.28); }
        .glass-tight { background: var(--card2); border:1px solid var(--line); border-radius: 18px; padding: 14px; }
        .tag { display:inline-block; padding:6px 10px; border-radius:999px; margin:3px; font-size:12px; background: rgba(229,9,9,.18); color:#ffd0d0; border:1px solid rgba(229,9,9,.35); }
        .status { display:inline-flex; align-items:center; padding:7px 11px; border-radius:999px; font-weight:800; font-size:12px; }
        .ok { background:rgba(80,210,60,.16); color:#aaff9b; border:1px solid rgba(80,210,60,.35); }
        .warn { background:rgba(255,176,32,.16); color:#ffd37a; border:1px solid rgba(255,176,32,.35); }
        .bad { background:rgba(229,9,9,.18); color:#ffb8b8; border:1px solid rgba(229,9,9,.4); }
        .small { color: var(--muted); font-size: 14px; }
        .big-red { color: var(--red); font-weight: 900; }
        .divider { height:1px; background:var(--line); margin:16px 0; }
        .copybox { background:#050607; border:1px solid rgba(229,9,9,.35); border-radius:18px; padding:12px; }
        .stButton > button, .stDownloadButton > button { border-radius: 14px !important; border: 1px solid rgba(229,9,9,.45) !important; background: linear-gradient(180deg, #f01212, #b80000) !important; color: white !important; font-weight: 800 !important; min-height: 42px; }
        .stButton > button:hover, .stDownloadButton > button:hover { filter: brightness(1.08); border-color:#ff4444 !important; }
        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div { background-color: rgba(255,255,255,.055) !important; color: white !important; border-color: rgba(255,255,255,.12) !important; border-radius: 14px !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { border-radius: 999px; padding: 10px 18px; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1); }
        .stTabs [aria-selected="true"] { background: rgba(229,9,9,.24) !important; color:#fff !important; border-color: rgba(229,9,9,.55); }
        div[data-testid="stFileUploader"] { background: rgba(255,255,255,.04); border:1px dashed rgba(255,255,255,.18); border-radius: 22px; padding: 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_hero() -> None:
    img64 = image_to_base64(ASSETS / "wareneingang.png")
    st.markdown(
        f"""
        <div class="hero">
          <img src="data:image/png;base64,{img64}" />
          <div class="subhero">
            <h1>Digitaler Wareneingang mit KI</h1>
            <p>3 Fotos. Alle Daten. Bürozugriff. Copy & Paste für WISO. KI-Zuordnung per Bauteilfoto.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_html(status: str) -> str:
    cls = "ok" if status in ["Abgeschlossen", "Gespeichert"] else "warn" if "Prüfung" in status else "bad"
    return f'<span class="status {cls}">{status}</span>'


def load_image_bytes(name: str) -> bytes:
    return (ASSETS / name).read_bytes()


def init_data() -> None:
    if "entries" in st.session_state:
        return
    st.session_state.entries = [
        {
            "id": "LS-2024-04578",
            "date": "24.05.2024, 09:15",
            "customer": "Mustertechnik GmbH",
            "supplier": "Elektronik Komponenten AG",
            "article_no": "ART-123456",
            "description": "Präzisionsteil XY",
            "quantity": 25,
            "length": 120.50,
            "width": 80.25,
            "height": 45.00,
            "polished": "Ja",
            "coated": "Ja",
            "coating": "Harteloxal",
            "layer": "Schwarz / 25 µm",
            "notes": "Keine Kanten brechen. Ware vollständig erfasst.",
            "status": "Abgeschlossen",
            "receipt_img": load_image_bytes("demo_lieferschein.png"),
            "parts_img": load_image_bytes("demo_bauteile.png"),
            "packaging_img": load_image_bytes("demo_verpackung.png"),
            "match": 92,
        },
        {
            "id": "LS-2024-04577",
            "date": "24.05.2024, 08:32",
            "customer": "ABC Engineering",
            "supplier": "Frästeile Nord GmbH",
            "article_no": "ART-987654",
            "description": "Gehäuseteil AB",
            "quantity": 10,
            "length": 95.00,
            "width": 60.00,
            "height": 30.00,
            "polished": "Nein",
            "coated": "Ja",
            "coating": "Pulverbeschichtung",
            "layer": "RAL 9005 / 80 µm",
            "notes": "Oberfläche prüfen, kleiner Kratzer an Verpackung.",
            "status": "Prüfung offen",
            "receipt_img": load_image_bytes("demo_lieferschein.png"),
            "parts_img": load_image_bytes("demo_bauteile.png"),
            "packaging_img": load_image_bytes("demo_verpackung.png"),
            "match": 67,
        },
        {
            "id": "LS-2024-04576",
            "date": "23.05.2024, 14:21",
            "customer": "Precision Parts AG",
            "supplier": "Metallbau Weber",
            "article_no": "ART-555666",
            "description": "Befestigungsplatte",
            "quantity": 50,
            "length": 200.00,
            "width": 100.00,
            "height": 12.00,
            "polished": "Ja",
            "coated": "Nein",
            "coating": "-",
            "layer": "-",
            "notes": "Direkt für Büro freigegeben.",
            "status": "Abgeschlossen",
            "receipt_img": load_image_bytes("demo_lieferschein.png"),
            "parts_img": load_image_bytes("demo_bauteile.png"),
            "packaging_img": load_image_bytes("demo_verpackung.png"),
            "match": 45,
        },
    ]


def bytes_to_img(data: bytes):
    return Image.open(io.BytesIO(data))


def render_metrics() -> None:
    entries = st.session_state.entries
    open_checks = sum(1 for e in entries if e["status"] != "Abgeschlossen")
    total_qty = sum(int(e["quantity"]) for e in entries)
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Wareneingänge", len(entries), "digital erfasst"),
        ("Bauteile", total_qty, "Stück gesamt"),
        ("Offene Prüfung", open_checks, "noch zu klären"),
        ("WISO-ready", len(entries), "kopierbare Datensätze"),
    ]
    for col, (label, value, hint) in zip([c1, c2, c3, c4], cards):
        col.markdown(f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div><div class="hint">{hint}</div></div>', unsafe_allow_html=True)


def render_entry_card(entry: Dict, compact: bool = False) -> None:
    with st.container(border=False):
        st.markdown('<div class="glass-tight">', unsafe_allow_html=True)
        top = st.columns([2.2, 1])
        top[0].markdown(f"### {entry['id']}")
        top[0].markdown(f"**{entry['customer']}** · {entry['date']}")
        top[1].markdown(status_html(entry["status"]), unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        cols = st.columns(4)
        cols[0].metric("Artikel", entry["article_no"])
        cols[1].metric("Menge", f"{entry['quantity']} Stk.")
        cols[2].metric("Maße", f"{entry['length']} × {entry['width']} × {entry['height']}")
        cols[3].metric("Schicht", entry["layer"])
        if not compact:
            i1, i2, i3 = st.columns(3)
            i1.image(bytes_to_img(entry["receipt_img"]), caption="Lieferschein", use_container_width=True)
            i2.image(bytes_to_img(entry["parts_img"]), caption="Bauteile", use_container_width=True)
            i3.image(bytes_to_img(entry["packaging_img"]), caption="Verpackung", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


def dashboard() -> None:
    show_hero()
    render_metrics()
    st.write("")
    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.subheader("Letzte Wareneingänge")
        for entry in st.session_state.entries[:3]:
            render_entry_card(entry, compact=True)
            st.write("")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.subheader("So läuft der Prozess")
        st.markdown(
            """
            **1. Lieferschein fotografieren**  
            **2. Bauteile fotografieren**  
            **3. Verpackungsmaterial fotografieren**  
            **4. Daten ergänzen:** Artikelnummer, Menge, Maße, Polieren, Beschichtung  
            **5. Büro kann Daten prüfen und für WISO kopieren**  
            **6. KI findet später die Zuordnung per Bauteilfoto**
            """
        )
        st.image(ASSETS / "slide_1.png", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


def file_to_bytes(uploaded) -> Optional[bytes]:
    if uploaded is None:
        return None
    return uploaded.getvalue()


def capture() -> None:
    st.markdown("## Neuen Wareneingang erfassen")
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("### 1. Die 3 Pflichtfotos")
    c1, c2, c3 = st.columns(3)
    receipt = c1.file_uploader("📄 Lieferschein fotografieren", type=["png", "jpg", "jpeg"], key="receipt_upload")
    parts = c2.file_uploader("🔩 Bauteile fotografieren", type=["png", "jpg", "jpeg"], key="parts_upload")
    packaging = c3.file_uploader("📦 Verpackungsmaterial fotografieren", type=["png", "jpg", "jpeg"], key="packaging_upload")

    p1, p2, p3 = st.columns(3)
    p1.image(receipt if receipt else ASSETS / "demo_lieferschein.png", caption="Vorschau Lieferschein", use_container_width=True)
    p2.image(parts if parts else ASSETS / "demo_bauteile.png", caption="Vorschau Bauteile", use_container_width=True)
    p3.image(packaging if packaging else ASSETS / "demo_verpackung.png", caption="Vorschau Verpackung", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("### 2. Daten direkt im Wareneingang eintragen")
    col1, col2, col3 = st.columns(3)
    with col1:
        customer = st.text_input("Kunde", value="Mustertechnik GmbH")
        supplier = st.text_input("Lieferant", value="Elektronik Komponenten AG")
        article_no = st.text_input("Artikelnummer", value="ART-123456")
        description = st.text_input("Bezeichnung", value="Präzisionsteil XY")
    with col2:
        quantity = st.number_input("Menge", min_value=1, value=25, step=1)
        length = st.number_input("Länge (mm)", value=120.50)
        width = st.number_input("Breite (mm)", value=80.25)
        height = st.number_input("Höhe (mm)", value=45.00)
    with col3:
        polished = st.radio("Poliert?", ["Ja", "Nein"], horizontal=True)
        coated = st.radio("Beschichtet?", ["Ja", "Nein"], horizontal=True)
        coating = st.selectbox("Schicht / Beschichtung", ["Harteloxal", "Pulverbeschichtung", "Verzinkt", "Brüniert", "Keine"])
        layer = st.selectbox("Farbe / Schichtdicke", ["Schwarz / 25 µm", "RAL 9005 / 80 µm", "Transparent / 15 µm", "Silber / 20 µm", "-"])
    notes = st.text_area("Weitere Hinweise", value="Keine Kanten brechen. Bitte für Büro/WISO prüfen.")

    if st.button("✅ Wareneingang speichern", use_container_width=True):
        new_id = f"LS-{datetime.now().strftime('%Y')}-{len(st.session_state.entries)+4578:05d}"
        st.session_state.entries.insert(0, {
            "id": new_id,
            "date": datetime.now().strftime("%d.%m.%Y, %H:%M"),
            "customer": customer,
            "supplier": supplier,
            "article_no": article_no,
            "description": description,
            "quantity": int(quantity),
            "length": float(length),
            "width": float(width),
            "height": float(height),
            "polished": polished,
            "coated": coated,
            "coating": coating if coated == "Ja" else "-",
            "layer": layer if coated == "Ja" else "-",
            "notes": notes,
            "status": "Gespeichert",
            "receipt_img": file_to_bytes(receipt) or load_image_bytes("demo_lieferschein.png"),
            "parts_img": file_to_bytes(parts) or load_image_bytes("demo_bauteile.png"),
            "packaging_img": file_to_bytes(packaging) or load_image_bytes("demo_verpackung.png"),
            "match": 92,
        })
        st.success(f"Wareneingang {new_id} wurde gespeichert. Er ist sofort im Bürobereich und in der KI-Suche sichtbar.")
    st.markdown('</div>', unsafe_allow_html=True)


def archive() -> None:
    st.markdown("## Archiv & Details")
    search = st.text_input("Suchen nach Kunde, Lieferschein, Artikelnummer oder Bezeichnung", placeholder="z. B. ART-123456 oder Mustertechnik")
    entries = st.session_state.entries
    if search:
        q = search.lower()
        entries = [e for e in entries if q in " ".join(map(str, e.values())).lower()]
    for entry in entries:
        render_entry_card(entry)
        st.write("")


def wiso_text(entry: Dict) -> str:
    return "\t".join([
        entry["id"],
        entry["customer"],
        entry["supplier"],
        entry["article_no"],
        entry["description"],
        str(entry["quantity"]),
        f"{entry['length']} x {entry['width']} x {entry['height']} mm",
        entry["polished"],
        entry["coated"],
        entry["coating"],
        entry["layer"],
        entry["notes"],
    ])


def office() -> None:
    st.markdown("## Bürozugriff & Copy/Paste für WISO")
    st.markdown("Alle Wareneingänge sind hier als Büroansicht sichtbar. Die Daten können direkt kopiert und in WISO eingefügt werden.")
    st.image(ASSETS / "demo_buero.png", caption="Beispiel: Büroansicht am PC", use_container_width=True)

    df = pd.DataFrame([
        {
            "Lieferschein": e["id"],
            "Kunde": e["customer"],
            "Artikelnummer": e["article_no"],
            "Bezeichnung": e["description"],
            "Menge": e["quantity"],
            "Maße": f"{e['length']} x {e['width']} x {e['height']} mm",
            "Poliert": e["polished"],
            "Beschichtet": e["coated"],
            "Schicht": e["coating"],
            "Farbe/Schichtdicke": e["layer"],
            "Status": e["status"],
        }
        for e in st.session_state.entries
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

    selected = st.selectbox("Datensatz für WISO auswählen", [e["id"] for e in st.session_state.entries])
    entry = next(e for e in st.session_state.entries if e["id"] == selected)
    st.markdown("### Copy & Paste Datenblock")
    st.markdown("Klicke rechts oben im Codefeld auf **Copy** und füge den Inhalt in WISO oder Excel ein.")
    st.code(wiso_text(entry), language="text")

    csv = df.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button("⬇️ CSV für Büro exportieren", data=csv, file_name="wareneingaenge_wiso_export.csv", mime="text/csv")


def ai_search() -> None:
    st.markdown("## KI-Suche: Bauteil fotografieren und Zuordnung finden")
    left, right = st.columns([0.85, 1.15])
    with left:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown("### Suchfoto")
        uploaded = st.file_uploader("Foto vom unbekannten Bauteil hochladen", type=["png", "jpg", "jpeg"], key="ai_upload")
        st.image(uploaded if uploaded else ASSETS / "demo_suchteil.png", caption="Beispiel-Suchbild", use_container_width=True)
        start = st.button("🔎 KI-Suche starten", use_container_width=True)
        st.markdown("""
        **Demo-Ablauf:**  
        1. Bildmerkmale erkennen  
        2. Wareneingänge durchsuchen  
        3. Lieferschein, Bauteile und Verpackung anzeigen
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        if start or True:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.markdown("### Treffer gefunden")
            best = st.session_state.entries[0]
            st.success(f"{best['match']}% Übereinstimmung: {best['id']} · {best['customer']}")
            render_entry_card(best)
            st.markdown("### Weitere mögliche Treffer")
            for e in st.session_state.entries[1:3]:
                st.markdown(f"**{e['id']}** · {e['customer']} · Treffer: **{e['match']}%**")
            st.markdown('</div>', unsafe_allow_html=True)


def presentation() -> None:
    st.markdown("## Präsentationsbilder im App-Design")
    st.markdown("Diese Screens sind als visuelle Erklärung in der Demo enthalten.")
    slides = [
        ("Slide 1 – Titel", "slide_1.png"),
        ("Slide 2 – Problem", "slide_2.png"),
        ("Slide 3 – 3 Fotos", "slide_3.png"),
        ("Slide 4 – Daten erfassen", "slide_4.png"),
        ("Slide 5 – KI-Zuordnung", "slide_5.png"),
        ("Slide 6 – Bürozugriff", "slide_6.png"),
        ("Slide 7 – WISO Copy & Paste", "slide_7.png"),
        ("Slide 8 – Vorteile", "slide_8.png"),
    ]
    for title, name in slides:
        with st.expander(title, expanded=False):
            st.image(ASSETS / name, use_container_width=True)


def main() -> None:
    css()
    init_data()
    st.sidebar.image(ASSETS / "wareneingang.png", use_container_width=True)
    st.sidebar.markdown("### Pondruff / WE")
    st.sidebar.markdown("**Wareneingangs-Tool Demo**")
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Neuer Wareneingang", "Archiv", "Büro / WISO", "KI-Suche", "Präsentation"],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Demo ohne echte Cloud. Daten bleiben während der Streamlit-Sitzung erhalten.")

    if page == "Dashboard":
        dashboard()
    elif page == "Neuer Wareneingang":
        capture()
    elif page == "Archiv":
        archive()
    elif page == "Büro / WISO":
        office()
    elif page == "KI-Suche":
        ai_search()
    else:
        presentation()


if __name__ == "__main__":
    main()
