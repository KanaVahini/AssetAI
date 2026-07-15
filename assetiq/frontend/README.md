# AssetIQ Frontend

React + Vite frontend for the AssetIQ Copilot.

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Make sure the backend is running first, in your `assetiq` project:
   ```
   python backend/main.py
   ```
   It should be live at http://localhost:8000

3. Start the frontend:
   ```
   npm run dev
   ```
   Opens at http://localhost:5173

## Structure

- `src/services/api.js` — all backend API calls (only place that talks to FastAPI)
- `src/pages/` — Home, Copilot (chat), Upload
- `src/components/` — Sidebar, MessageBubble, SourceCard, Loader

## Notes

- Backend URL is hardcoded in `src/services/api.js` as `http://localhost:8000` — change it there if you deploy the backend elsewhere.
- No CSS files needed beyond `src/index.css` — all components use inline styles.
