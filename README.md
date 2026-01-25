# Am i Delulu?

Minimal Streamlit MVP that scans Telegram JSON exports for manipulation patterns.

## What it does
- Upload `result.json` from Telegram export
- Detects keyword-based patterns (gaslighting, passive-aggressive, blame-shifting, triangulation, verbal aggression)
- Shows a simple summary and examples

## What it ignores
- Forwarded messages (`forwarded_from*` fields are skipped)
- Optional: verbal aggression when you check the swear-words checkbox

## Run locally
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Input format
Export a Telegram chat as JSON. This app expects a file like `result.json` that has a `messages` array with fields:
- `type: "message"`
- `from` (sender)
- `text` (string or list of entities)

## Notes
This is a keyword matcher, not a diagnosis.
