import json
import os
from typing import Any, Dict, Iterable
from urllib import error, parse, request


def detect_manipulation(
    content: Any,
    *,
    allowed_categories: Iterable[str],
    fallback_result: Dict[str, Any],
    avoid_patterns: Iterable[str] = (),
    timeout_seconds: float = 8.0,
) -> Dict[str, Any]:
    """
    Analyze text/messages with Gemini and return strict JSON shape.
    Falls back to `fallback_result` on timeout/errors/invalid output.
    """
    fallback = _normalize_result(fallback_result, allowed_categories)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return fallback

    text = _to_text(content)
    if not text:
        return fallback

    avoid_list = [str(x).strip() for x in avoid_patterns if str(x).strip()]
    avoid_list = avoid_list[:5]

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{parse.quote(model)}:generateContent?key={parse.quote(api_key)}"
    )

    avoid_section = ""
    if avoid_list:
        avoid_section = (
            "Avoid over-flagging these known false-positive patterns from user feedback:\n"
            + "\n".join(f"- {item}" for item in avoid_list)
            + "\n\n"
        )

    prompt_text = (
        "You classify whether text contains manipulation patterns. Return JSON only.\n"
        "Output keys exactly: is_manipulation (bool), categories (array), "
        "confidence (0..1), explanation (short string).\n"
        f"Allowed categories: {', '.join(sorted(set(allowed_categories)))}\n"
        "Rules:\n"
        "- Use only allowed category names.\n"
        "- If uncertain, lower confidence.\n"
        "- Keep explanation under 180 characters.\n\n"
        f"{avoid_section}"
        f"Text to analyze:\n{text}"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt_text}],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "required": ["is_manipulation", "categories", "confidence", "explanation"],
                "properties": {
                    "is_manipulation": {"type": "BOOLEAN"},
                    "categories": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "confidence": {"type": "NUMBER"},
                    "explanation": {"type": "STRING"},
                },
            },
        },
    }

    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        content_text = body["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(content_text)
        normalized = _normalize_result(parsed, allowed_categories)

        if normalized["is_manipulation"] and not normalized["categories"] and fallback["categories"]:
            return fallback
        return normalized
    except (error.URLError, error.HTTPError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return fallback


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()[:5000]
    if isinstance(content, list):
        lines = []
        for item in content:
            if isinstance(item, dict):
                sender = str(item.get("sender", "Unknown")).strip()
                text = str(item.get("text", "")).strip()
                if text:
                    lines.append(f"{sender}: {text}")
            elif item:
                lines.append(str(item).strip())
        return "\n".join(lines)[:5000]
    if isinstance(content, dict):
        sender = str(content.get("sender", "Unknown")).strip()
        text = str(content.get("text", "")).strip()
        if text:
            return f"{sender}: {text}"[:5000]
    return str(content).strip()[:5000]


def _normalize_result(result: Dict[str, Any], allowed_categories: Iterable[str]) -> Dict[str, Any]:
    allowed_map = {str(x).strip().lower(): str(x).strip() for x in allowed_categories}
    safe = {
        "is_manipulation": False,
        "categories": [],
        "confidence": 0.2,
        "explanation": "No manipulation detected by current detector.",
    }
    if not isinstance(result, dict):
        return safe

    is_manipulation = bool(result.get("is_manipulation", False))
    categories_raw = result.get("categories", [])
    if not isinstance(categories_raw, list):
        categories_raw = []

    categories = []
    for item in categories_raw:
        label_raw = str(item).strip()
        label = allowed_map.get(label_raw.lower())
        if label and label not in categories:
            categories.append(label)

    confidence_raw = result.get("confidence", safe["confidence"])
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = safe["confidence"]
    confidence = max(0.0, min(1.0, confidence))

    explanation = str(result.get("explanation", safe["explanation"])).strip()
    if not explanation:
        explanation = safe["explanation"]
    explanation = explanation[:180]

    if not is_manipulation:
        categories = []

    return {
        "is_manipulation": is_manipulation,
        "categories": categories,
        "confidence": confidence,
        "explanation": explanation,
    }
