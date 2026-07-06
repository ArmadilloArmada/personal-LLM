"""Project board — kanban tasks for crew projects."""

from __future__ import annotations

import re
import uuid
from typing import Any

from persona.personas import PERSONAS, get_persona

BOARD_COLUMNS = ["backlog", "in_progress", "review", "done"]


def new_task(
    title: str,
    assignee: str = "captain",
    description: str = "",
    column: str = "backlog",
    order: int = 0,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4())[:8],
        "title": title[:120],
        "description": description[:500],
        "assignee": assignee,
        "column": column if column in BOARD_COLUMNS else "backlog",
        "order": order,
    }


def extract_tasks_from_plan(plan: str, worker_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Parse Captain's plan into kanban tasks."""
    workers = worker_ids or []
    tasks: list[dict[str, Any]] = []
    lines = [line.strip() for line in plan.splitlines() if line.strip()]

    for line in lines:
        if len(line) < 4:
            continue
        assignee = _match_assignee(line, workers)
        if not assignee and not _looks_like_task(line):
            continue
        title = _clean_task_title(line)
        if title:
            tasks.append(new_task(title=title, assignee=assignee or "captain", order=len(tasks)))

    if not tasks:
        for pid in workers:
            if pid == "captain":
                continue
            persona = get_persona(pid)
            tasks.append(
                new_task(
                    title=f"{persona.name}: contribute to project deliverable",
                    assignee=pid,
                    description=f"Owned by {persona.role}",
                    order=len(tasks),
                )
            )

    if not tasks:
        tasks.append(new_task(title="Define project scope", assignee="captain"))

    return tasks


def _match_assignee(line: str, workers: list[str]) -> str | None:
    lower = line.lower()
    for pid in workers:
        try:
            persona = get_persona(pid)
        except KeyError:
            continue
        if pid in lower or persona.name.lower() in lower:
            return pid
    for pid, persona in PERSONAS.items():
        if persona.name.lower() in lower or pid in lower:
            return pid
    return None


def _looks_like_task(line: str) -> bool:
    return bool(re.match(r"^(\d+[\).\s]|[-*•])", line))


def _clean_task_title(line: str) -> str:
    title = re.sub(r"^(\d+[\).\s]+|[-*•]\s*)", "", line).strip()
    title = re.sub(r"^(byte|sunny|nova|sketch|captain)\s*:\s*", "", title, flags=re.I)
    return title[:120]


def board_view(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped = {col: [] for col in BOARD_COLUMNS}
    for task in sorted(tasks, key=lambda t: (BOARD_COLUMNS.index(t.get("column", "backlog")), t.get("order", 0))):
        col = task.get("column", "backlog")
        if col not in grouped:
            col = "backlog"
        grouped[col].append(task)
    return grouped


def move_task(tasks: list[dict[str, Any]], task_id: str, column: str, order: int | None = None) -> list[dict[str, Any]]:
    if column not in BOARD_COLUMNS:
        column = "backlog"
    updated: list[dict[str, Any]] = []
    for task in tasks:
        if task["id"] == task_id:
            task = {**task, "column": column}
            if order is not None:
                task["order"] = order
        updated.append(task)
    if order is None:
        col_tasks = [t for t in updated if t["column"] == column]
        for idx, task in enumerate(col_tasks):
            if task["id"] == task_id:
                task["order"] = idx
    return updated
