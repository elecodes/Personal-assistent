# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-26

### Added
- **Voice Dictation & Parsing**: Natural language Spanish dictation parser ([voice_parser.py](file:///Users/elena/Developer/Personal%20Assistent/voice_parser.py)) using Web Speech API with continuous dictation auto-restart loop.
- **FastAPI Web Server**: Standalone backend ([server.py](file:///Users/elena/Developer/Personal%20Assistent/server.py)) serving static web app and API endpoints for parsing, Notion sync, Obsidian export, and Google Calendar event URLs.
- **Visual Calendar Dashboard**: Interactive day-based Kanban board (*Hoy*, *Mañana*, *Próximos Días*, *Sin Fecha*) with editable card titles, categories, priorities, date-time pickers, and dynamic checklists.
- **Obsidian Vault Integration**: Support for exporting Markdown notes directly to local Obsidian Vault directories and subfolders (`OBSIDIAN_VAULT_PATH` and `OBSIDIAN_FOLDER`), with fallback to official `obsidian://new?vault=...&file=...` URI routing.
- **Google Calendar Sync**: Instant template link generation for scheduling task events in Google Calendar.
- **Architecture Documentation**: Added ADR 0001 under `docs/adr/`.
