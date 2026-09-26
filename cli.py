"""CLI that reads a JSON task list and inserts it into a Notion data source."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Sequence

from notion_client import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_CHILDREN_PER_REQUEST,
    PROP_CATEGORY,
    PROP_DATE,
    PROP_PRIORITY,
    PROP_TITLE,
    VALID_CATEGORIES,
    VALID_PRIORITIES,
    NotionClient,
    NotionConfig,
    NotionConfigError,
    PagePlan,
    Task,
    build_page_plan,
)

logger = logging.getLogger("cli")

EXIT_OK = 0
EXIT_TASK_FAILURES = 1
EXIT_INVALID_INPUT = 2

REQUIRED_KEYS = ("title", "category", "date_time", "priority", "steps")


class ValidationError(Exception):
    def __init__(self, messages: Sequence[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = list(messages)


def parse_task(item: Any, index: int) -> Task:
    prefix = f"tasks[{index}]"
    if not isinstance(item, dict):
        raise ValidationError([f"{prefix}: expected an object, got {type(item).__name__}."])

    missing = [key for key in REQUIRED_KEYS if key not in item]
    if missing:
        raise ValidationError([f"{prefix}: missing required key(s): {', '.join(missing)}."])

    errors: list[str] = []

    title = item["title"]
    if not isinstance(title, str) or not title.strip():
        errors.append(f"{prefix}.title: expected a non-empty string.")

    category = item["category"]
    if category not in VALID_CATEGORIES:
        errors.append(
            f"{prefix}.category: {category!r} is not valid. Use one of: {', '.join(VALID_CATEGORIES)}."
        )

    priority = item["priority"]
    if priority not in VALID_PRIORITIES:
        errors.append(
            f"{prefix}.priority: {priority!r} is not valid. Use one of: {', '.join(VALID_PRIORITIES)}."
        )

    date_time = item["date_time"]
    if date_time is not None and not isinstance(date_time, str):
        errors.append(
            f"{prefix}.date_time: expected a string or null, got {type(date_time).__name__}."
        )

    steps = item["steps"]
    if not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
        errors.append(f"{prefix}.steps: expected a list of strings.")

    if errors:
        raise ValidationError(errors)

    return Task(
        title=title.strip(),
        category=category,
        date_time=date_time,
        priority=priority,
        steps=tuple(steps),
    )


def parse_tasks(payload: Any) -> tuple[list[Task], list[str]]:
    if not isinstance(payload, list):
        raise ValidationError(
            [f"The input must be a JSON array of tasks, got {type(payload).__name__}."]
        )
    if not payload:
        raise ValidationError(["The task array is empty."])

    tasks: list[Task] = []
    errors: list[str] = []
    for index, item in enumerate(payload):
        try:
            tasks.append(parse_task(item, index))
        except ValidationError as exc:
            errors.extend(exc.messages)
    return tasks, errors


def read_payload(source: str | None) -> Any:
    if source and source != "-":
        try:
            with open(source, "r", encoding="utf-8") as handle:
                raw = handle.read()
        except OSError as exc:
            raise ValidationError([f"Could not read {source!r}: {exc}"]) from exc
    else:
        if sys.stdin.isatty():
            raise ValidationError(
                ["No input received. Pipe JSON through stdin or pass a file with --input."]
            )
        raw = sys.stdin.read()

    if not raw.strip():
        raise ValidationError(["The input is empty."])

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError([f"The input is not valid JSON: {exc}"]) from exc


def print_plan(plan: PagePlan, position: int, full_payload: bool) -> None:
    task = plan.task
    blocks = len(plan.page_body.get("children", []))
    extra = sum(len(batch) for batch in plan.extra_children_batches)
    print(f"\n[{position}] {task.title}")
    print(
        f"    {PROP_TITLE}: {task.title} | {PROP_CATEGORY}: {task.category} | "
        f"{PROP_PRIORITY}: {task.priority} | {PROP_DATE}: {task.date_time or '(omitted)'}"
    )
    print(
        f"    to-do blocks: {blocks + extra} "
        f"({blocks} in POST /v1/pages, {extra} in {len(plan.extra_children_batches)} "
        f"PATCH batch(es) of max {MAX_CHILDREN_PER_REQUEST})"
    )
    for warning in plan.warnings:
        print(f"    warning: {warning}")
    if full_payload:
        print("    payload:")
        print(json.dumps(plan.page_body, indent=2, ensure_ascii=False))


def run_dry_run(tasks: Sequence[Task], data_source_id: str, full_payload: bool) -> int:
    print(f"Dry run: {len(tasks)} task(s) validated, no API call will be made.")
    for position, task in enumerate(tasks, start=1):
        print_plan(build_page_plan(task, data_source_id), position, full_payload)
    print(f"\nSummary: {len(tasks)} task(s) would be inserted, 0 failed.")
    return EXIT_OK


def run_insert(tasks: Sequence[Task], client: NotionClient) -> int:
    results = client.insert_tasks(tasks)
    failures = [result for result in results if not result.ok]

    for result in results:
        status = "OK  " if result.ok else "FAIL"
        detail = result.page_id or result.error
        print(f"[{status}] {result.title} -> {detail}")
        for warning in result.warnings:
            print(f"       warning: {warning}")

    print(f"\nSummary: {len(results) - len(failures)} inserted, {len(failures)} failed, {len(results)} total.")
    for result in failures:
        print(f"  - {result.title}: {result.error}")
    return EXIT_TASK_FAILURES if failures else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Insert a JSON array of tasks into a Notion data source."
    )
    parser.add_argument(
        "--input",
        default="-",
        help="Path to a JSON file with the task array. Use '-' or omit it to read stdin.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the input and show what would be sent, without calling the Notion API.",
    )
    parser.add_argument(
        "--full-payload",
        action="store_true",
        help="In dry runs, print the full JSON payload of every create-page request.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level for diagnostics written to stderr (default: INFO).",
    )
    return parser


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.debug("python-dotenv is not installed; skipping .env loading")
        return
    load_dotenv()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    load_dotenv_if_available()

    try:
        payload = read_payload(args.input)
        tasks, errors = parse_tasks(payload)
    except ValidationError as exc:
        for message in exc.messages:
            print(f"Input error: {message}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    if errors:
        for message in errors:
            print(f"Input error: {message}", file=sys.stderr)
        print(
            f"Input error: {len(errors)} problem(s) found. Nothing was sent to Notion.",
            file=sys.stderr,
        )
        return EXIT_INVALID_INPUT

    if args.dry_run:
        try:
            data_source_id = NotionConfig.from_env().data_source_id
        except NotionConfigError as exc:
            logger.warning("%s Using a placeholder in the dry-run output.", exc)
            data_source_id = "<NOTION_DATA_SOURCE_ID>"
        return run_dry_run(tasks, data_source_id, args.full_payload)

    try:
        config = NotionConfig.from_env()
    except NotionConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    with NotionClient(config, timeout=args.timeout) as client:
        return run_insert(tasks, client)


if __name__ == "__main__":
    sys.exit(main())
