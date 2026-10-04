from app.agent.errors import ErrorClassifier

def test_error_classification():
    # 1. Auth expired
    cat, rec = ErrorClassifier.classify("Session Expired. Please log in again.", 401)
    assert cat == ErrorClassifier.AUTH_EXPIRED
    assert "log in again" in rec

    # 2. Transient
    cat, rec = ErrorClassifier.classify("Internal Server Error (Flaky 500 Fault Injected)", 500)
    assert cat == ErrorClassifier.TRANSIENT
    assert "backoff and retry" in rec

    # 3. Slot conflict
    cat, rec = ErrorClassifier.classify("Slot conflict: Slot #1 is already booked.", 200)
    assert cat == ErrorClassifier.SLOT_CONFLICT
    assert "next available free slot" in rec

    # 4. Validation
    cat, rec = ErrorClassifier.classify("Validation Error: Expected CTC must be a plain numeric number in LPA", 400)
    assert cat == ErrorClassifier.VALIDATION
    assert "reformat input" in rec

    # 5. Selector missing
    cat, rec = ErrorClassifier.classify("Error: Link 'L99' not found.", 200)
    assert cat == ErrorClassifier.SELECTOR_MISSING
    assert "web_read" in rec

    # 6. Permission denied
    cat, rec = ErrorClassifier.classify("Action 'web_submit' is not permitted for role 'Analyst'.", 200)
    assert cat == ErrorClassifier.PERMISSION_DENIED
    assert "Do not attempt workarounds" in rec
