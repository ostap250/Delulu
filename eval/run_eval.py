import argparse
import json
from collections import defaultdict

from app import predict_messages, classify_karpman

CATEGORIES = [
    "gaslighting",
    "blame_shifting",
    "passive_aggressive",
    "triangulation",
    "verbal_aggression",
]


def load_golden(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", [])


def compute_metrics(golden_items, predictions):
    stats = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in CATEGORIES}
    false_pos = {cat: [] for cat in CATEGORIES}
    false_neg = {cat: [] for cat in CATEGORIES}
    karpman_correct = 0

    for item in golden_items:
        message_id = item["id"]
        expected = set(item.get("expected_categories", []))
        predicted = set(predictions.get(message_id, {}).get("categories", []))

        for cat in CATEGORIES:
            if cat in expected and cat in predicted:
                stats[cat]["tp"] += 1
            elif cat not in expected and cat in predicted:
                stats[cat]["fp"] += 1
                false_pos[cat].append(item)
            elif cat in expected and cat not in predicted:
                stats[cat]["fn"] += 1
                false_neg[cat].append(item)

        predicted_role, _, _ = classify_karpman(item.get("text", ""))
        if predicted_role == item.get("expected_karpman"):
            karpman_correct += 1

    return stats, false_pos, false_neg, karpman_correct


def format_metrics(stats):
    lines = []
    lines.append("Category               TP   FP   FN   Precision  Recall")
    lines.append("--------------------------------------------------------")
    for cat, counts in stats.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        lines.append(f"{cat:<22} {tp:>3}  {fp:>3}  {fn:>3}    {precision:>6.2f}   {recall:>6.2f}")
    return "\n".join(lines)


def print_top_errors(label, items_by_cat, limit=10):
    print(f"\n{label} (top {limit})")
    print("-" * 40)
    for cat in CATEGORIES:
        items = items_by_cat.get(cat, [])[:limit]
        print(f"{cat}:")
        if not items:
            print("  (none)")
            continue
        for item in items:
            text = item.get("text", "")
            print(f"  - {item.get('id')}: {text}")


def main():
    parser = argparse.ArgumentParser(description="Run rule-based eval on golden set.")
    parser.add_argument("--golden", default="eval/golden_cases.sample.json")
    args = parser.parse_args()

    golden_items = load_golden(args.golden)
    messages = [
        {"id": item["id"], "sender": item["sender"], "text": item["text"]}
        for item in golden_items
    ]

    predictions = predict_messages(messages, ignore_verbal_aggression=False)
    stats, false_pos, false_neg, karpman_correct = compute_metrics(golden_items, predictions)

    print(format_metrics(stats))
    if golden_items:
        accuracy = (karpman_correct / len(golden_items)) * 100
    else:
        accuracy = 0.0
    print(f"\nKarpman accuracy: {accuracy:.1f}% ({karpman_correct}/{len(golden_items)})")

    print_top_errors("False positives", false_pos)
    print_top_errors("False negatives", false_neg)


if __name__ == "__main__":
    main()
