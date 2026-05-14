from ariadne_doc_assistant.core.policies import mask_text


def test_masking() -> None:
    raw = """
    token=super-secret-value
    Authorization: Bearer abc123456
    -----BEGIN PRIVATE KEY-----
    hidden
    -----END PRIVATE KEY-----
    """
    masked = mask_text(raw)
    assert "super-secret-value" not in masked
    assert "abc123456" not in masked
    assert "PRIVATE KEY" not in masked
    assert "[MASKED]" in masked
