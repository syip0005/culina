# Culina Frontend

React frontend for Culina, a nutrition tracking application with AI-powered food lookup.

## Tech Stack

- **Framework:** React 19 + TypeScript 5.9
- **Routing:** TanStack Router (file-based, auto code-splitting)
- **Build:** Vite 8
- **Auth:** Supabase (Google & GitHub OAuth)
- **Styling:** Single CSS file, brutalist black-and-white design system
- **State:** React hooks (useState/useEffect/useContext) — no external state library

## Getting Started

### Prerequisites

- Node.js 20+
- npm
- Running backend (see `../backend/culina-backend/README.md`)
- Supabase project (for OAuth)

### Local Development

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Configure environment variables:**

   Create a `.env` file:

   ```
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key
   VITE_BACKEND_URL=http://localhost:8000
   ```

   | Variable | Description |
   |---|---|
   | `VITE_SUPABASE_URL` | Supabase project URL |
   | `VITE_SUPABASE_ANON_KEY` | Supabase anonymous/publishable key |
   | `VITE_BACKEND_URL` | Backend API URL (default: `http://localhost:8000`) |

3. **Start the dev server:**

   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`.

## Project Structure

```
frontend/
├── src/
│   ├── routes/                     # TanStack Router file-based routes
│   │   ├── __root.tsx              # Root layout (AuthProvider wrapper)
│   │   ├── _authenticated.tsx      # Auth guard layout (redirects to /login)
│   │   ├── _authenticated/
│   │   │   ├── index.tsx           # Home — daily tracking dashboard
│   │   │   ├── settings.tsx        # Settings — targets, timezone, preferences
│   │   │   └── stats.tsx           # Stats — week/fortnight/month/year analytics
│   │   └── login.tsx               # Login — Supabase OAuth
│   ├── components/
│   │   ├── AddItemPanel.tsx        # Search overlay for adding food items
│   │   ├── EditEntryPanel.tsx      # Modal for editing/creating nutrition entries
│   │   ├── LookupView.tsx          # AI multi-turn conversation overlay
│   │   ├── MealSection.tsx         # Meal display with items, inline editing
│   │   ├── NutritionSummary.tsx    # Reusable macro display (energy/protein/fat/carbs)
│   │   └── Icons.tsx               # SVG icon components
│   ├── utils/
│   │   ├── date.ts                 # Timezone-aware date helpers
│   │   ├── debounce.ts             # useDebounce hook
│   │   ├── energy.ts               # kJ ↔ kcal conversion
│   │   ├── prefetch.ts             # Cross-route data cache (60s TTL)
│   │   └── serving.ts             # Serving unit display helpers
│   ├── api.ts                      # Typed API client (Bearer token auto-attached)
│   ├── auth.tsx                    # AuthProvider + useAuth() hook
│   ├── types.ts                    # TypeScript interfaces (mirrors backend schemas)
│   ├── supabase.ts                 # Supabase client singleton
│   ├── main.tsx                    # App entry point
│   └── index.css                   # All styles (brutalist B&W design system)
├── package.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```

## Pages

### Home (`/`)

Daily nutrition tracking dashboard.

- Date navigation via keyboard arrows or swipe on mobile
- Daily macro summary (consumed vs remaining, toggleable)
- Four meal sections: Breakfast, Lunch, Dinner, Snacks
- Current meal type auto-highlighted based on time of day
- Add items via search, AI lookup, or manual creation
- Inline quantity editing on existing items
- Optimistic UI updates for all mutations
- Background prefetch of adjacent days

### Settings (`/settings`)

User configuration.

- Daily macro targets (energy, protein, fat, carbs)
- Per-macro goal modes: under, over, or within tolerance
- Timezone and energy unit preference (kJ/kcal)
- Sign out

### Stats (`/stats`)

Historical analytics with period navigation.

- **Week/Fortnight:** Daily table with macros and on-target status
- **Month:** Calendar grid showing daily on-target results
- **Year:** Monthly bar chart showing on-target ratios

### Login (`/login`)

Supabase OAuth with Google and GitHub providers.

## Design System

Brutalist black-and-white aesthetic:

- **Colors:** White background, black foreground, no shadows
- **Borders:** 2px solid black, no border-radius
- **Typography:** Outfit font, bold uppercase headings
- **Layout:** Max 480px container, mobile-first

All styles in `src/index.css` using CSS custom properties. No CSS modules or CSS-in-JS.

## Development Commands

```bash
npm run dev       # Start Vite dev server (port 3000)
npm run build     # TypeScript check + production build
npm run lint      # ESLint
npm run preview   # Preview production build
```
