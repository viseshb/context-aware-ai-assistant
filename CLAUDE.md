# Context-Aware AI Assistant - Project Instructions

## Project Overview
A production-grade, open-source Context-Aware AI Assistant using MCP (Model Context Protocol) to integrate GitHub, Slack, and PostgreSQL. Users query code repositories, team discussions, and database metrics via natural language across 10 switchable LLM providers. Built with FastAPI (Python) backend and Next.js (React) frontend.

**This is a real portfolio project going on the user's resume and will be open-sourced on GitHub. It must be professional, fully functional, and impressive.**

## Tech Stack (DO NOT CHANGE)

### Backend
- **Python 3.12** with **FastAPI**
- **MCP SDK** (`mcp` package) for Model Context Protocol
- **Pydantic** for validation, **Pydantic Settings** for env config
- **httpx** for async HTTP (GitHub API, Slack API)
- **asyncpg** for PostgreSQL
- **matplotlib** for chart generation
- **presidio-analyzer + presidio-anonymizer** for PII detection/redaction
- **slowapi** for rate limiting
- **sqlparse** for SQL read-only enforcement
- **python-jose + passlib[bcrypt]** for JWT auth
- **structlog** for logging

### Frontend
- **Next.js 16.2** (App Router) — Devtools MCP, context-aware diagnostics, auto error stack traces, React Compiler
- **React 19**
- **TypeScript** (strict)
- **Tailwind CSS v4**
- **Zustand** for state management
- **@tanstack/react-query** for server state
- **Framer Motion** for animations
- **Recharts** for inline charts
- **react-markdown + remark-gfm** for markdown rendering
- **react-syntax-highlighter** for code blocks
- **Lucide React** for icons (SVG, NEVER emojis as icons)
- **@fontsource/plus-jakarta-sans** for typography

## LLM Models (10 Providers, NO Default)

User MUST select a model before chatting. No default model. Model selector is a card grid, NOT a dropdown.

| Model | Provider | Tier |
|-------|----------|------|
| Gemini 2.5 Flash Lite | Google API | Free |
| Llama 4 Maverick | NVIDIA NIM | Free |
| Ministral 14B | NVIDIA NIM | Free |
| Gemini 2.5 Flash | Google API | Free |
| Kimi K2 | NVIDIA NIM | Free |
| Claude CLI | Subprocess | Free (Pro/Max) |
| Gemini 3.1 Flash Lite | Google API | Free |
| Gemini 3 Flash | Google API | Free |
| Claude API | Anthropic SDK | Paid |
| OpenAI gpt-4.1-mini | OpenAI SDK | Paid |

All API keys configured via `.env` file.

## UI/UX Rules (CRITICAL)

### Design System
- **Background:** `#0F172A` (slate-950)
- **Panels:** `#1E293B` (slate-800)
- **CTA/Active:** `#22C55E` (green-500)
- **Text:** `#F8FAFC` (slate-50)
- **Text Muted:** `#94A3B8` (slate-400)
- **Font:** Plus Jakarta Sans (all text)
- **Glass cards:** `bg-slate-800/70 backdrop-blur-xl border border-white/[0.08]`

### Design Principles
- **NOT AI SLOP** — Do NOT make it look like a generic ChatGPT/AI chatbot clone
- User messages: right-aligned with green-tinted background
- Assistant messages: left-aligned with panel background
- NOT centered ChatGPT-style layout
- Tool execution: collapsible cards with green progress animation
- Context badges: color-coded pills (GitHub=gray, Slack=purple, DB=blue)
- All transitions: 150-300ms, smooth
- Respect `prefers-reduced-motion`

### Icon Rules
- ONLY use Lucide React (SVG icons)
- NEVER use emojis as UI icons
- Consistent sizing: 24x24 viewBox, w-6 h-6

### Pre-Delivery Checklist (run before every UI commit)
- [ ] No emojis used as icons
- [ ] All clickable elements have `cursor-pointer`
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light/dark text contrast >= 4.5:1
- [ ] Focus states visible for keyboard navigation
- [ ] Responsive at 375px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile

## Authentication & RBAC

### User Flow
1. **Landing page** (`/`) — public, trendy marketing page explaining the tool
2. **Sign up** (`/signup`) — creates account with `viewer` role (no tool access)
3. **Login** (`/login`) — returns JWT token + user profile with role/permissions
4. **Chat** (`/chat`) — protected, requires auth. Tool access based on RBAC role
5. **Admin** (`/admin`) — protected, requires admin role. User/permission management

### Roles
- **admin** — full access: all tools, all resources, settings, user management
- **member** — assigned access: only their permitted repos/channels/tables
- **viewer** — chat only: LLM answers from its own knowledge, no tool calls

### First Admin
```bash
python -m app.security.jwt_auth create-admin --username admin --email admin@local
```

## Security (NO COMPROMISE)

### 8-Layer Defense-in-Depth
1. **Authentication** — ALL users must login, JWT + bcrypt, 24h token expiry
2. **RBAC** — role-based tool filtering, per-user resource allowlists, checked BEFORE every tool call
3. **Rate Limiting** — 30 req/min REST, 20 msg/min WebSocket, 5 login attempts/min (brute force)
4. **Input Validation** — Pydantic schemas, max 10,000 char messages, password strength requirements
5. **Allowlist Enforcement** — per-user allowed repos/channels/tables, validated BEFORE tool execution
6. **Read-Only Enforcement** — SQL parsed with sqlparse (only SELECT), SET TRANSACTION READ ONLY, GitHub GET-only, Slack read-only scopes
7. **PII Filtering** — presidio scans ALL LLM responses, redacts emails/phones/SSNs/credit cards/IPs
8. **Audit Logging** — every action logged with user_id: tool calls, security events, login attempts, PII redactions

### Security Rules
- NEVER allow SQL mutations (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT)
- NEVER expose API keys in frontend or API responses
- ALWAYS validate tool call arguments against user's RBAC permissions BEFORE execution
- ALWAYS scan LLM output for PII BEFORE sending to frontend
- ALWAYS log security-relevant events to audit log with user attribution
- Viewer role users NEVER get tool access — LLM answers from its own knowledge only

## Architecture

### Backend Structure
```
backend/app/
├── main.py          # FastAPI app, lifespan, CORS
├── config.py        # Pydantic Settings from .env
├── api/             # REST + WebSocket endpoints
├── llm/             # LLM provider abstraction + 5 provider implementations
├── mcp_layer/       # MCP client, manager, 3 MCP servers (GitHub/Slack/Postgres)
├── security/        # PII filter, allowlists, rate limiter, read-only, JWT auth, audit log
├── services/        # Chat orchestrator, summarizer, chart service, context tracker
├── schemas/         # Pydantic models
└── utils/           # Logging, error handlers
```

### Frontend Structure
```
frontend/src/
├── app/             # Next.js App Router pages
│   ├── page.tsx         # Landing page (public)
│   ├── (auth)/          # Login + Signup pages
│   ├── (protected)/     # Chat + Admin (require auth)
│   └── middleware.ts    # JWT route protection
├── components/      # UI components (landing, auth, layout, chat, model, context, tools, rich, admin, ui)
├── stores/          # Zustand stores (chat, model, auth, ui)
├── hooks/           # Custom hooks (useChat, useModels, useAuth)
├── services/        # API client, WebSocket client
└── config/          # Theme tokens, model metadata
```

### MCP Servers
- Each runs as a **subprocess** using **stdio transport**
- MCPManager spawns/manages all servers on FastAPI startup
- GitHub server: 7 read-only tools
- Slack server: 5 read-only tools
- Postgres server: 4 read-only tools (SQL validated)

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # runs on port 3000

# Tests
cd backend && python -m pytest tests/ -v

# Admin setup
cd backend && python -m app.security.admin_auth create-admin
```

## Plan File
Full implementation plan: `.claude/plans/flickering-crunching-giraffe.md`

## Landing Page + Footer
- Landing page at `/` is public (no auth required)
- Sections: LandingNavbar, HeroSection (animated), FeaturesGrid (bento), HowItWorks, SecurityBadges, CTAFooter, Footer
- **Footer:** "Created by Visesh Bentula" + "Contact Us" link
- **Contact Us:** Opens modal with Name, Email, Subject, Body fields + "Send Email" button
- **Contact backend:** `POST /api/contact` sends email to `visesh66@gmail.com` (HARDCODED in backend .env, NEVER exposed to frontend)
- Contact email is rate-limited to 3/min per IP

## Key Decisions (DO NOT OVERRIDE)
- WebSocket for real-time chat streaming, REST for metadata endpoints
- MCP servers as subprocesses (stdio), not HTTP
- Zustand over Redux (lightweight, no boilerplate)
- Model selector is a card grid, NOT a dropdown
- No database for conversation history in MVP (lives in Zustand)
- Tailwind v4 with CSS-native config
- Claude CLI provider uses subprocess + stdout parsing
