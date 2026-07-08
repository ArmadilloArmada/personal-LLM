"""Tests for project templates."""

from persona.templates import project_templates


def test_project_templates_not_empty():
    templates = project_templates()
    assert len(templates) >= 4


def test_project_templates_have_required_fields():
    for t in project_templates():
        assert t["id"]
        assert t["title"]
        assert t["prompt"]
        assert t["mode"] in ("project", "roundtable", "solo")
