"""FastAPI backend server for the Voice Task Organizer.

Integrates Web Speech API voice parser with Notion Client, Obsidian Markdown Export, and Calendar Sync.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from notion_client import (
    NotionClient,
    NotionConfig,
    NotionConfigError,
    NotionAPIError,
    Task,
    build_page_plan,
)
from voice_parser import parse_transcript
from firebase_client import firebase_manager
from polly_client import polly_manager

load_dotenv()

logger = logging.getLogger("server")

app = FastAPI(title="Voice Task Organizer", version="1.0.0")


class DictationPayload(BaseModel):
    transcript: str


class TaskPayload(BaseModel):
    title: str
    category: str
    priority: str
    date_time: str | None = None
    steps: list[str] = []


class FirebaseNotePayload(BaseModel):
    title: str
    content: str
    category: str = "Nota"
    priority: str = "Media"
    generate_audio: bool = False
    tags: list[str] = []


class PollyPayload(BaseModel):
    text: str
    voice_id: str = "Lupe"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return a 204 No Content for favicon requests to prevent 404 console warnings."""
    return Response(status_code=204)


@app.post("/api/parse")
async def parse_voice_dictation(payload: DictationPayload):
    """Parse raw Spanish dictation text into a structured task preview."""
    try:
        parsed = parse_transcript(payload.transcript)
        return {"success": True, "task": parsed}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.post("/api/tasks")
async def create_task(payload: TaskPayload):
    """Send a structured task to Notion."""
    try:
        config = NotionConfig.from_env()
    except NotionConfigError as err:
        raise HTTPException(status_code=500, detail=f"Configuración de Notion faltante: {err}")

    task = Task(
        title=payload.title.strip() or "Nueva Idea",
        category=payload.category,
        date_time=payload.date_time,
        priority=payload.priority,
        steps=tuple(payload.steps),
    )

    client = NotionClient(config)

    try:
        result = client.insert_task(task)
        if result.error:
            raise HTTPException(status_code=502, detail=f"Error en Notion: {result.error}")

        return {
            "success": True,
            "page_id": result.page_id,
            "url": getattr(result, "url", None),
            "calendar_url": generate_gcal_link(payload.title, payload.date_time, payload.steps),
        }
    except NotionAPIError as err:
        raise HTTPException(status_code=502, detail=f"Error en Notion API: {err}")


@app.post("/api/obsidian")
async def export_to_obsidian(payload: TaskPayload):
    """Export task as a Markdown file directly to Obsidian Vault in background (without focusing app)."""
    title_clean = re.sub(r'[\\/*?:"<>|]', "", payload.title).strip() or "Nota"
    filename = f"{title_clean}.md"

    # YAML Frontmatter + Markdown content
    yaml_date = f'"{payload.date_time}"' if payload.date_time else "null"
    steps_md = "\n".join(f"- [ ] {step}" for step in payload.steps) if payload.steps else "*Sin pasos registrados.*"

    md_content = f"""---
title: "{payload.title}"
category: "{payload.category}"
priority: "{payload.priority}"
date: {yaml_date}
tags:
  - organizador-voz
  - {payload.category.lower()}
---

# {payload.title}

**Categoría:** {payload.category} | **Prioridad:** {payload.priority}  
**Fecha:** {payload.date_time or 'Sin fecha'}

## Lista de Comprobación
{steps_md}
"""

    vault_path_raw = os.getenv("OBSIDIAN_VAULT_PATH", "").strip('"\'')
    vault_name_raw = os.getenv("OBSIDIAN_VAULT_NAME", "").strip('"\'')
    folder_raw = os.getenv("OBSIDIAN_FOLDER", "").strip('"\'/ ')

    saved_to_disk = False
    saved_file_path = None

    if vault_path_raw:
        base_dir = Path(os.path.expanduser(vault_path_raw))
        target_dir = base_dir / folder_raw if folder_raw else base_dir
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            target_file.write_text(md_content, encoding="utf-8")
            saved_to_disk = True
            saved_file_path = str(target_file)
        except Exception as e:
            logger.warning("Fallo al guardar directamente en disco: %s", e)

    relative_path = f"{folder_raw}/{title_clean}" if folder_raw else title_clean

    if vault_name_raw:
        obsidian_uri = f"obsidian://new?vault={quote(vault_name_raw)}&file={quote(relative_path)}&content={quote(md_content)}"
    else:
        obsidian_uri = f"obsidian://new?file={quote(relative_path)}&content={quote(md_content)}"

    return {
        "success": True,
        "saved_to_disk": saved_to_disk,
        "saved_file_path": saved_file_path,
        "obsidian_uri": obsidian_uri,
        "markdown_content": md_content,
    }


@app.post("/api/calendar-link")
async def get_calendar_link(payload: TaskPayload):
    """Generate a Google Calendar event creation link for a task."""
    link = generate_gcal_link(payload.title, payload.date_time, payload.steps)
    return {"google_calendar_url": link}


@app.post("/api/firebase/notes")
async def save_firebase_note(payload: FirebaseNotePayload):
    """Save a note into Firebase Firestore (and optionally generate audio with Polly)."""
    audio_url = None
    if payload.generate_audio:
        temp_file = f"/tmp/polly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
        synthesized_path = polly_manager.synthesize_to_file(payload.content, temp_file)
        if synthesized_path:
            audio_url = firebase_manager.upload_audio_file(synthesized_path)

    note_id = firebase_manager.save_note(
        title=payload.title,
        content=payload.content,
        category=payload.category,
        priority=payload.priority,
        audio_url=audio_url,
        tags=payload.tags,
    )

    if not note_id:
        raise HTTPException(status_code=500, detail="Error guardando nota en Firestore.")

    return {"success": True, "note_id": note_id, "audio_url": audio_url}


@app.get("/api/firebase/notes")
async def get_firebase_notes(limit: int = 50):
    """Retrieve notes stored in Firebase Firestore."""
    notes = firebase_manager.get_notes(limit=limit)
    return {"success": True, "notes": notes}


@app.post("/api/polly/synthesize")
async def synthesize_speech(payload: PollyPayload):
    """Synthesize text into speech using Amazon Polly."""
    temp_file = f"/tmp/polly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
    path = polly_manager.synthesize_to_file(payload.text, temp_file, voice_id=payload.voice_id)
    if not path:
        raise HTTPException(status_code=500, detail="Error sintetizando voz con Amazon Polly.")
    return {"success": True, "file_path": path}


@app.get("/api/polly/stream")
async def stream_polly_speech(text: str, voice_id: str = "Lupe"):
    """Stream audio synthesized by Amazon Polly directly as MP3."""
    audio_bytes = polly_manager.synthesize_bytes(text, voice_id=voice_id, engine="neural")
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Error al generar audio con Amazon Polly.")
    return Response(content=audio_bytes, media_type="audio/mpeg")


def generate_gcal_link(title: str, date_time_str: str | None, steps: list[str]) -> str | None:
    """Generate a Google Calendar event template URL."""
    if not date_time_str:
        return None

    try:
        dt = datetime.fromisoformat(date_time_str)
    except ValueError:
        return None

    dt_end = dt + timedelta(hours=1)
    fmt = "%Y%m%dT%H%M%SZ"
    dates_param = f"{dt.strftime(fmt)}/{dt_end.strftime(fmt)}"

    details = "Checklist de la tarea:\n" + "\n".join(f"- [ ] {s}" for s in steps) if steps else "Creado desde Voice Task Organizer."
    
    base = "https://calendar.google.com/calendar/render"
    query = f"?action=TEMPLATE&text={quote(title)}&dates={dates_param}&details={quote(details)}"
    return base + query


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
