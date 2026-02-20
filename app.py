import json
import streamlit as st
import streamlit.components.v1 as components

from rules.context_window import apply_context_window_boost

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

WEIGHTS = {
    "gaslighting": 3,
    "blame_shifting": 3,
    "triangulation": 2,
    "passive_aggressive": 1,
    "verbal_aggression": 2,
}

BASE_SEVERITY = {
    "gaslighting": 5,
    "blame_shifting": 4,
    "triangulation": 3,
    "passive_aggressive": 2,
    "verbal_aggression": 4,
}

KARPMAN_RULES = {
    "Victim": [
        "why me",
        "i can't",
        "i cannot",
        "nobody cares",
        "no one cares",
        "it's not fair",
        "unfair",
        "i'm helpless",
        "i am helpless",
        "you made me feel",
        "i feel so bad",
        "мені так погано",
        "мене ніхто не розуміє",
        "мені боляче",
        "це нечесно",
        "я не можу",
        "я безсилий",
        "я безсила",
        "чому завжди я",
    ],
    "Persecutor": [
        "it's your fault",
        "its your fault",
        "you always",
        "you never",
        "because of you",
        "you made me",
        "shut up",
        "иди нахуй",
        "йди нахуй",
        "пішов нахуй",
        "ти винен",
        "ти винна",
        "ти завжди",
        "ти ніколи",
        "ненавиджу тебе",
        "ти тупий",
        "ти тупа",
    ],
    "Rescuer": [
        "i'll fix",
        "i will fix",
        "let me help",
        "i'll help",
        "i will help",
        "i'll handle",
        "i will handle",
        "you need me",
        "don't worry i'll",
        "i'll do it for you",
        "я допоможу",
        "я все вирішу",
        "я зроблю це за тебе",
        "не хвилюйся я",
        "дай я зроблю",
    ],
}

SARCASM_HINTS = [
    "lol",
    "lmao",
    "haha",
    "хаха",
    "ахаха",
    "жарт",
    "жартую",
    "сарказм",
    "😂",
    "🤣",
]


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


UKRAINIAN_HINT_CHARS = set("аеєиіїоуюяґАЕЄИІЇОУЮЯҐ")


def score_text_readability(text):
    if not text:
        return 0
    readable = sum(1 for ch in text if ch in UKRAINIAN_HINT_CHARS)
    broken = text.count("�")
    return readable - broken


def repair_garbled_text(text):
    if not text:
        return text
    candidates = [text]
    for encoding in ("latin1", "cp1251"):
        try:
            fixed = text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore")
            if fixed:
                candidates.append(fixed)
        except Exception:
            continue
    return max(candidates, key=score_text_readability)


def decode_json_bytes(file_bytes):
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


def load_messages_from_bytes(file_bytes):
    content = decode_json_bytes(file_bytes)
    data = json.loads(content)

def get_demo_messages():
    return [
        {"id": "1", "sender": "You", "text": "Hey, yesterday when you canceled last minute, it kind of hurt."},
        {"id": "2", "sender": "Alex", "text": "You're overreacting, it was just a small thing."},
        {"id": "3", "sender": "You", "text": "I just wanted a bit of notice."},
        {"id": "4", "sender": "Alex", "text": "You're too sensitive. Anyone else would be fine with it."},
        {"id": "5", "sender": "You", "text": "It happens pretty often though."},
        {"id": "6", "sender": "Alex", "text": "That never happened. You're remembering it wrong."},
        {"id": "7", "sender": "You", "text": "It did, last week too."},
        {"id": "8", "sender": "Alex", "text": "Wow, okay. If I'm such a bad person, maybe I should just stop trying."},
        {"id": "9", "sender": "You", "text": "That's not what I said."},
        {"id": "10", "sender": "Alex", "text": "Whatever. Do what you want."},
        {"id": "11", "sender": "You", "text": "I just want us to communicate better."},
        {"id": "12", "sender": "Alex", "text": "My ex never complained this much."},
        {"id": "13", "sender": "You", "text": "That feels unfair to compare."},
        {"id": "14", "sender": "Alex", "text": "Calm down. You're making drama out of nothing."},
        {"id": "15", "sender": "You", "text": "I'm not trying to fight."}
    ]


    messages = []
    for item in data.get("messages", []):
        if item.get("type") != "message":
            continue
        if any(key.startswith("forwarded_from") for key in item.keys()):
            continue
        sender = repair_garbled_text(item.get("from") or "Unknown")
        message_id = item.get("id")
        text = repair_garbled_text(extract_text(item.get("text", "")).strip())
        if text:
            messages.append({"id": message_id, "sender": sender, "text": text})

    return messages


def predict_messages(messages, ignore_verbal_aggression=False):
    predictions = {}
    prev_sender = None
    prev_text = ""

    for msg in messages:
        sender = msg["sender"]
        text = msg["text"]
        text_lower = text.lower().strip()
        categories = []
        severity = {}
        metadata = {}

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
                is_acronym = text_lower.strip(".!OK") in acronyms
                previous_context = prev_sender is not None and prev_sender != sender and len(prev_text) >= 20
                if is_short and is_acronym and previous_context:
                    matched = True

            if matched:
                categories.append(key)
                severity[key] = BASE_SEVERITY.get(key, 3)

        karpman_role, _, _ = classify_karpman(text)
        predictions[msg.get("id")] = {
            "categories": categories,
            "karpman": karpman_role,
            "severity": severity,
            "metadata": metadata,
        }

        prev_sender = sender
        prev_text = text

    return apply_context_window_boost(messages, predictions)



def analyze_messages(messages, ignore_verbal_aggression=False):
    results = {key: {"total": 0, "by_sender": {}, "examples": []} for key in CATEGORIES}
    predictions = predict_messages(messages, ignore_verbal_aggression=ignore_verbal_aggression)

    for msg in messages:
        sender = msg["sender"]
        text = msg["text"]
        message_id = msg.get("id")
        pred = predictions.get(message_id, {"categories": []})

        for key in pred["categories"]:
            results[key]["total"] += 1
            results[key]["by_sender"][sender] = results[key]["by_sender"].get(sender, 0) + 1
            limit = CATEGORIES[key].get("example_limit", 3)
            if len(results[key]["examples"]) < limit:
                results[key]["examples"].append({"sender": sender, "text": text})

    return results


def classify_karpman(text):
    if not text:
        return "None", 0.1, "empty"
    text_lower = text.lower()
    if any(hint in text_lower for hint in SARCASM_HINTS):
        return "None", 0.2, "sarcasm or joke"

    scores = {}
    for role, keywords in KARPMAN_RULES.items():
        scores[role] = sum(1 for k in keywords if k in text_lower)

    top_role = max(scores, key=scores.get)
    top_score = scores[top_role]
    if top_score == 0:
        return "None", 0.2, "no clear role cues"

    ties = [role for role, score in scores.items() if score == top_score]
    if len(ties) > 1:
        return "None", 0.3, "mixed signals"

    confidence = min(0.9, 0.5 + (0.1 * top_score))
    reasons = {
        "Victim": "self-pity or helplessness",
        "Persecutor": "blame or attack language",
        "Rescuer": "unsolicited help or fixing",
    }
    return top_role, confidence, reasons.get(top_role, "pattern match")


def build_karpman_items(messages):
    items = []
    counts = {"Victim": 0, "Persecutor": 0, "Rescuer": 0, "None": 0}
    by_sender = {}
    for msg in messages:
        role, confidence, reason = classify_karpman(msg["text"])
        sender = msg.get("sender", "Unknown")
        counts[role] = counts.get(role, 0) + 1
        sender_roles = by_sender.setdefault(
            sender, {"Victim": 0, "Persecutor": 0, "Rescuer": 0, "None": 0}
        )
        sender_roles[role] = sender_roles.get(role, 0) + 1
        items.append(
            {
                "id": msg.get("id"),
                "role": role,
                "confidence": round(confidence, 2),
                "reason": reason[:60],
            }
        )
    return items, counts, by_sender


def compute_participants(messages):
    counts = {}
    for msg in messages:
        sender = msg["sender"]
        counts[sender] = counts.get(sender, 0) + 1
    participants = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _ in participants], counts


def build_report(file_name, messages, results, ignore_verbal_aggression=False):
    participants, message_counts = compute_participants(messages)
    karpman_items, karpman_counts, karpman_by_sender = build_karpman_items(messages)
    return {
        "title": "Project Mirror MVP - Telegram JSON Scan",
        "input_file": file_name,
        "messages_parsed": len(messages),
        "categories": results,
        "participants": participants,
        "message_counts": message_counts,
        "karpman": {
            "items": karpman_items,
            "counts": karpman_counts,
            "by_sender": karpman_by_sender,
        },
        "options": {
            "ignore_verbal_aggression": ignore_verbal_aggression,
        },
    }


st.set_page_config(page_title="Am i DeluluOK", layout="centered")

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

st.title("Am i DeluluOK")
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


def compute_weighted_scores(categories, message_counts, ignore_verbal_aggression=False):
    weighted = {}
    for key, data in categories.items():
        weight = WEIGHTS.get(key, 1)
        if ignore_verbal_aggression and key == "verbal_aggression":
            weight = 0
        for sender, count in data.get("by_sender", {}).items():
            entry = weighted.setdefault(sender, {"weighted_sum": 0, "rate_per_100": 0})
            entry["weighted_sum"] += count * weight

def render_copy_button(text: str, key: str):
    safe = json.dumps(text)
    html = f"""
    <div style="display:flex; flex-direction:column; gap:6px;">
      <button id="copy-btn-{key}" style="
          background:#2a2f45; color:#e8ecff; border:1px solid #3a4060;
          padding:8px 12px; border-radius:8px; cursor:pointer;">
        ?? Copy summary
      </button>
      <div id="copy-status-{key}" style="color:#bcd1ff; font-size:0.9rem;"></div>
    </div>
    <script>
      const btn = document.getElementById("copy-btn-{key}");
      const status = document.getElementById("copy-status-{key}");
      btn.addEventListener("click", () => {{
        const text = {safe};
        navigator.clipboard.writeText(text).then(() => {{
          status.textContent = "Copied ?";
        }}).catch(() => {{
          status.textContent = "Copy failed ? open Manual copy below.";
        }});
      }});
    </script>
    """
    # JS runs client-side; Streamlit can't receive clipboard status directly here.
    components.html(html, height=70)
    return None



    return weighted


if st.session_state.page == "upload":
    ignore_swears = st.checkbox(
        "We frequently use swear words and I DO NOT count it as offence",
        value=False,
    )
    st.caption("Demo includes examples of gaslighting, blame-shifting, triangulation and passive-aggressive responses.")
    if st.button("✨ Try Demo Example"):
        demo_messages = get_demo_messages()
        results = analyze_messages(demo_messages, ignore_verbal_aggression=ignore_swears)
        report = build_report("demo", demo_messages, results, ignore_verbal_aggression=ignore_swears)
        st.session_state.report = report
        st.session_state.page = "summary"
        if hasattr(st, "rerun"):
            st.rerun()

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

    ignore_verbal = report.get("options", {}).get("ignore_verbal_aggression", False)
    sender_totals = compute_sender_totals(report["categories"])
    weighted_scores = compute_weighted_scores(
        report["categories"],
        report.get("message_counts", {}),
        ignore_verbal_aggression=ignore_verbal,
    )

    top_sender = None
    top_weight = 0
    top_rate = 0
    if weighted_scores:
        top_sender, top_data = max(weighted_scores.items(), key=lambda item: item[1]["weighted_sum"])
        top_weight = top_data["weighted_sum"]
        top_rate = top_data["rate_per_100"]

    if top_sender:
        st.success(
            f"Top flagged sender (severity-weighted): {top_sender} — {top_weight} pts ({top_rate:.1f} / 100 msgs)"
        )
        participants = report.get("participants", [])
        second_sender = next((p for p in participants if p != top_sender), None)
        second_label = second_sender or "Second participant"
        second_weight = weighted_scores.get(second_sender, {}).get("weighted_sum", 0)
        combined = top_weight + second_weight
        share = round((top_weight / combined) * 100) if combined else 0
        other_share = max(0, 100 - share)
        st.write(f"Manipulation share: {share}% — {top_sender} vs {second_label} {other_share}%")
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
    if top_sender and top_notes:
        overview_text = (
            f"In this dialogue, {top_sender} shows more patterns of {', '.join(top_notes)}. "
            "This is based on keyword matches only, not a diagnosis."
        )
    elif any(count > 0 for _, count in sorted_categories):
        overview_text = (
            "Some manipulation-related keywords appear in the chat, but no single person stands out clearly. "
            "This is based on keyword matches only, not a diagnosis."
        )
    else:
        overview_text = "No manipulation keywords detected in this chat."

    st.write(overview_text)
    karpman_by_sender = report.get("karpman", {}).get("by_sender", {})



    summary_lines = []
    if top_sender:
        summary_lines.append(
            f"Top flagged sender (severity-weighted): {top_sender} - {top_weight} pts ({top_rate:.1f} / 100 msgs)"
        )
    else:
        summary_lines.append("Top flagged sender: none")

    summary_lines.append("\nCategory counts by sender:")
    for key, info in CATEGORIES.items():
        label = info["label"]
        data = report["categories"][key]
        if not data["by_sender"]:
            summary_lines.append(f"- {label}: none")
            continue
        compact = ", ".join(f"{sender}={count}" for sender, count in data["by_sender"].items())
        summary_lines.append(f"- {label}: {compact}")

    summary_lines.append("\nKarpman roles by sender:")
    if karpman_by_sender:
        for sender, roles in karpman_by_sender.items():
            compact = ", ".join(f"{role}={count}" for role, count in roles.items())
            summary_lines.append(f"- {sender}: {compact}")
    else:
        summary_lines.append("- none")

    summary_lines.append("\nOverview:")
    summary_lines.append(overview_text)
    summary_text = "\n".join(summary_lines)
    render_copy_button(summary_text, key="summary")

    with st.expander("🧾 Manual copy (click if you don't see Copied ✅)", expanded=False):
        lines = [line.strip() for line in summary_text.split("\n") if line.strip()]
        if lines:
            st.markdown("\n".join(f"- {line}" for line in lines))
        else:
            st.markdown("- (empty summary)")
        st.text_area("Summary (select all + copy)", summary_text, height=220)

    st.markdown("### Karpman Drama Triangle")
    karpman_by_sender = report.get("karpman", {}).get("by_sender", {})

    karpman_counts = report.get("karpman", {}).get("counts", {})
    karpman_by_sender = report.get("karpman", {}).get("by_sender", {})
    st.write(
        f"Victim: {karpman_counts.get('Victim', 0)} • "
        f"Persecutor: {karpman_counts.get('Persecutor', 0)} • "
        f"Rescuer: {karpman_counts.get('Rescuer', 0)} • "
        f"None: {karpman_counts.get('None', 0)}"
    )
    if karpman_by_sender:
        for sender, roles in karpman_by_sender.items():
            ranked = sorted(
                ((role, count) for role, count in roles.items() if role != "None"),
                key=lambda item: item[1],
                reverse=True,
            )
            if ranked and ranked[0][1] > 0:
                top_role, top_count = ranked[0]
                st.write(f"{sender} might be **{top_role}** ({top_count} messages).")
            else:
                st.write(f"{sender}: no clear Karpman role detected.")

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
