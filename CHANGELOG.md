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

## [1.1.22] - 2026-01-31

### Changed
- Legacy UI removed; FastAPI + Next.js is now the only supported runtime.

## [1.1.21] - 2026-01-31

### Fixed
- Upload + API routing hardened; `/api/*` compatibility preserved.
