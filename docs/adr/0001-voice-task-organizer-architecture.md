# 1. Voice Task Organizer Architecture and Multi-Destination Sync

* Status: Accepted
* Date: 2026-09-26

## Context and Problem Statement

The user needed an intuitive productivity tool to capture thoughts and tasks via voice dictation without manual pen-and-paper overhead, convert spoken notes into structured visual cards with actionable checklists, and automatically schedule date-bound items into calendars and knowledge bases (Notion and Obsidian).

## Decision Drivers

* **Zero Cost (Free Tier First)**: Eliminate subscription and API costs by prioritizing native browser capabilities (Web Speech API) and free-tier APIs/protocols.
* **Low Friction Capture**: Support continuous Spanish voice dictation without premature auto-pausing.
* **Visual Actionable Organization**: Group tasks into a day-based calendar board (*Hoy*, *Mañana*, *Próximos días*, *Sin Fecha*) with editable checklist steps and explicit task completion toggles.
* **Silent Background Knowledge Base Export**: Export notes to Obsidian directly in background disk mode (`obsidian_vault/Substack`) without launching or interrupting the user with desktop app focus changes.
* **Multi-destination Ecosystem Integration**: Sync structured tasks seamlessly to Notion API, local Obsidian Vaults, and Google Calendar.

## Considered Options

1. **Monolithic Heavy Frontend**: Complex React SPA with paid cloud STT (Whisper API).
2. **Lightweight Python (FastAPI) + Web Speech API Frontend**: Pure Javascript client using Web Speech API, a lightweight FastAPI backend for parsing/Notion/Obsidian endpoints, and zero external JS frameworks.

## Decision Outcome

Chosen option: **Option 2 (FastAPI + Web Speech API Frontend)** because it delivers $0 operational cost, instant local execution, continuous browser-native voice dictation, and seamless integration with existing `notion_client.py` and local Obsidian Vault paths.

### Positive Consequences

* $0 operational cost across voice recognition, Text-to-Speech (TTS) daily playback, Notion API, Obsidian Markdown export, and Google Calendar links.
* Responsive, zero-latency visual board with inline editable cards, checklists, calendar date pickers, and daily column audio summaries.
* 100% silent background Markdown note writing into `obsidian_vault/Substack` with fallback to official `obsidian://new?vault=...&file=...&content=...` URI routing.

### Negative Consequences & Future Considerations

* Web Speech API & SpeechSynthesis capabilities depend on browser voice engines (robotic default voice in some OS/browsers). Evaluation of external free-tier/low-cost TTS alternatives (e.g. Amazon Polly) pending for future enhancement.
