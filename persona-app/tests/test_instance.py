"""Tests for single-instance helpers."""

from __future__ import annotations

import json

from persona.instance import instance_file, read_saved_url, write_instance


def test_write_and_read_instance(tmp_path, monkeypatch):
    monkeypatch.setattr("persona.instance.persona_data_dir", lambda: tmp_path)
    write_instance("http://127.0.0.1:8765", 8765, pid=1234)
    assert instance_file().exists()
    data = json.loads(instance_file().read_text(encoding="utf-8"))
    assert data["port"] == 8765
    assert data["url"] == "http://127.0.0.1:8765"
    assert read_saved_url() == "http://127.0.0.1:8765"
