# QuantCouncil Web

Next.js 15 (App Router, TypeScript) dashboard for QuantCouncil, a personal AI
quant research and paper trading lab. Simulation only; no real money.

The foundation shell shows the module roadmap and a live health check against
the FastAPI backend.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000. Production build: `npm run build && npm run start`.

## Configuration

| Variable              | Default                 | Purpose                          |
| --------------------- | ----------------------- | -------------------------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the QuantCouncil API |

`NEXT_PUBLIC_API_URL` is inlined at build time, so set it before
`npm run build` (or in `.env.local` for `npm run dev`).
