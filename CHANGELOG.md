# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-03-07

### Fixed
- Status no longer gets stuck in `waking` when the configured host probe port is unreachable but Ollama becomes ready.
- Dashboard no longer leaves stale `ready` visible after status refresh failures; it now shows a clear unavailable state.
- Desktop layout keeps the main state pill aligned on the right side.

### Improved
- Dashboard now auto-refreshes when the tab becomes visible or focused again.
- Dashboard auto-connects when a saved API key exists.

### Added
- Visible release version in the UI hero and footer.
- Regression test coverage for the host-probe-fails / Ollama-ready path.
