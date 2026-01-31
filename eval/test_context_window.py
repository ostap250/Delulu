from app import predict_messages


def test_invalidation_after_emotion_boost():
    messages = [
        {"id": "1", "sender": "A", "text": "I feel really hurt by that."},
        {"id": "2", "sender": "B", "text": "You're overreacting."},
    ]
    preds = predict_messages(messages, ignore_verbal_aggression=False)
    msg2 = preds["2"]
    assert "gaslighting" in msg2["categories"], "Expected gaslighting from context boost"
    assert msg2["severity"]["gaslighting"] >= 7, "Expected boosted severity"
    assert msg2["metadata"]["gaslighting"]["context_boosted"] is True


def test_invalidation_without_emotion_no_boost():
    messages = [
        {"id": "1", "sender": "A", "text": "Okay."},
        {"id": "2", "sender": "B", "text": "You're overreacting."},
    ]
    preds = predict_messages(messages, ignore_verbal_aggression=False)
    msg2 = preds["2"]
    assert "gaslighting" in msg2["categories"], "Base keyword should still match"
    assert msg2["severity"]["gaslighting"] == 5, "No context boost expected"
    assert msg2["metadata"].get("gaslighting") is None


def test_emotion_same_sender_no_boost():
    messages = [
        {"id": "1", "sender": "A", "text": "I feel upset."},
        {"id": "2", "sender": "A", "text": "You're overreacting."},
    ]
    preds = predict_messages(messages, ignore_verbal_aggression=False)
    msg2 = preds["2"]
    assert "gaslighting" in msg2["categories"], "Base keyword should still match"
    assert msg2["severity"]["gaslighting"] == 5, "No context boost for same sender"
    assert msg2["metadata"].get("gaslighting") is None


if __name__ == "__main__":
    test_invalidation_after_emotion_boost()
    test_invalidation_without_emotion_no_boost()
    test_emotion_same_sender_no_boost()
    print("Context window tests passed.")
