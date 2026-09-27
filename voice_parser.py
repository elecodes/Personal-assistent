"""Voice dictation parser for task creation.

Extracts structured Task fields (title, category, priority, date_time, steps)
from natural language Spanish transcriptions.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, time
from typing import Sequence

VALID_CATEGORIES = ("Trabajo", "Personal", "Ideas", "Proyectos")
VALID_PRIORITIES = ("Alta", "Media", "Baja")


def parse_transcript(transcript: str, reference_date: datetime | None = None) -> dict[str, str | None | list[str]]:
    """Parse a Spanish speech transcript into task parameters."""
    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    ref = reference_date or datetime.now()
    text = transcript.strip()

    # 1. Extract Category
    category = "Ideas"  # Default category
    text_lower = text.lower()
    for cat in VALID_CATEGORIES:
        if re.search(r"\b" + re.escape(cat.lower()) + r"\b", text_lower):
            category = cat
            break

    # 2. Extract Priority
    priority = "Media"  # Default priority
    if re.search(r"\b(prioridad alta|urgente|muy importante|alta prioridad|alta)\b", text_lower):
        priority = "Alta"
    elif re.search(r"\b(prioridad baja|poca prioridad|baja prioridad|baja)\b", text_lower):
        priority = "Baja"
    elif re.search(r"\b(prioridad media|media prioridad|media)\b", text_lower):
        priority = "Media"

    # 3. Extract Date/Time
    date_time_str = _extract_date_time(text_lower, ref)

    # 4. Extract Steps / Checklist
    steps = _extract_steps(text)

    # 5. Extract Sync Triggers (Notion / Obsidian)
    sync_notion = bool(re.search(r"\b(añadir|anadir|add|enviar|guardar|subir|sync|sincronizar|exportar)\b.*?\bnotion\b", text_lower))
    sync_obsidian = bool(re.search(r"\b(añadir|anadir|add|enviar|guardar|subir|sync|sincronizar|exportar)\b.*?\bobsidian\b", text_lower))

    # 6. Extract Title
    title = _clean_title(text)

    return {
        "title": title,
        "category": category,
        "priority": priority,
        "date_time": date_time_str,
        "steps": steps,
        "sync_notion": sync_notion,
        "sync_obsidian": sync_obsidian,
    }


def _extract_date_time(text: str, ref: datetime) -> str | None:
    """Extract target date/time from Spanish text."""
    target_date: datetime | None = None

    if "pasado mañana" in text:
        target_date = ref + timedelta(days=2)
    elif "mañana" in text:
        target_date = ref + timedelta(days=1)
    elif "hoy" in text:
        target_date = ref

    days_es = {
        "lunes": 0,
        "martes": 1,
        "miércoles": 2,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sábado": 5,
        "sabado": 5,
        "domingo": 6,
    }

    if not target_date:
        for day_name, day_num in days_es.items():
            if f"el {day_name}" in text or f"este {day_name}" in text or f"próximo {day_name}" in text or f"proximo {day_name}" in text:
                days_ahead = (day_num - ref.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = ref + timedelta(days=days_ahead)
                break

    if not target_date:
        # Check for specific date format like "15 de octubre" or "25/12"
        months_es = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
            "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
        }
        match = re.search(r"\b(\d{1,2})\s+de\s+([a-z]+)\b", text)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            if month_name in months_es:
                month = months_es[month_name]
                year = ref.year
                if month < ref.month or (month == ref.month and day < ref.day):
                    year += 1
                try:
                    target_date = datetime(year, month, day)
                except ValueError:
                    pass

    if target_date:
        # Extract time if specified (e.g. "a las 15" or "a las 3 pm" or "9:30")
        hour = 9  # Default 9:00 AM
        minute = 0
        time_match = re.search(r"\ba las (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text)
        if time_match:
            h = int(time_match.group(1))
            m = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            if ampm == "pm" and h < 12:
                h += 12
            elif ampm == "am" and h == 12:
                h = 0
            hour, minute = h, m

        target_datetime = datetime.combine(target_date.date(), time(hour, minute))
        return target_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    return None


def _extract_steps(text: str) -> list[str]:
    """Extract step list from Spanish dictation intelligently."""
    # Pre-clean sync trigger phrases
    clean_text = re.sub(r"\b(añadir|anadir|add|enviar|guardar|subir|sync|sincronizar|exportar)\s+(a\s+|en\s+|to\s+)?(notion|obsidian)\b", "", text, flags=re.IGNORECASE).strip()

    steps: list[str] = []

    # 1. Split by newlines if present
    if "\n" in clean_text:
        lines = [line.strip(" -*•") for line in clean_text.split("\n") if line.strip()]
        if len(lines) > 1:
            return [l.capitalize() for l in lines]

    # 2. Check for explicit list prefix like "pasos:", "tareas:", "checklist:"
    steps_match = re.search(r"\b(pasos|paso|tareas|checklist|subtareas):\s*(.*)", clean_text, re.IGNORECASE)
    raw_text = steps_match.group(2) if steps_match else clean_text

    # 3. Split by dictation delimiters:
    pattern = r"[\.\;\n]|(?:\b(?:primero|segundo|tercero|cuarto|quinto|luego|después|despues|además|ademas|también|tambien|punto|coma|nuevo renglón|nueva línea|tarea|subtarea)\b|\bpunto\s*\d+\b|\b\d+[\.\)]\s*)"
    
    parts = re.split(pattern, raw_text, flags=re.IGNORECASE)
    for part in parts:
        cleaned = re.sub(r"^(y|o|e|que)\s+", "", part.strip(" ,.-*•"), flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+\b(y|o|e|que|en|para)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
        if len(cleaned) > 2:
            steps.append(cleaned.capitalize())

    if len(steps) > 1:
        return steps

    # 4. Fallback: split by common action verbs and anglicisms if no explicit delimiters found
    actions_list = [
        "comprar", "llamar", "enviar", "hacer", "revisar", "preparar", "escribir",
        "estudiar", "organizar", "ir a", "buscar", "pagar", "subir", "mandar",
        "borrar", "crear", "editar", "verificar", "analizar", "corregir",
        "deploy", "deployar", "meeting", "call", "pr", "pull request", "check",
        "checkear", "chequear", "test", "testing", "testear", "commit", "commitear",
        "merge", "mergear", "push", "pushear", "pull", "sync", "sincronizar",
        "review", "code review", "feedback", "backup", "post", "postear",
        "update", "updatear", "release", "sprint", "standup", "ticket", "issue",
        "bug", "feature", "pipeline", "build", "refactor"
    ]
    verb_pattern = r"\b(?=(?:" + "|".join(re.escape(w) for w in actions_list) + r")\b)"
    verb_parts = re.split(verb_pattern, clean_text, flags=re.IGNORECASE)
    verb_steps = [re.sub(r"^(y|o|e|que)\s+", "", p.strip(" ,.-"), flags=re.IGNORECASE).strip().capitalize() for p in verb_parts if len(p.strip(" ,.-")) > 2]
    if len(verb_steps) > 1:
        return verb_steps

    return steps if len(steps) > 1 else []


def _clean_title(text: str) -> str:
    """Clean title removing keywords and preserving multi-line structure."""
    steps = _extract_steps(text)
    if len(steps) > 1:
        return "\n".join(f"• {s}" for s in steps)

    cleaned = re.sub(r"\b(categoría|categoria|para|en)\s+(trabajo|personal|ideas|proyectos)\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(prioridad|urgente)\s*(alta|media|baja)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(para mañana|mañana|hoy|pasado mañana|el [a-z]+)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\ba las \d{1,2}(:\d{2})?\s*(am|pm)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(añadir|anadir|add|enviar|guardar|subir|sync|sincronizar|exportar)\s+(a\s+|en\s+|to\s+)?(notion|obsidian)\b", "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s*[\.\;]\s*", "\n", cleaned)
    cleaned = re.sub(r"\s*\b(primero|segundo|tercero|cuarto|quinto|luego|después|despues|punto \d+|tarea \d+|\d+[\.\)])\b\s*", "\n• ", cleaned, flags=re.IGNORECASE)

    lines = [re.sub(r"\s+\b(y|o|e|que|en|para)\s*$", "", l.strip(" ,.-"), flags=re.IGNORECASE) for l in cleaned.split("\n") if l.strip(" ,.-")]
    lines = [l for l in lines if l]
    if not lines:
        lines = [text[:50]]

    formatted = "\n".join(l.capitalize() if not l.startswith("• ") else f"• {l[2:].capitalize()}" for l in lines)
    return formatted
