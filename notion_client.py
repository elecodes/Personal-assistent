"""Notion client that turns productivity tasks into pages in a data source.

The public surface is intentionally small: builders that turn a task into a
Notion payload (pure functions, usable for dry runs) plus `NotionClient`, which
performs the HTTP calls with retries and rate-limit handling.
"""

from __future__ import annotations

import calendar
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Sequence

import requests

# These must match EXACTLY the column names of the Notion data source.
# If the data source uses different column names, these must be updated.
PROP_TITLE = "Name"
PROP_CATEGORY = "Categoría"
PROP_PRIORITY = "Prioridad"
PROP_DATE = "Fecha"

VALID_CATEGORIES = ("Trabajo", "Personal", "Ideas", "Proyectos")
VALID_PRIORITIES = ("Alta", "Media", "Baja")

NOTION_API_VERSION = "2026-03-11"
NOTION_BASE_URL = "https://api.notion.com/v1"

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_CHILDREN_PER_REQUEST = 100
MAX_RICH_TEXT_LENGTH = 2000
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 1.0
MAX_RETRY_AFTER_SECONDS = 60.0

PLACEHOLDER_DATA_SOURCE_ID = "<NOTION_DATA_SOURCE_ID>"

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")
_UUID_WITHOUT_DASHES_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")

logger = logging.getLogger(__name__)


class NotionConfigError(RuntimeError):
    """Raised when the environment is missing required configuration."""


class NotionAPIError(RuntimeError):
    """Raised when a Notion API call fails after exhausting retries."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(f"Notion API error {status_code} ({code}): {message}")
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Task:
    title: str
    category: str
    date_time: str | None
    priority: str
    steps: tuple[str, ...]


@dataclass
class TaskResult:
    title: str
    page_id: str | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class NotionConfig:
    token: str
    data_source_id: str

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "NotionConfig":
        env = os.environ if environ is None else environ
        token = (env.get("NOTION_TOKEN") or "").strip()
        raw_data_source_id = (env.get("NOTION_DATA_SOURCE_ID") or "").strip()

        missing = [
            name
            for name, value in (
                ("NOTION_TOKEN", token),
                ("NOTION_DATA_SOURCE_ID", raw_data_source_id),
            )
            if not value
        ]
        if missing:
            raise NotionConfigError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Export them in your shell or put them in a .env file (see .env.example)."
            )

        return cls(token=token, data_source_id=normalize_data_source_id(raw_data_source_id))


def normalize_data_source_id(raw: str) -> str:
    """Accept both dashed and undashed 32-character Notion ids."""
    if _UUID_WITHOUT_DASHES_PATTERN.match(raw):
        logger.debug("Normalizing NOTION_DATA_SOURCE_ID to dashed UUID format")
        parts = (raw[0:8], raw[8:12], raw[12:16], raw[16:20], raw[20:32])
        return "-".join(parts)
    return raw


def _truncate(text: str, warnings: list[str], label: str) -> str:
    if len(text) <= MAX_RICH_TEXT_LENGTH:
        return text
    warnings.append(
        f"{label} is {len(text)} characters long and was truncated to "
        f"{MAX_RICH_TEXT_LENGTH} (Notion rich text limit)."
    )
    logger.warning("Truncating %s: %d characters exceed the Notion limit of %d", label, len(text), MAX_RICH_TEXT_LENGTH)
    return text[:MAX_RICH_TEXT_LENGTH]


def normalize_date_value(value: str, warnings: list[str]) -> str | None:
    """Return the date in a format Notion accepts, or None with a warning.

    An unparseable date must not fail the whole insertion, so the caller drops
    the Fecha property instead of aborting.
    """
    text = value.strip()
    try:
        if _DATE_PATTERN.match(text):
            date.fromisoformat(text)
            return text
        if _DATE_TIME_PATTERN.match(text):
            datetime.fromisoformat(text)
            return text
    except ValueError:
        pass

    warnings.append(
        f"Ignoring Fecha: {value!r} is not a valid date. "
        "Expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS."
    )
    logger.warning("Skipping Fecha property for unexpected date format: %r", value)
    return None


def build_task_properties(task: Task) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    properties: dict[str, Any] = {
        PROP_TITLE: {
            "title": [
                {"type": "text", "text": {"content": _truncate(task.title, warnings, "title")}}
            ]
        },
        PROP_CATEGORY: {"select": {"name": task.category}},
        PROP_PRIORITY: {"select": {"name": task.priority}},
    }

    if task.date_time is not None:
        start = normalize_date_value(task.date_time, warnings)
        if start is not None:
            properties[PROP_DATE] = {"date": {"start": start}}

    return properties, warnings


def build_todo_children(task: Task) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    children: list[dict[str, Any]] = []

    for index, step in enumerate(task.steps, start=1):
        content = step.strip()
        if not content:
            warnings.append(f"Step {index} is empty and was skipped.")
            continue
        children.append(
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {"type": "text", "text": {"content": _truncate(content, warnings, f"step {index}")}}
                    ]
                },
            }
        )

    return children, warnings


def split_children(children: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
    """Split children into the initial create-page batch and follow-up batches."""
    initial = list(children[:MAX_CHILDREN_PER_REQUEST])
    remaining = list(children[MAX_CHILDREN_PER_REQUEST:])
    batches = [
        remaining[index : index + MAX_CHILDREN_PER_REQUEST]
        for index in range(0, len(remaining), MAX_CHILDREN_PER_REQUEST)
    ]
    return initial, batches


@dataclass(frozen=True)
class PagePlan:
    task: Task
    page_body: dict[str, Any]
    extra_children_batches: tuple[tuple[dict[str, Any], ...], ...]
    warnings: tuple[str, ...]


def build_page_plan(task: Task, data_source_id: str = PLACEHOLDER_DATA_SOURCE_ID) -> PagePlan:
    properties, property_warnings = build_task_properties(task)
    children, child_warnings = build_todo_children(task)
    initial, batches = split_children(children)

    body: dict[str, Any] = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": properties,
    }
    if initial:
        body["children"] = initial

    return PagePlan(
        task=task,
        page_body=body,
        extra_children_batches=tuple(tuple(batch) for batch in batches),
        warnings=tuple(property_warnings + child_warnings),
    )


def _extract_error(response: requests.Response) -> tuple[str, str]:
    code, message = "unknown_error", response.text or response.reason or "no response body"
    try:
        payload = response.json()
    except ValueError:
        return code, message
    if isinstance(payload, dict):
        code = str(payload.get("code") or code)
        message = str(payload.get("message") or message)
    return code, message


def _retry_after_seconds(response: requests.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        logger.warning("Could not parse retry-after header value %r", raw)
        return None
    if target is None:
        return None
    # calendar.timegm keeps this tz-agnostic; a naive result is read as UTC.
    return max(0.0, calendar.timegm(target.utctimetuple()) - time.time())


class NotionClient:
    def __init__(
        self,
        config: NotionConfig,
        *,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {config.token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            }
        )

    def __enter__(self) -> "NotionClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def _backoff_delay(self, attempt: int) -> float:
        return RETRY_BASE_DELAY_SECONDS * (2**attempt)

    def _sleep_before_retry(self, attempt: int, reason: str, delay: float) -> None:
        logger.warning(
            "%s (attempt %d/%d). Retrying in %.1fs.", reason, attempt + 1, self.max_retries, delay
        )
        time.sleep(delay)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{NOTION_BASE_URL}{path}"
        last_error: NotionAPIError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._session.request(method, url, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = NotionAPIError(0, "request_failed", str(exc))
                if attempt >= self.max_retries:
                    break
                self._sleep_before_retry(attempt, f"Request to {path} failed: {exc}", self._backoff_delay(attempt))
                continue

            status = response.status_code
            if status == 429:
                last_error = NotionAPIError(status, *_extract_error(response))
                if attempt >= self.max_retries:
                    break
                delay = _retry_after_seconds(response)
                if delay is None:
                    delay = self._backoff_delay(attempt)
                elif delay > MAX_RETRY_AFTER_SECONDS:
                    logger.warning(
                        "retry-after is %.0fs, waiting the configured maximum of %.0fs instead.",
                        delay,
                        MAX_RETRY_AFTER_SECONDS,
                    )
                    delay = MAX_RETRY_AFTER_SECONDS
                self._sleep_before_retry(attempt, "Rate limited by Notion", delay)
                continue

            if 500 <= status < 600:
                last_error = NotionAPIError(status, *_extract_error(response))
                if attempt >= self.max_retries:
                    break
                self._sleep_before_retry(
                    attempt, f"Notion returned {status}", self._backoff_delay(attempt)
                )
                continue

            if 400 <= status < 500:
                code, message = _extract_error(response)
                raise NotionAPIError(status, code, message)

            try:
                body = response.json()
            except ValueError as exc:
                raise NotionAPIError(status, "invalid_json", str(exc)) from exc
            if not isinstance(body, dict):
                raise NotionAPIError(status, "unexpected_body", "Response body was not a JSON object")
            return body

        if last_error is None:
            last_error = NotionAPIError(0, "request_failed", f"{method} {path} failed")
        raise last_error

    def insert_task(self, task: Task) -> TaskResult:
        plan = build_page_plan(task, self.config.data_source_id)
        result = TaskResult(title=task.title, warnings=list(plan.warnings))
        if plan.extra_children_batches:
            logger.info(
                "Task %r has %d to-do blocks: %d in the create request and %d follow-up batch(es).",
                task.title,
                len(plan.page_body.get("children", [])) + sum(len(b) for b in plan.extra_children_batches),
                len(plan.page_body.get("children", [])),
                len(plan.extra_children_batches),
            )

        try:
            page = self._request("POST", "/pages", plan.page_body)
        except NotionAPIError as exc:
            logger.error("Failed to create page for %r: %s", task.title, exc)
            result.error = str(exc)
            return result

        page_id = page.get("id")
        if not isinstance(page_id, str) or not page_id:
            result.error = "Notion created the page but did not return a page id."
            return result

        result.page_id = page_id
        for index, batch in enumerate(plan.extra_children_batches, start=1):
            try:
                self._request(
                    "PATCH", f"/blocks/{page_id}/children", {"children": list(batch)}
                )
            except NotionAPIError as exc:
                result.error = (
                    f"Page {page_id} was created but to-do batch {index} of "
                    f"{len(plan.extra_children_batches)} failed: {exc}"
                )
                return result

        logger.info("Created page %s for task %r", page_id, task.title)
        return result

    def insert_tasks(self, tasks: Sequence[Task]) -> list[TaskResult]:
        results: list[TaskResult] = []
        for task in tasks:
            try:
                results.append(self.insert_task(task))
            except Exception as exc:  # a single bad task must not kill the batch
                logger.exception("Unexpected error while inserting task %r", task.title)
                results.append(TaskResult(title=task.title, error=f"Unexpected error: {exc}"))
        return results
