import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def _db_path() -> str:
    return os.getenv("DELULU_DB_PATH", "delulu.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text_hash TEXT NOT NULL,
                model_output TEXT NOT NULL,
                rule_output TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_label INTEGER NOT NULL CHECK (user_label IN (0, 1)),
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES analysis_events(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suspected_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                model_result TEXT NOT NULL,
                final_user_label INTEGER CHECK (final_user_label IN (0, 1) OR final_user_label IS NULL),
                created_at TEXT NOT NULL
            )
            """
        )


def apply_data_retention(retention_days: int) -> None:
    if retention_days <= 0:
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute("DELETE FROM feedback_labels WHERE created_at < ?", (cutoff,))
        conn.execute("DELETE FROM suspected_submissions WHERE created_at < ?", (cutoff,))
        conn.execute("DELETE FROM analysis_events WHERE created_at < ?", (cutoff,))


def compute_input_text_hash(messages: List[Dict[str, Any]]) -> str:
    normalized = [
        {
            "sender": str(msg.get("sender", "")).strip(),
            "text": str(msg.get("text", "")).strip(),
        }
        for msg in messages
    ]
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def store_analysis_event(
    *,
    input_text_hash: str,
    model_output: Dict[str, Any],
    rule_output: Dict[str, Any],
) -> int:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_events (input_text_hash, model_output, rule_output, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                input_text_hash,
                json.dumps(model_output, ensure_ascii=False),
                json.dumps(rule_output, ensure_ascii=False),
                created_at,
            ),
        )
        _append_log(
            "analysis_event",
            {"event_id": int(cur.lastrowid), "input_text_hash": input_text_hash},
        )
        return int(cur.lastrowid)


def store_feedback_label(*, event_id: int, user_label: bool, note: Optional[str] = None) -> int:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO feedback_labels (event_id, user_label, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (event_id, 1 if user_label else 0, note, created_at),
        )
        _append_log(
            "feedback_label",
            {"feedback_id": int(cur.lastrowid), "event_id": event_id, "user_label": bool(user_label), "note": note},
        )
        return int(cur.lastrowid)


def store_suspected_submission(
    *,
    raw_text: str,
    model_result: Dict[str, Any],
    final_user_label: Optional[bool] = None,
) -> int:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    label_value = None if final_user_label is None else (1 if final_user_label else 0)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO suspected_submissions (raw_text, model_result, final_user_label, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                raw_text,
                json.dumps(model_result, ensure_ascii=False),
                label_value,
                created_at,
            ),
        )
        _append_log(
            "suspected_submission",
            {"submission_id": int(cur.lastrowid), "has_final_label": final_user_label is not None},
        )
        return int(cur.lastrowid)


def update_suspected_submission_label(*, submission_id: int, final_user_label: bool) -> None:
    label_value = 1 if final_user_label else 0
    with _connect() as conn:
        conn.execute(
            """
            UPDATE suspected_submissions
            SET final_user_label = ?
            WHERE id = ?
            """,
            (label_value, submission_id),
        )
    _append_log(
        "suspected_submission_label_update",
        {"submission_id": submission_id, "final_user_label": bool(final_user_label)},
    )


def get_false_positive_memories(query_text: str, limit: int = 3) -> List[str]:
    """
    Return similar past false-positive examples to avoid over-flagging.
    Sources:
    - suspected_submissions with final_user_label = 0
    - feedback_labels note payloads containing text=
    """
    query_text = (query_text or "").strip()
    if not query_text:
        return []

    candidates: List[str] = []
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT raw_text
            FROM suspected_submissions
            WHERE final_user_label = 0
            ORDER BY id DESC
            LIMIT 200
            """
        ).fetchall()
        candidates.extend(str(r[0]).strip() for r in rows if r and r[0])

        note_rows = conn.execute(
            """
            SELECT note
            FROM feedback_labels
            WHERE user_label = 0 AND note IS NOT NULL
            ORDER BY id DESC
            LIMIT 400
            """
        ).fetchall()
        for row in note_rows:
            note = str(row[0] or "").strip()
            extracted = _extract_text_from_note(note)
            if extracted:
                candidates.append(extracted)

    # Deduplicate while preserving recency.
    seen = set()
    unique_candidates = []
    for text in candidates:
        key = text.lower()
        if key not in seen:
            seen.add(key)
            unique_candidates.append(text)

    scored = []
    for text in unique_candidates:
        score = _jaccard_similarity(query_text, text)
        if score > 0:
            scored.append((score, text))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in scored[: max(0, limit)]]


def get_rule_feedback_adjustments(categories: List[str]) -> Dict[str, float]:
    """
    Build per-category multiplier from feedback history.
    - 1.0 means no adjustment.
    - Lower values reduce rule impact when users often mark that category as false.
    """
    adjustments = {key: 1.0 for key in categories}
    totals = {key: 0 for key in categories}
    false_counts = {key: 0 for key in categories}

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT user_label, note
            FROM feedback_labels
            WHERE note IS NOT NULL
            """
        ).fetchall()

    for user_label_raw, note_raw in rows:
        note = str(note_raw or "")
        category = _extract_category_from_note(note)
        if not category or category not in totals:
            continue
        totals[category] += 1
        if int(user_label_raw) == 0:
            false_counts[category] += 1

    for key in categories:
        total = totals[key]
        if total == 0:
            continue
        false_ratio = false_counts[key] / total
        # Cap to keep behavior stable: 0.5..1.0
        adjustments[key] = max(0.5, 1.0 - (0.5 * false_ratio))

    return adjustments


def get_quality_metrics() -> Dict[str, Any]:
    with _connect() as conn:
        feedback_rows = conn.execute(
            "SELECT id, event_id, user_label, note FROM feedback_labels ORDER BY id DESC"
        ).fetchall()
        event_rows = conn.execute("SELECT id, model_output FROM analysis_events").fetchall()
        submission_rows = conn.execute("SELECT id, model_result FROM suspected_submissions").fetchall()

    feedback_volume = len(feedback_rows)
    false_positive_count = sum(1 for _, _, user_label, _ in feedback_rows if int(user_label) == 0)
    false_positive_rate = (false_positive_count / feedback_volume) if feedback_volume else 0.0

    events_by_id: Dict[int, Dict[str, Any]] = {}
    for event_id_raw, model_output_raw in event_rows:
        try:
            events_by_id[int(event_id_raw)] = json.loads(model_output_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

    submissions_by_id: Dict[int, Dict[str, Any]] = {}
    for submission_id_raw, model_result_raw in submission_rows:
        try:
            submissions_by_id[int(submission_id_raw)] = json.loads(model_result_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

    agreements = 0
    comparable = 0
    for _, event_id_raw, user_label_raw, note_raw in feedback_rows:
        user_label = bool(int(user_label_raw))
        note = str(note_raw or "")
        category = _extract_category_from_note(note)
        submission_id = _extract_submission_id_from_note(note)

        predicted_value: Optional[bool] = None
        if category:
            event_model = events_by_id.get(int(event_id_raw), {})
            predicted_value = _event_predicted_category(event_model, category)
        elif submission_id is not None:
            model_result = submissions_by_id.get(submission_id, {})
            llm_result = model_result.get("llm_result", {})
            predicted_value = bool(llm_result.get("is_manipulation", False))
        else:
            event_model = events_by_id.get(int(event_id_raw), {})
            predicted_value = _event_predicted_any(event_model)

        if predicted_value is None:
            continue
        comparable += 1
        if predicted_value == user_label:
            agreements += 1

    agreement_rate = (agreements / comparable) if comparable else 0.0
    return {
        "feedback_volume": feedback_volume,
        "false_positive_rate": false_positive_rate,
        "agreement_rate": agreement_rate,
        "agreement_comparable": comparable,
    }


def _extract_category_from_note(note: str) -> Optional[str]:
    match = re.search(r"category=([a-z_]+)", note)
    if not match:
        return None
    return match.group(1).strip()


def _extract_text_from_note(note: str) -> Optional[str]:
    match = re.search(r"text=(.+)$", note)
    if not match:
        return None
    value = match.group(1).strip()
    if not value:
        return None
    return value[:500]


def _extract_submission_id_from_note(note: str) -> Optional[int]:
    match = re.search(r"suspected_submission_id=(\d+)", note)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _event_predicted_category(event_model: Dict[str, Any], category: str) -> Optional[bool]:
    if not isinstance(event_model, dict):
        return None
    for _, payload in event_model.items():
        if isinstance(payload, dict):
            categories = payload.get("categories", [])
            if isinstance(categories, list) and category in categories:
                return True
    return False


def _event_predicted_any(event_model: Dict[str, Any]) -> Optional[bool]:
    if not isinstance(event_model, dict):
        return None
    for _, payload in event_model.items():
        if isinstance(payload, dict) and bool(payload.get("is_manipulation", False)):
            return True
    return False


def _append_log(event_type: str, payload: Dict[str, Any]) -> None:
    log_path = os.getenv("DELULU_LOG_PATH", "delulu_metrics.log")
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event_type": event_type,
        "payload": payload,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # Non-blocking logging.
        return


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-zA-Z0-9']+", text.lower()))


def _jaccard_similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    intersection = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return 0.0
    return intersection / union
