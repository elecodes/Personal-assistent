# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-09-27

### Added
- **Hands-Free Voice Auto-Sync**: Automatic sync triggers for Notion and Obsidian parsed directly from dictation or typed commands (`añadir a notion`, `add to obsidian`, `enviar a notion`, `sync obsidian`) without needing manual clicks.
- **LocalStorage Board Persistence**: Full dashboard state retention using `localStorage` so cards and checklist edits remain intact across sessions and browser reloads.
- **UI & UX Refinements**: Manual card creation fix without active mic required, focus loss prevention during text editing, and automatic clearing of default card titles on focus.

## [1.3.0] - 2026-09-27

### Added
- **Firebase Cloud Persistence**: Cloud Firestore NoSQL database and Cloud Storage audio persistence (`firebase_client.py`) under Firebase Free Tier.
- **Amazon Polly Neural Text-to-Speech**: High-definition neural TTS integration (`polly_client.py` & `/api/polly/stream`) with Spanish neural voices (`Lupe`, `Mia`, `Lucia`).
- **Notion Data Source & Calendar Sync**: Updated `notion_client.py` supporting `data_source_id` payloads, `multi_select` properties (`Categoría`, `Prioridad`), and automatic fallback handling for Notion Calendar Database Tables.
- **Smart Voice Dictation & Anglicisms Parsing**: Enhanced `voice_parser.py` supporting tech anglicisms (`deploy`, `meeting`, `PR`, `pull request`, `commit`, `merge`, `push`, `sync`, `test`, `review`, `feedback`, `backup`, `issue`, `bug`, `feature`) and multi-line bullet point formatting (`•`). Documented **Whisper Flow** dictation compatibility option in README.
- **Architecture Documentation**: Added ADR 0002 under `docs/adr/0002-firebase-polly-notion-voice-enhancements.md`.

## [1.2.0] - 2026-09-26

### Added
- **Text-to-Speech (TTS) Audio Playback**: Daily column audio summaries (`speakColumn`) and individual card playback (`speakSingleTask`) using native `SpeechSynthesisUtterance` API ($0 cost).

## [1.1.0] - 2026-09-26

### Added
- **Silent Background Obsidian Export**: Exporting Markdown notes directly to local workspace vault (`obsidian_vault/Substack`) in 100% background silent mode without launching or focusing the Obsidian desktop app.
- **Task Completion & Retention**: Card completion toggle (`Completar` / `Completada`) with active board retention until explicit completion, plus a dashboard filter toggle for completed tasks.
- **Header Subtitles**: Dual brand and workflow subtitles in header ("Soy Creadora. Tecnología para un fin" + process summary).
- **Inline Card Editing & Step Focus**: Full in-place editing of note titles, category/priority dropdowns, date pickers, and automated input focus when adding new checklist steps.

## [1.0.0] - 2026-09-26

### Added
- **Voice Dictation & Parsing**: Natural language Spanish dictation parser ([voice_parser.py](file:///Users/elena/Developer/Personal%20Assistent/voice_parser.py)) using Web Speech API with continuous dictation auto-restart loop.
- **FastAPI Web Server**: Standalone backend ([server.py](file:///Users/elena/Developer/Personal%20Assistent/server.py)) serving static web app and API endpoints for parsing, Notion sync, Obsidian export, and Google Calendar event URLs.
- **Visual Calendar Dashboard**: Interactive day-based Kanban board (*Hoy*, *Mañana*, *Próximos Días*, *Sin Fecha*) with editable card titles, categories, priorities, date-time pickers, and dynamic checklists.
- **Google Calendar Sync**: Instant template link generation for scheduling task events in Google Calendar.
- **Architecture Documentation**: Added ADR 0001 under `docs/adr/`.
