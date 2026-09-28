# 4. Mobile-First Progressive Web App (PWA) Architecture

* Status: Accepted
* Date: 2026-09-28

## Context and Problem Statement

The Voice Task & Notes Assistant required seamless mobile device usability, allowing users to dictate notes, organize task cards, and install the application directly onto their mobile home screens (iOS/Android).

## Decision Drivers

* **Cross-Device Mobile First Experience**: Mobile viewports (< 768px) need touch-optimized layouts without vertical scroll clutter.
* **Home Screen Installation (PWA)**: Allow users to add the application to their home screen as a standalone web application without App Store deployment overhead.
* **Prevent iOS Auto-Zoom UX Issues**: Form inputs on mobile Safari auto-zoom if font sizes are smaller than 16px.

## Decision Outcome

1. **PWA Manifest & Server Integration (`static/manifest.json` & `server.py`)**:
   - Created `static/manifest.json` defining standalone app settings, theme color (`#0f172a`), and app metadata.
   - Added `/manifest.json` endpoint in `server.py`.
2. **Mobile Tabbed Column Navigation (`static/index.html`)**:
   - Implemented responsive segmented tab control (`#mobileColumnTabs`) for screens under 768px.
   - Users can toggle between *Hoy*, *Mañana*, *Próximos*, and *Backlog* views with live badge counts.
3. **Touch Targets & Prevent Auto-Zoom**:
   - Configured form inputs to 16px on mobile viewports to stop Safari auto-zooming.
   - Expanded touch target heights for all buttons (`.action-btn-pill`).

## Consequences

* Immediate installation support via "Add to Home Screen" on iOS and Android.
* Fluid mobile dictation and board management on any smartphone.
