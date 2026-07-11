"""Starter project templates — the hero onboarding flow for Persona."""

from __future__ import annotations

from typing import Any

PROJECT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "side-project",
        "title": "Launch a side project",
        "emoji": "🚀",
        "description": "Validate an idea, name it, and ship a 2-week plan.",
        "mode": "project",
        "prompt": (
            "I want to launch a side project. Help me validate the idea, pick a name, "
            "define an MVP, and create a 2-week execution plan with clear tasks for the crew."
        ),
    },
    {
        "id": "debug-app",
        "title": "Debug my app",
        "emoji": "🐛",
        "description": "Byte leads — reproduce, isolate, and fix the issue.",
        "mode": "project",
        "prompt": (
            "I need help debugging my application. Walk me through reproducing the issue, "
            "isolating the root cause, proposing a minimal fix, and listing verification steps."
        ),
    },
    {
        "id": "business-plan",
        "title": "Write a business plan",
        "emoji": "📋",
        "description": "Research the market and draft a one-page plan.",
        "mode": "project",
        "prompt": (
            "Help me write a concise one-page business plan: problem, audience, solution, "
            "revenue model, go-to-market, and next 3 milestones."
        ),
    },
    {
        "id": "study-plan",
        "title": "Study for an exam",
        "emoji": "📚",
        "description": "Nova researches, Sunny keeps you motivated.",
        "mode": "project",
        "prompt": (
            "I have an exam coming up. Create a study plan with topics to cover, "
            "practice questions, a daily schedule, and memory techniques."
        ),
    },
    {
        "id": "blog-post",
        "title": "Write a blog post",
        "emoji": "✍️",
        "description": "Outline, draft, and polish a publishable article.",
        "mode": "project",
        "prompt": (
            "I want to write a blog post. Help me pick an angle, create an outline, "
            "draft the article, and suggest a headline and meta description."
        ),
    },
    {
        "id": "brainstorm",
        "title": "Brainstorm ideas",
        "emoji": "💡",
        "description": "Quick group roundtable — all agents weigh in.",
        "mode": "roundtable",
        "prompt": (
            "I need creative ideas. Each crew member should share 2-3 unique suggestions "
            "for my topic, then we'll pick the best ones to develop further."
        ),
    },
]


def project_templates() -> list[dict[str, Any]]:
    return list(PROJECT_TEMPLATES)
