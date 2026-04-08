from ariadne_doc_assistant.core.policies import (
    PROTECTED_END,
    PROTECTED_START,
    extract_protected_blocks,
)


def test_protected_blocks_parser() -> None:
    text = "\n".join(
        [
            "# Title",
            PROTECTED_START,
            "Do not alter this block.",
            PROTECTED_END,
            "Regular content.",
        ]
    )
    blocks = extract_protected_blocks(text)
    assert len(blocks) == 1
    assert "Do not alter this block." in blocks[0]
