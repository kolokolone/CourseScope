# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.1.30] - 2026-01-31

### Fixed
- Windows startup: run_win.bat waits for backend /health before starting the frontend (prevents proxy ECONNREFUSED).
- Frontend logs: failed API responses are logged at warn-level to avoid dev overlay noise.

## [1.1.29] - 2026-01-31

### Fixed
- Upload networking (dev): frontend now ignores `NEXT_PUBLIC_API_URL` outside production and always uses the Next.js `/api/*` proxy to avoid CORS/host issues.

### Changed
- Docs: README changelog section now links to this file (no duplicated version blocks).

## [1.1.28] - 2026-01-31

### Fixed
- Upload networking: Next.js rewrite now proxies `/api/*` to `http://127.0.0.1:8000/*` (avoids Windows localhost edge cases).

### Changed
- Windows launcher: run_win.bat no longer forces direct backend URL for the frontend; dev defaults to proxy.

## [1.1.27] - 2026-01-31

### Fixed
- Windows launcher: skip reinstalling frontend deps when `frontend/node_modules/` exists (faster subsequent starts).

## [1.1.26] - 2026-01-31

### Fixed
- Windows launcher: start API + frontend in dedicated windows and keep the launcher open for diagnostics.

## [1.1.25] - 2026-01-31

### Fixed
- Windows launcher: simplified execution flow and added `--smoke` prereq check.

## [1.1.24] - 2026-01-31

### Changed
- CI: GitHub Actions workflow hardened and aligned with real repo commands.

## [1.1.23] - 2026-01-31

### Changed
- Docs: consolidated to a single source of truth; added root changelog and roadmap.
- Backend: series registry now reuses core computations for grade/moving.

### Fixed
- Series endpoint robustness: avoid NaN filtering crashes for non-numeric series.

## [1.1.22] - 2026-01-31

### Changed
- Legacy UI removed; FastAPI + Next.js is now the only supported runtime.

## [1.1.21] - 2026-01-31

### Fixed
- Upload + API routing hardened; `/api/*` compatibility preserved.
