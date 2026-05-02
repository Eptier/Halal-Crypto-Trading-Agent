from pathlib import Path

import pytest

from halal_agent.safety import ACK_FILENAME, ACK_PHRASE, SafetyError, require_live_ack


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(SafetyError):
        require_live_ack(tmp_path)


def test_file_without_phrase_raises(tmp_path: Path):
    (tmp_path / ACK_FILENAME).write_text("ok i guess", encoding="utf-8")
    with pytest.raises(SafetyError):
        require_live_ack(tmp_path)


def test_file_with_phrase_passes(tmp_path: Path):
    (tmp_path / ACK_FILENAME).write_text(
        f"# Live trading authorized\n\n{ACK_PHRASE}\n", encoding="utf-8"
    )
    require_live_ack(tmp_path)  # should not raise
