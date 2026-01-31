# Cycling Stats Frontend

A comprehensive cycling analytics dashboard built with Next.js, React, and TypeScript that displays detailed activity metrics, charts, and maps.

## Features

### 🚀 Core Functionality
- **Activity Upload**: Drag & drop GPX/FIT file upload with comprehensive error handling
- **Metrics Dashboard**: Complete metrics coverage with 100+ data points
- **Interactive Charts**: Multi-axis charts with Recharts, supporting time/distance views
- **Activity Maps**: Interactive Leaflet maps with polyline rendering
- **Responsive Design**: Mobile-first UI with Tailwind CSS and Radix UI

### 📊 Metrics Coverage
- **Summary Metrics**: Duration, distance, elevation, speed, heart rate, power, cadence
- **Advanced Metrics**: Training load, performance predictions, power curves, grade analysis
- **Garmin Integration**: Pace distribution, climb analysis, step data, filtered elevations
- **Pacing Analysis**: Stability metrics, drift calculations, threshold analysis
- **Series Data**: Heart rate, power, speed, cadence, elevation, temperature, grade
- **Map Integration**: GPS coordinates with downsampling for performance

### 🎨 UI Components
- **Metrics Registry**: Centralized metric definitions with intelligent formatting
- **Dynamic Rendering**: Conditional display based on file type (GPX vs FIT)
- **Performance Optimized**: Sampling for large datasets, memoized components
- **Error Handling**: User-friendly error messages with network diagnostics

## Tech Stack

- **Framework**: Next.js 16.1.5 with App Router
- **UI**: React 19.2.3, TypeScript 5, Tailwind CSS 4
- **Charts**: Recharts 3.7.0 with custom performance optimizations
- **Maps**: React Leaflet 5.0.0 with Leaflet 1.9.4
- **File Upload**: React Dropzone 14.3.8
- **State Management**: TanStack Query 5.90.20 for server state
- **Icons**: Lucide React 0.563.0
- **Testing**: Vitest 1.6.0 with Testing Library

## Getting Started

### Prerequisites
- Node.js 18+
- Backend API running on `http://localhost:8000` (see Network Debugging section)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd cycling-stats-frontend

# Install dependencies
npm install

# Optional: set up environment variables (direct backend calls)
# IMPORTANT: NEXT_PUBLIC_API_URL must be the backend root (no trailing "/api")
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### Development

```bash
# Start development server
npm run dev

# Or with alternative package managers
yarn dev
pnpm dev
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run test` - Run tests in watch mode
- `npm run test:watch` - Run tests with interactive watch

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── activity/[id]/      # Dynamic activity pages
│   │   ├── real/          # Real activity data
│   │   └── theoretical/    # Theoretical calculations
│   └── page.tsx           # Home page
├── components/             # Reusable React components
│   ├── metrics/           # Metrics display components
│   ├── upload/            # File upload components
│   └── ui/               # Base UI components
├── lib/                   # Utility libraries
│   ├── api.ts             # API client with error handling
│   ├── metricsRegistry.ts  # Centralized metrics definitions
│   └── metricsFormat.ts   # Formatting utilities
├── hooks/                 # React hooks
│   └── useActivity.ts     # Activity data hooks
└── types/                 # TypeScript definitions
```

## Metrics Registry System

The application uses a centralized metrics registry (`src/lib/metricsRegistry.ts`) that:

- **Defines 100+ metrics** with paths, categories, and metadata
- **Handles conditional rendering** based on file type (GPX vs FIT)
- **Provides consistent formatting** across all metric displays
- **Supports hierarchical paths** for nested data structures

### Categories
- **Summary**: Duration, distance, elevation, speed, heart rate
- **Power**: Average, max, normalized, training load
- **Performance**: VO2max, performance predictions
- **Pacing**: Stability, drift, threshold analysis
- **Garmin**: Extended metrics for Garmin devices
- **Series**: Time-series data for charts
- **Map**: GPS coordinates and elevation data

## Charts & Visualization

### Performance Features
- **Dynamic Sampling**: Automatically samples data >2500 points for performance
- **Multi-Axis Support**: Switch between time and distance x-axis
- **Interactive Tooltips**: Rich data display on hover
- **Responsive Design**: Charts adapt to screen size
- **Memory Efficient**: Uses React.memo and useMemo for optimization

### Chart Types
- **Line Charts**: Heart rate, power, speed, cadence over time/distance
- **Area Charts**: Elevation profiles with gradient fills
- **Scatter Plots**: Power distribution and analysis
- **Combined Charts**: Multiple metrics with dual y-axis

## Network Debugging

### Common Issues

If you encounter "Failed to fetch" errors:

1. **Check Backend Status**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify Environment**:
   ```bash
   cat .env.local
   # Should contain: NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Test Proxy** (development):
   ```bash
   curl http://localhost:3000/api/health
   ```

### Enhanced Error Messages

The application provides specific error guidance:
- **Network errors**: "Check API URL, CORS, or backend availability"
- **URL errors**: "Check NEXT_PUBLIC_API_URL formatting"
- **API errors**: Detailed messages from backend

### API Base URL Rules (v1.1.22)
- Default (no env): `/api` (Next.js rewrite)
- If `NEXT_PUBLIC_API_URL` is set: used as base URL after trimming trailing slashes
- Do NOT set `NEXT_PUBLIC_API_URL` to a value ending with `/api`

For complete debugging guide, see [NETWORK_DEBUG.md](./NETWORK_DEBUG.md).

## Testing

### Test Suite
- **Unit Tests**: Component logic, utilities, hooks
- **Integration Tests**: API client, error handling
- **Coverage**: Formatters, registry, network handling

### Running Tests
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm test -- --coverage
```

### Test Structure
```
src/
├── components/*/           # Component tests
├── lib/                   # Utility tests
└── network-handling.test.ts # Network error logic
```

## Performance Optimizations

### Frontend Optimizations
- **React.memo**: Prevent unnecessary re-renders
- **useMemo**: Cache expensive calculations
- **Code Splitting**: Dynamic imports for charts and maps
- **Data Sampling**: Limit chart data points for large datasets
- **Lazy Loading**: Components loaded on demand

### API Optimizations
- **Query Caching**: TanStack Query with 5-10 minute cache
- **Prefetching**: Related data preloaded when needed
- **Background Updates**: Stale-while-revalidate strategy

## Deployment

### Environment Setup
```bash
# Production build
npm run build

# Environment variables (production)
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `npm test`
5. Commit your changes: `git commit -m "Add feature"`
6. Push to the branch: `git push origin feature-name`
7. Open a Pull Request

### Development Guidelines
- Follow TypeScript best practices
- Use the metrics registry for new metrics
- Add tests for new features
- Maintain test coverage above 80%
- Use conventional commit messages

## Version History

### v1.1.22 (Current)
- **Unified API client**: one `apiRequest()` for JSON + uploads (FormData)
- **Base URL rules**: defaults to `/api` rewrite; `NEXT_PUBLIC_API_URL` must be backend root (no `/api`)
- **Better debugging**: dev logs include request timing and `X-Request-ID` when present
- **Formatters**: explicit handling for `text` + `boolean` metric formats
- **Complete Metrics Registry**: 100+ metrics with intelligent formatting
- **Enhanced Charts**: Performance-optimized Recharts integration
- **Network Error Handling**: User-friendly error messages and debugging
- **Test Coverage**: Comprehensive test suite with network handling tests
- **UI Improvements**: Responsive design and accessibility enhancements

### v1.1.20
- **Complete Metrics Registry**: 100+ metrics with intelligent formatting
- **Enhanced Charts**: Performance-optimized Recharts integration
- **Network Error Handling**: User-friendly error messages and debugging
- **Test Coverage**: Comprehensive test suite with network handling tests
- **UI Improvements**: Responsive design and accessibility enhancements

### v1.1.19
- Basic metrics display
- Simple file upload
- Initial chart implementation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [Network Debugging Guide](./NETWORK_DEBUG.md)
2. Review existing [GitHub Issues](https://github.com/your-repo/issues)
3. Create a new issue with detailed information

---

Built with ❤️ for the cycling community
