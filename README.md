# Pondruff / WE Wareneingang Cloud + GPT-4.1

## Streamlit Secrets

```toml
SUPABASE_URL = "https://DEIN-PROJEKT.supabase.co"
SUPABASE_ANON_KEY = "DEIN-ANON-KEY"
OPENAI_API_KEY = "sk-..."
```

## Features

- Supabase Login
- Supabase Tabelle fuer Wareneingaenge
- Supabase Storage fuer Lieferschein, Bauteile und Verpackung
- GPT-4.1 Lieferschein-OCR
- WISO Copy/Paste


## Neu: Bauteil-KI

- Foto vom unbekannten Bauteil hochladen
- GPT-4.1 vergleicht mit gespeicherten Bauteilbildern in Supabase Storage
- Trefferliste mit Score und Begründung


## Plus 6 Update

1. Pflicht- und Plausibilitaetspruefung vor dem Speichern
2. Verbessertes Archiv mit grosser Bildansicht
3. KI Top-Trefferliste
4. Filter nach Suche, Kunde, Bediener und Status
5. HTML-Bericht pro Wareneingang zum Download
6. Statistikseite mit Auswertungen


## WISO Übergabe

Neuer Bereich:
- Wareneingang auswählen
- WISO-Datenblock kopieren
- CSV für einzelnen Auftrag herunterladen
- CSV für mehrere Treffer herunterladen
- HTML-Auftragsbericht herunterladen
- Bilder direkt gegenprüfen