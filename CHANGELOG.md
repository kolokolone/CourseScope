# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.1.23] - 2026-01-31

### Changed
- Consolidate documentation sources (root changelog + simplified frontend README).
- Ensure derived series used by the `/activity/{id}/series/*` endpoints reuse core implementations.

### Fixed
- Series endpoint robustness: avoid NaN filtering crashes for non-numeric series.

## [1.1.24] - 2026-01-31

### Changed
- Windows launcher: run_win.bat now relaunches itself into a dedicated console and starts API + frontend more reliably.
- CI: pipeline remains strict (fails on any test/build failure) and matches the real repo.

## [1.1.25] - 2026-01-31

### Fixed
- Windows launcher: simplified execution flow and added `--smoke` prereq check.

## [1.1.26] - 2026-01-31

### Fixed
- Windows launcher: start API + frontend in dedicated windows and keep the launcher open for diagnostics.

## [1.1.27] - 2026-01-31

### Fixed
- Windows launcher: skip reinstalling frontend deps when `frontend/node_modules/` already exists (much faster subsequent starts).

## [1.1.28] - 2026-01-31

### Fixed
- Upload networking: default dev flow now uses Next.js `/api/*` proxy (no direct browser calls), avoiding CORS/host edge cases.

## [1.1.22] - 2026-01-31

### Changed
- Legacy UI removed; FastAPI + Next.js is now the only supported runtime.

## [1.1.21] - 2026-01-31

### Fixed
- Upload + API routing hardened; `/api/*` compatibility preserved.
