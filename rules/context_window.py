EMOTION_OR_COMPLAINT_MARKERS = [
    "i feel",
    "it hurts",
    "that hurt",
    "i'm upset",
    "i am upset",
    "i'm sad",
    "i am sad",
    "i'm angry",
    "i am angry",
    "i don't like",
    "please stop",
    "this is not ok",
    "it bothers me",
    "i'm uncomfortable",
    "i am uncomfortable",
    "мені боляче",
    "мені неприємно",
    "мене це дратує",
    "мені сумно",
    "мені образливо",
    "мені не ок",
    "будь ласка, не",
    "мені дискомфортно",
]

INVALIDATION_MARKERS = [
    "you're too sensitive",
    "you are too sensitive",
    "you're overreacting",
    "you are overreacting",
    "calm down",
    "you're crazy",
    "you are crazy",
    "that never happened",
    "you're imagining things",
    "stop being dramatic",
    "ти занадто чутлива",
    "ти занадто чутливий",
    "ти перебільшуєш",
    "ти вигадуєш",
    "заспокойся",
    "ти божевільна",
    "ти божевільний",
    "цього не було",
    "не драматизуй",
]


def apply_context_window_boost(messages, per_message_results):
    for idx, msg in enumerate(messages):
        message_id = msg.get("id")
        current = per_message_results.get(message_id)
        if not current:
            continue

        text = (msg.get("text") or "").lower()
        if not text:
            continue

        if not any(marker in text for marker in INVALIDATION_MARKERS):
            continue

        sender = msg.get("sender")
        has_emotion_context = False
        for offset in (1, 2):
            prev_idx = idx - offset
            if prev_idx < 0:
                continue
            prev_msg = messages[prev_idx]
            if prev_msg.get("sender") == sender:
                continue
            prev_text = (prev_msg.get("text") or "").lower()
            if any(marker in prev_text for marker in EMOTION_OR_COMPLAINT_MARKERS):
                has_emotion_context = True
                break

        if not has_emotion_context:
            continue

        categories = current.setdefault("categories", [])
        if "gaslighting" not in categories:
            categories.append("gaslighting")

        severity = current.setdefault("severity", {})
        base = severity.get("gaslighting", 5)
        severity["gaslighting"] = min(10, base + 2)

        metadata = current.setdefault("metadata", {})
        metadata["gaslighting"] = {
            "context_boosted": True,
            "context_window": 2,
        }

    return per_message_results
