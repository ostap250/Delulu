import json
import streamlit as st

CATEGORIES = {
    "gaslighting": {
        "label": "Gaslighting",
        "keywords": [
    "you're too sensitive",
    "you are too sensitive",
    "you're overreacting",
    "you are overreacting",
    "that never happened",
    "you're remembering it wrong",
    "you are remembering it wrong",
    "you're crazy",
    "you are crazy",
    "це не було",
    "такого не було",
    "ти вигадуєш",
    "ти придумала",
    "ти придумав",
    "ти все перекручуєш",
    "ти все придумала",
    "ти все придумав",
    "ти занадто чутлива",
    "ти занадто чутливий",
    "ти перебільшуєш",
    "ти неадекват",
    "ти не при своєму розумі",
    "ти псих",
    "ти істериш",
    "ти істеричка",
    "ти не памʼятаєш",
    "ти не пам'ятаєш",
    "ти гониш",
    "ти рофлиш",
    "ти крінжиш",
    "не агрись",
        ],
    },
    "passive_aggressive": {
        "label": "Passive-Aggressive",
        "example_limit": 3,
        "keywords": [
            "i'm fine",
            "im fine",
            "whatever you want",
            "do what you want",
            "ok if you say so",
            "мені байдуже",
            "як хочеш",
            "роби що хочеш",
            "та роби",
            "ну і ладно",
            "ну добре",
            "все норм",
            "все ок",
            "як знаєш",
            "сама вирішуй",
            "сам вирішуй",
            "мені все одно",
            "без різниці",
            "ой все",
            "ясно",
            "пон",
            "ага, ясно",
            "та як хочеш",
            "мені пох",
            "мені пофіг",
            "як тобі угодно",
            "нічого, роби як хочеш",
        ],
        "dismissive_acronyms": [
            "k",
            "kk",
            "idk",
            "idc",
            "nvm",
            "smh",
            "bruh",
            "lol",
            "lmao",
            "omg",
            "wtf",
            "tf",
            "ngl",
            "fr",
            "ikr",
            "tbh",
        ],
    },
    "blame_shifting": {
        "label": "Blame-Shifting",
        "example_limit": 3,
        "keywords": [
            "it's your fault",
            "its your fault",
            "you made me",
            "because of you",
            "це через тебе",
            "ти мене змусив",
            "ти мене змусила",
            "ти винен",
            "ти винна",
            "ти сама винна",
            "ти сам винен",
            "мені довелося через тебе",
        ],
    },
    "triangulation": {
        "label": "Triangulation",
        "example_limit": 1,
        "keywords": [
            "everyone thinks",
            "people say",
            "my friends say",
            "мої друзі кажуть",
            "всі так думають",
            "навіть вони кажуть",
            "інші кажуть",
            "всі знають що",
        ],
    },
    "verbal_aggression": {
        "label": "Verbal Aggression",
        "example_limit": 3,
        "keywords": [
            "fuck you",
            "go fuck yourself",
            "shut up",
            "go to hell",
            "иди нахуй",
            "йди нахуй",
            "пішов нахуй",
            "піди нахуй",
            "нахуй",
            "сука",
            "сучка",
            "бля",
            "блять",
            "пиздець",
            "піздець",
            "fuck off",
        ],
    },
}


def extract_text(text_field):
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        parts = []
        for chunk in text_field:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict):
                value = chunk.get("text", "")
                if isinstance(value, str):
                    parts.append(value)
        return "".join(parts)
    return ""


def load_messages_from_bytes(file_bytes):
    content = file_bytes.decode("utf-8", errors="replace")
    data = json.loads(content)

    messages = []
    for item in data.get("messages", []):
        if item.get("type") != "message":
            continue
        sender = item.get("from") or "Unknown"
        text = extract_text(item.get("text", "")).strip()
        if text:
            messages.append({"sender": sender, "text": text})

    return messages


def analyze_messages(messages, ignore_verbal_aggression=False):
    results = {}
    for key in CATEGORIES:
        results[key] = {"total": 0, "by_sender": {}, "examples": []}

    prev_sender = None
    prev_text = ""

    for msg in messages:
        sender = msg["sender"]
        text = msg["text"]
        text_lower = text.lower().strip()

        for key, category in CATEGORIES.items():
            if ignore_verbal_aggression and key == "verbal_aggression":
                continue
            matched = False
            keywords = category.get("keywords", [])

            if any(k in text_lower for k in keywords):
                matched = True

            if key == "passive_aggressive" and not matched:
                acronyms = category.get("dismissive_acronyms", [])
                is_short = len(text_lower) <= 6
                is_acronym = text_lower.strip(".!?") in acronyms
                previous_context = prev_sender is not None and prev_sender != sender and len(prev_text) >= 20
                if is_short and is_acronym and previous_context:
                    matched = True

            if matched:
                results[key]["total"] += 1
                results[key]["by_sender"][sender] = results[key]["by_sender"].get(sender, 0) + 1
                limit = category.get("example_limit", 3)
                if len(results[key]["examples"]) < limit:
                    results[key]["examples"].append({"sender": sender, "text": text})

        prev_sender = sender
        prev_text = text

    return results


def build_report(file_name, messages, results, ignore_verbal_aggression=False):
    return {
        "title": "Project Mirror MVP - Telegram JSON Scan",
        "input_file": file_name,
        "messages_parsed": len(messages),
        "categories": results,
        "options": {
            "ignore_verbal_aggression": ignore_verbal_aggression,
        },
    }


st.set_page_config(page_title="Am i Delulu?", layout="centered")

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 20% 20%, #1b1f3a 0%, #0b0f1f 45%, #05070d 100%);
        color: #e8ecff;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        background:
          radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.9) 50%, transparent 51%),
          radial-gradient(1px 1px at 70% 20%, rgba(255,255,255,0.6) 50%, transparent 51%),
          radial-gradient(1.5px 1.5px at 40% 80%, rgba(255,255,255,0.7) 50%, transparent 51%),
          radial-gradient(1px 1px at 85% 65%, rgba(255,255,255,0.5) 50%, transparent 51%),
          radial-gradient(2px 2px at 10% 70%, rgba(255,255,255,0.4) 50%, transparent 51%);
        pointer-events: none;
        opacity: 0.6;
        z-index: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Am i Delulu?")
st.write("Upload Telegram JSON export (result.json) to scan for basic manipulation phrases.")

if "page" not in st.session_state:
    st.session_state.page = "upload"
if "report" not in st.session_state:
    st.session_state.report = None


def decide_most_manipulative(categories):
    totals = {}
    for data in categories.values():
        for sender, count in data.get("by_sender", {}).items():
            totals[sender] = totals.get(sender, 0) + count

    if not totals:
        return None, 0

    max_count = max(totals.values())
    top = [sender for sender, count in totals.items() if count == max_count]
    if len(top) == 1:
        return top[0], max_count
    return ", ".join(sorted(top)), max_count


def compute_sender_totals(categories):
    totals = {}
    for data in categories.values():
        for sender, count in data.get("by_sender", {}).items():
            totals[sender] = totals.get(sender, 0) + count
    return totals


if st.session_state.page == "upload":
    ignore_swears = st.checkbox(
        "We frequently use swear words and I DO NOT count it as offence",
        value=False,
    )
    uploaded_file = st.file_uploader("Upload result.json", type=["json"])

    if not uploaded_file:
        st.info("Waiting for a Telegram export file...")
    else:
        try:
            messages = load_messages_from_bytes(uploaded_file.getvalue())
        except json.JSONDecodeError:
            st.error("Invalid JSON file. Please upload a Telegram export result.json.")
            st.stop()

        results = analyze_messages(messages, ignore_verbal_aggression=ignore_swears)
        report = build_report(uploaded_file.name, messages, results, ignore_verbal_aggression=ignore_swears)
        st.session_state.report = report
        st.session_state.page = "summary"
        if hasattr(st, "rerun"):
            st.rerun()

elif st.session_state.page == "summary":
    report = st.session_state.report
    if not report:
        st.warning("No analysis found. Please upload a file first.")
        if st.button("Back to upload"):
            st.session_state.page = "upload"
        st.stop()

    st.subheader("Summary")
    st.write(f"Messages parsed: {report['messages_parsed']}")

    most_sender, most_count = decide_most_manipulative(report["categories"])
    sender_totals = compute_sender_totals(report["categories"])
    total_flags = sum(sender_totals.values())
    if most_sender:
        st.success(f"Most manipulative (by flagged messages): {most_sender} ({most_count})")
        share = round((most_count / total_flags) * 100) if total_flags else 0
        other_share = max(0, 100 - share)
        st.write(f"Manipulation share: {share}% — {most_sender} vs Others {other_share}%")
        st.markdown(
            f"""
            <div style="width: 100%; height: 16px; background: #2a2f45; border-radius: 999px; overflow: hidden;">
              <div style="width: {share}%; height: 100%; background: #ff4d6d;"></div>
              <div style="width: {other_share}%; height: 100%; background: #7b88a8;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No manipulation keywords detected, so no dominant sender yet.")

    st.markdown("### Overview")
    category_notes = {
        "gaslighting": "undermining your reality",
        "passive_aggressive": "indirect or dismissive replies",
        "blame_shifting": "shifting responsibility onto you",
        "triangulation": "using others' opinions as pressure",
        "verbal_aggression": "hostile or abusive language",
    }
    sorted_categories = sorted(
        ((key, report["categories"][key]["total"]) for key in CATEGORIES.keys()),
        key=lambda item: item[1],
        reverse=True,
    )
    top_notes = [category_notes[key] for key, count in sorted_categories if count > 0][:2]
    if most_sender and top_notes:
        st.write(
            f"In this dialogue, {most_sender} shows more patterns of {', '.join(top_notes)}. "
            "This is based on keyword matches only, not a diagnosis."
        )
    elif any(count > 0 for _, count in sorted_categories):
        st.write(
            "Some manipulation-related keywords appear in the chat, but no single person stands out clearly. "
            "This is based on keyword matches only, not a diagnosis."
        )
    else:
        st.write("No manipulation keywords detected in this chat.")

    for key, info in CATEGORIES.items():
        label = info["label"]
        data = report["categories"][key]
        ignore_verbal = report.get("options", {}).get("ignore_verbal_aggression", False)
        if ignore_verbal and key == "verbal_aggression":
            st.markdown(f"### ~~{label}~~")
            st.write("Ignored by your preference (swear words are not counted).")
            continue

        total = data["total"]
        if total == 0:
            st.markdown(f"### ~~{label}~~")
            st.write(f"Your relationship does not contain {label}.")
            percent = 0 if report["messages_parsed"] == 0 else round((total / report["messages_parsed"]) * 100)
            st.write(f"Unusuality check: {percent}% of messages flagged for {label}.")
            continue

        st.markdown(f"### {label}")
        percent = 0 if report["messages_parsed"] == 0 else round((total / report["messages_parsed"]) * 100)
        st.write(f"Flags: {total} ({percent}% of messages)")
        if data["by_sender"]:
            st.write("By sender:")
            for sender, count in data["by_sender"].items():
                st.write(f"- {sender}: {count}")
        else:
            st.write("By sender: none")

        if data["examples"]:
            st.write("Examples:")
            for example in data["examples"]:
                st.write(f"- {example['sender']}: {example['text']}")
        else:
            st.write("Examples: none")

    if st.button("Back to upload"):
        st.session_state.page = "upload"
