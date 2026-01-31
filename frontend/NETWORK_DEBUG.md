# Network Error Debugging Guide

## Error Analysis

The "Failed to fetch" error you encountered typically indicates:

1. **Backend not running** - API server at localhost:8000 is down
2. **CORS issues** - Backend not configured to allow frontend origin
3. **Network connectivity** - Firewall or network blocking the request
4. **Wrong API URL** - NEXT_PUBLIC_API_URL not set correctly (or should be unset in dev)

## Current Configuration

Your frontend is configured with:
- **Recommended in dev**: leave `NEXT_PUBLIC_API_URL` unset and use the Next.js proxy.
  - Base URL: `/api`
  - Next.js rewrite: `/api/*` -> `http://127.0.0.1:8000/*` (next.config.ts)
- **Optional env (advanced)**: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
  - Only use this if you intentionally want direct browser calls (no proxy).
  - IMPORTANT: must be backend root (do NOT add `/api`)
  - OK: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
  - KO: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api`

## Debugging Steps

### 0. Spot the proxy error (most common)
If you see this in the Next.js terminal:

`Failed to proxy http://127.0.0.1:8000/... Error: connect ECONNREFUSED 127.0.0.1:8000`

Then the backend isn't running (or isn't ready yet).

### 1. Check if backend is running
```bash
curl http://127.0.0.1:8000/health
# Should return JSON with status info
```

PowerShell equivalent:
```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### 2. Check Next.js proxy (if backend is running)
```bash
# Start frontend
npm run dev
# In another terminal:
curl http://localhost:3000/api/health
```

### 3. Verify environment configuration
```bash
# In dev, prefer NO .env.local (use proxy).
# If you do use .env.local, it must contain:
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 4. Test network connectivity
```bash
# Test direct connection
telnet localhost 8000
# Should connect successfully
```

## Error Handling Implementation

The frontend now includes:

1. **Enhanced error messages** in ActivityUpload component:
   - "Failed to fetch" → "Network error. Check API URL, CORS, or backend availability."
   - "Failed to parse URL" → "Invalid API URL. Check NEXT_PUBLIC_API_URL formatting."

2. **Network handling tests** in `src/lib/network-handling.test.ts`:
   - Error message generation logic
   - Backend detection logic
   - Base URL normalization (trailing slash allowed in input, trimmed in output)

3. **Improved user feedback** with specific guidance for different error types.

## Common Solutions

### Backend Not Running
```bash
# Navigate to backend directory and start:
cd ../backend  # or wherever your backend is
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### CORS Issues
Add to your backend FastAPI app:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Wrong Environment
```bash
# Set correct API URL:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

## Testing the Fix

1. Start backend server
2. Start frontend with correct environment
3. Try uploading a GPX/FIT file
4. Check browser console for `[API] request` / `[API] response` logs (dev)
5. Verify successful upload or get helpful error message

The tests confirm that error handling logic works correctly. The main issue is likely backend availability or configuration.
