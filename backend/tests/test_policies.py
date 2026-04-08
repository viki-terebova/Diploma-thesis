from ariadne_doc_assistant.core.policies import redact_text


def test_redaction() -> None:
    raw = """
    token=super-secret-value
    Authorization: Bearer abc123456
    -----BEGIN PRIVATE KEY-----
    hidden
    -----END PRIVATE KEY-----
    """
    redacted = redact_text(raw)
    assert "super-secret-value" not in redacted
    assert "abc123456" not in redacted
    assert "PRIVATE KEY" not in redacted
    assert "[REDACTED]" in redacted
