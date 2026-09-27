# 2. Firebase Cloud Persistence, Amazon Polly Neural TTS, and Notion Data Source Integration

* Status: Accepted
* Date: 2026-09-27

## Context and Problem Statement

The user requested expanding the Voice Task & Notes Assistant to include:
1. **Cloud Persistence (Free Tier)**: Store both text notes/metadata and audio files in a cloud database instead of staying strictly local.
2. **High-Definition Voice Synthesis**: Replace browser-native robotic TTS with natural, human-like voice synthesis using Amazon Polly.
3. **Notion Database & Calendar Sync**: Ensure seamless task insertion into Notion Database Tables (Calendar view) supporting `multi_select` properties and Data Source API standards.
4. **Smart Voice Parsing & Anglicisms**: Parse complex natural Spanish voice dictations and technical anglicisms (`deploy`, `meeting`, `PR`, `commit`, `merge`, `push`, etc.) into multi-line structured checklists.

## Decision Drivers

* **Free Tier First Cloud Database & Storage**: Selected **Firebase (Cloud Firestore + Cloud Storage)** for NoSQL document persistence and audio storage within generous free-tier limits.
* **Neural Speech Quality**: Selected **Amazon Polly** (Neural Engine) with Spanish voices (`Lupe`, `Mia`, `Lucia`) for human-like Text-to-Speech audio streaming.
* **Robust Notion API Integration**: Upgraded `notion_client.py` to support Notion Data Sources, `multi_select` schema formats, and automatic fallback chains (`data_source_id` -> `database_id` -> `page_id`).
* **Intelligent Dictation Parsing**: Enhanced `voice_parser.py` with multi-line regex patterns, transition connectors, and tech anglicism dictionaries.

## Decision Outcome

1. **Firebase Integration (`firebase_client.py`)**:
   - `Cloud Firestore`: Stores notes, category, priority, date_time, tags, and audio URLs.
   - `Cloud Storage`: Holds uploaded `.mp3` audio files with public URL generation.
2. **Amazon Polly Integration (`polly_client.py` & `server.py`)**:
   - Implemented `PollyManager` with `boto3` support for Neural TTS.
   - Added `/api/polly/stream` endpoint in `server.py` and updated web UI (`static/index.html`) to stream Amazon Polly Neural audio.
3. **Notion Schema & API Support (`notion_client.py`)**:
   - Updated `build_task_properties` to format `Categoría` and `Prioridad` as `multi_select`.
   - Updated `insert_task` to handle Notion Data Sources and database fallback chains.
4. **Anglicism & Multi-Line Voice Parser (`voice_parser.py`)**:
   - Added recognition for technical anglicisms (`deploy`, `meeting`, `PR`, `pull request`, `commit`, `merge`, `push`, `sync`, `test`, `review`, `feedback`, `backup`, `issue`, `bug`, `feature`).
   - Automatically formats spoken action phrases into multi-line checklist items with bullet points (`•`).

## Consequences

* Cloud persistence for all notes and voice audio available in Firebase Free Tier.
* High-fidelity, natural Spanish voice playback across web UI and API endpoints.
* Seamless synchronization to Notion Calendar Databases.
