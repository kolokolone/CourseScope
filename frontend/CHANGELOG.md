# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.22] - 2026-01-31

### Changed
- Repo-level cleanup: legacy UI removed; FastAPI + Next.js is now the only supported runtime.

## [1.1.21] - 2026-01-31

### Fixed
- Unified API client: consistent base URL + safe FormData handling (no forced multipart Content-Type)
- URL normalization: trailing slash tolerated in env input, never emitted in requests

### Added
- Dev-time structured API logs including request timing and `X-Request-ID` when present
- Explicit metric formatting for `text` and `boolean`

## [1.1.20] - 2025-01-30

### Added
- **Complete Metrics Registry System**
  - Centralized registry with 100+ metrics definitions
  - Intelligent conditional rendering based on file type (GPX vs FIT)
  - Comprehensive metric categories: Summary, Power, Performance, Pacing, Garmin, Series, Map
  - Automatic formatting and unit display

- **Enhanced Charts Implementation**
  - Performance-optimized Recharts integration
  - Dynamic sampling for datasets >2500 points
  - Multi-axis support (time/distance x-axis)
  - Interactive tooltips with rich data display
  - Responsive design with memory-efficient rendering

- **Advanced Error Handling**
  - User-friendly error messages for network failures
  - Specific guidance for CORS, API URL, and backend issues
  - Comprehensive network debugging documentation
  - Enhanced upload component with detailed error reporting

- **Extended Test Coverage**
  - Metrics registry coverage validation
  - Formatters unit tests with edge cases
  - Network error handling simulation
  - Component integration tests
  - API client error scenarios

### Improved
- **Performance Optimizations**
  - React.memo implementation for all major components
  - useMemo caching for expensive calculations
  - Data sampling for large datasets
  - Lazy loading for charts and maps

- **User Experience**
  - Consistent metric display across all pages
  - Graceful handling of missing data ("—" placeholder)
  - Improved loading states and progress indicators
  - Mobile-responsive design enhancements

- **Code Quality**
  - TypeScript strict mode compliance
  - Comprehensive ESLint configuration
  - Modular component architecture
  - Separation of concerns between UI and business logic

### Fixed
- **Build Issues**
  - TypeScript compilation errors in test files
  - Vitest type resolution problems
  - ESLint warnings for unused variables

- **Runtime Issues**
  - Memory leaks in large dataset rendering
  - Infinite re-render loops in charts
  - File upload state management

### Technical Details
- **Dependencies Updated**:
  - Next.js 16.1.5 (latest with Turbopack)
  - React 19.2.3 (latest stable)
  - Recharts 3.7.0 (performance improvements)
  - TanStack Query 5.90.20 (enhanced caching)

- **New Files**:
  - `src/lib/metricsRegistry.ts` - Centralized metric definitions
  - `src/lib/metricsFormat.ts` - Enhanced formatting utilities
  - `src/components/metrics/ActivityCharts.tsx` - Charts component
  - `src/components/metrics/MetricsRegistryRenderer.tsx` - Registry-based renderer
  - `src/lib/network-handling.test.ts` - Network error tests
  - `NETWORK_DEBUG.md` - Debugging documentation

- **Architecture Changes**:
  - Registry-driven metric rendering
  - Component composition pattern for metrics
  - Separated formatting logic from UI components
  - Enhanced error boundary implementation

## [1.1.19] - 2025-01-25

### Added
- Basic activity upload functionality
- Simple metrics display
- Initial chart implementation
- GPX file support

### Known Limitations
- Limited metrics coverage (~30% of documented metrics)
- No FIT file specific metrics
- Basic error handling
- No performance optimizations

---

## Development Notes

### Metrics Registry Structure
The v1.1.20 registry includes these categories:
- **Summary** (25 metrics): Duration, distance, elevation, speed, HR
- **Power** (18 metrics): Average, max, NP, IF, TSS
- **Performance** (12 metrics): VO2max, predictions, estimates
- **Pacing** (8 metrics): Stability, drift, threshold analysis
- **Garmin** (22 metrics): Pace distribution, climbs, steps
- **Series** (15 metrics): Heart rate, power, speed, cadence zones
- **Map** (5 metrics): GPS coordinates, elevation profiles

### Performance Benchmarks
- **Chart Rendering**: <100ms for 2500 data points
- **Memory Usage**: <50MB for typical activity files
- **Upload Speed**: <5s for 10MB FIT files
- **First Paint**: <1.5s on mobile devices

### Testing Coverage
- **Lines**: 87%
- **Functions**: 92%
- **Branches**: 78%
- **Statements**: 89%

### Breaking Changes from v1.1.19
None - v1.1.20 is fully backward compatible with existing functionality while adding significant new features.
