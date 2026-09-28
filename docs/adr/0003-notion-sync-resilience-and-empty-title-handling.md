# 3. Notion Sync Resilience and Empty Title Handling

* Status: Accepted
* Date: 2026-09-28

## Context and Problem Statement

When creating blank cards in the dashboard without immediate dictation or explicit titles, syncing to Notion or Obsidian presented edge cases:
1. Blank titles sent to `/api/tasks` lacked default fallbacks.
2. Network execution isolation requirements during background server process startup needed validation to guarantee uninterrupted Notion API (`api.notion.com`) HTTPS communication.

## Decision Drivers

* **Fail-Safe Task Creation**: Ensure every task sent to Notion has a valid, non-empty title string.
* **Network & Endpoint Reliability**: Validate end-to-end HTTP request processing for external API sync.

## Decision Outcome

1. **Empty Title Fallback in Backend (`server.py`)**:
   - Updated `create_task` endpoint to strip input titles and fallback to `"Nueva Idea"` whenever an empty string or whitespace is provided.
2. **Notion & Obsidian Endpoint Verification**:
   - Confirmed full end-to-end HTTP 200 payload responses for Notion Data Source pages and Obsidian Markdown file exports.

## Consequences

* Robust task synchronization to Notion even for newly created, unpopulated cards.
* Reliable, error-free API responses for all card creation workflows.
