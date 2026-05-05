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
