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

    # 5. Extract Title
    title = _clean_title(text)

    return {
        "title": title,
        "category": category,
        "priority": priority,
        "date_time": date_time_str,
        "steps": steps,
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
    """Extract step list from Spanish dictation."""
    steps: list[str] = []

    # Look for explicit list pattern like "pasos: ... y luego ...", or "primero ... segundo ..."
    steps_match = re.search(r"\b(pasos|paso|tareas|checklist):\s*(.*)", text, re.IGNORECASE)
    if steps_match:
        raw_steps = steps_match.group(2)
        # Split by comma, 'y', 'luego', 'después'
        parts = re.split(r",|\by\b|\bluego\b|\bdespués\b|\bdespues\b", raw_steps)
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                steps.append(cleaned.capitalize())
        return steps

    # Check for ordinal markers: primero, segundo, tercero
    ordinal_parts = re.split(r"\b(primero|segundo|tercero|luego|después|despues)\b", text, flags=re.IGNORECASE)
    if len(ordinal_parts) > 3:
        for i in range(2, len(ordinal_parts), 2):
            step_text = ordinal_parts[i].strip()
            if step_text:
                steps.append(step_text.capitalize())
        return steps

    return steps


def _clean_title(text: str) -> str:
    """Clean title removing keywords."""
    # Remove category markers
    cleaned = re.sub(r"\b(categoría|categoria|para|en)\s+(trabajo|personal|ideas|proyectos)\b", "", text, flags=re.IGNORECASE)
    # Remove priority markers
    cleaned = re.sub(r"\b(prioridad|urgente)\s*(alta|media|baja)?\b", "", cleaned, flags=re.IGNORECASE)
    # Remove date markers
    cleaned = re.sub(r"\b(para mañana|mañana|hoy|pasado mañana|el [a-z]+)\b", "", cleaned, flags=re.IGNORECASE)
    # Remove time markers
    cleaned = re.sub(r"\ba las \d{1,2}(:\d{2})?\s*(am|pm)?\b", "", cleaned, flags=re.IGNORECASE)
    # Remove steps section if present
    cleaned = re.split(r"\b(pasos|paso|tareas|checklist):", cleaned, flags=re.IGNORECASE)[0]

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    if not cleaned:
        cleaned = text[:50]
    return cleaned.capitalize()
