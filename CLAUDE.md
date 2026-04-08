# Context-Aware AI Assistant - Project Instructions

## Project Overview
A production-grade, open-source Context-Aware AI Assistant using MCP (Model Context Protocol) to integrate GitHub, Slack, and PostgreSQL. Users query code repositories, team discussions, and database metrics via natural language across 10 switchable LLM providers. Built with FastAPI (Python) backend and Next.js (React) frontend.

**This is a real portfolio project on the user's resume and open-sourced on GitHub. It must be professional, fully functional, and impressive.**

## Editing Preference
- Make minimal, surgical changes by default.
- Prefer patching the existing file or section instead of rewriting whole files.
- Only rewrite an entire file when a full replacement is genuinely necessary or explicitly requested.

## Tech Stack (DO NOT CHANGE)

### Backend
- **Python 3.12** with **FastAPI**
- **MCP SDK** (`mcp` package) for Model Context Protocol
- **Pydantic** for validation, **Pydantic Settings** for env config
- **httpx** for async HTTP (GitHub API, Slack API)
- **asyncpg** for PostgreSQL
- **matplotlib** for chart generation
- **slowapi** for rate limiting
- **sqlparse** for SQL read-only enforcement
- **bcrypt** + **python-jose** for auth
- **structlog** + **rich** for pretty colored logging
- **aiosmtplib** for email (approval notifications, contact form)

### Frontend
- **Next.js 16.2** (App Router) — Devtools MCP, context-aware diagnostics, React Compiler
- **React 19** + **TypeScript** (strict)
- **Tailwind CSS v4**
- **Zustand** for state management
- **Framer Motion** for animations
- **react-markdown + remark-gfm + react-syntax-highlighter** for rich rendering
- **Recharts** for inline charts
- **Lucide React** for icons (SVG, NEVER emojis)
- **canvas-confetti** for approval celebration
- **Plus Jakarta Sans** font

## Instance Modes

### Solo Mode (`INSTANCE_MODE=solo`)
- Admin created via CLI only — NO signup in UI
- Landing "For You" → Login page
- Single user, full access

### Team Mode (`INSTANCE_MODE=team`)
- Admin created via CLI
- Team members sign up with `TEAM_CODE` → pending → admin approves via email
- Admin assigns role (member/viewer) + permissions (repos/channels/tables)
- Approved users see confetti → redirect to chat

### Admin CLI
```bash
cd backend
python -m app.security.jwt_auth create-admin --username visesh --email visesh66@gmail.com
```

## LLM Models (10 Providers, NO Default)

User MUST select a model before chatting. Model selector is a card grid, NOT a dropdown.

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

## System Prompt

The chatbot system prompt lives in `backend/app/services/chat_service.py` in the `SYSTEM_PROMPT` constant. This controls how the AI assistant behaves, responds, and uses tools. Update this to change the assistant's personality or instructions.

## UI/UX Rules (CRITICAL)

### Design System
- **Background:** `#0F172A` | **Panels:** `#1E293B` | **CTA:** `#22C55E`
- **Text:** `#F8FAFC` | **Muted:** `#94A3B8` | **Font:** Plus Jakarta Sans
- **Glass cards:** `bg-slate-800/70 backdrop-blur-xl border border-white/[0.08]`

### Design Principles
- **NOT AI SLOP** — unique dark-mode design, not a ChatGPT clone
- User messages: right-aligned, green-tinted bg
- Assistant messages: left-aligned, panel bg
- Tool execution: collapsible cards with green progress
- Context badges: GitHub=gray, Slack=purple, DB=blue
- Transitions: 150-300ms, respect `prefers-reduced-motion`
- Icons: Lucide React SVG only, NEVER emojis
- All clickable elements: `cursor-pointer`

## Authentication & RBAC

### User Flow
- Landing (`/`) → "For You" (→ login) | "For Your Team" (→ signup with team code)
- Solo: admin logs in directly, no signup
- Team: signup → pending → admin approves → confetti → login → chat
- Header shows: "Hello, {username}" + colored role badge (admin=green, member=blue, viewer=gray)

### Roles
- **admin** — full access, user management, all tools
- **member** — assigned repos/channels/tables only
- **viewer** — chat only, no tool access

### JWT
- Secret auto-generated per server start (tokens expire on restart)
- Expiry: 30 minutes (`JWT_EXPIRY_MINUTES`)

## Security (NO COMPROMISE — 8 Layers)

1. **Authentication** — JWT + bcrypt, 30-min expiry
2. **RBAC** — role-based tool filtering, checked BEFORE every tool call
3. **Rate Limiting** — 30 req/min REST, brute force protection
4. **Input Validation** — Pydantic schemas, max 10K chars, password strength
5. **Allowlists** — per-user repos/channels/tables
6. **Read-Only SQL** — sqlparse blocks mutations, READ ONLY transactions
7. **PII Filtering** — auto-redact emails, phones, SSNs, credit cards, API keys
8. **Audit Logging** — every action logged with user_id, tool, args, timestamp

## Architecture

### Backend
```
backend/app/
├── main.py              # FastAPI app, lifespan, CORS, rate limiting
├── config.py            # Pydantic Settings (.env loading)
├── dependencies.py      # Singletons: user_service, llm_registry, mcp_manager
├── api/
│   ├── auth.py          # signup (mode-aware), login (status-aware), /me
│   ├── chat.py          # WebSocket streaming + REST fallback
│   ├── models.py        # GET /api/models (auth-protected)
│   ├── admin.py         # User mgmt, approval endpoints, audit logs
│   ├── contact.py       # Email contact form
│   ├── context.py       # Data source status + RBAC info
│   ├── setup.py         # Instance mode info (public)
│   └── approval_status.py  # SSE for pending users
├── llm/
│   ├── base.py          # LLMProvider ABC, ChatEvent, Message
│   ├── registry.py      # Register/list/get providers
│   ├── tool_adapter.py  # MCP tools → LLM format + RBAC filtering
│   └── providers/
│       ├── _openai_compat.py  # Shared helpers for OpenAI-format APIs
│       ├── gemini.py          # 4 Google models
│       ├── nvidia.py          # 3 NVIDIA NIM models
│       ├── claude_api.py      # Anthropic SDK
│       ├── claude_cli.py      # CLI subprocess (cmd.exe /c claude -p)
│       └── openai_provider.py # GPT-4.1-mini
├── mcp_layer/
│   ├── manager.py       # Tool registration, execution routing
│   └── servers/
│       ├── github_server.py   # 7 tools (live GitHub API)
│       ├── slack_server.py    # 5 tools (live Slack API)
│       └── postgres_server.py # 4 tools (live DB queries)
├── security/
│   ├── jwt_auth.py      # JWT create/decode, bcrypt, CLI create-admin
│   ├── rbac.py          # Role checks, tool filtering, allowlist matching
│   ├── pii_filter.py    # Regex PII detection + redaction
│   ├── read_only.py     # SQL mutation blocking
│   ├── rate_limiter.py  # slowapi middleware
│   └── audit_log.py     # SQLite audit trail
├── services/
│   ├── chat_service.py  # Orchestrator: LLM + MCP tools + security
│   ├── user_service.py  # SQLite user CRUD + status + RBAC
│   └── email_service.py # Approval + notification emails
├── schemas/             # Pydantic models (auth, chat, settings)
└── utils/
    ├── logging.py       # Rich colored structured logging
    └── errors.py        # AppError hierarchy + unhandled exception handler
```

### Frontend
```
frontend/src/
├── app/
│   ├── page.tsx                          # Landing page
│   ├── (auth)/login/page.tsx             # Login (solo: primary entry)
│   ├── (auth)/signup/page.tsx            # Signup (team: with team code)
│   ├── (auth)/pending/page.tsx           # Waiting for approval + confetti
│   ├── (protected)/chat/page.tsx         # Chat with data source status bar
│   ├── (protected)/admin/page.tsx        # Admin panel (users, audit, system)
│   └── (protected)/admin/approve/page.tsx # Approval form (from email link)
├── components/
│   ├── landing/    # Navbar, Hero, Features, HowItWorks, Security, CTA, Footer, Contact
│   ├── auth/       # LoginForm, SignupForm, PendingApproval
│   ├── chat/       # ChatArea, MessageBubble, InputBar, StreamingIndicator, WelcomeScreen
│   ├── model/      # ModelSelector (card grid), ModelBadge
│   ├── rich/       # MarkdownRenderer, CodeBlock (syntax highlight + copy)
│   ├── context/    # ContextBadge (GitHub/Slack/DB pills)
│   ├── tools/      # ToolExecutionCard (collapsible)
│   ├── admin/      # AdminPanel, ApprovalForm
│   └── layout/     # Header ("Hello, username" + role badge)
├── stores/         # authStore (JWT + status + pending), chatStore (messages + streaming)
├── services/       # api.ts (fetch wrapper), websocket.ts (reconnecting WS)
└── config/         # models.ts (10 model metadata)
```

## Landing Page
- Navbar: "For You" | "For Your Team" (NOT "Login" / "Sign Up")
- Hero: animated chat preview, "For You" + "For Your Team" CTA buttons
- Features: bento grid (GitHub, Slack, PostgreSQL)
- HowItWorks: 3-step flow
- SecurityBadges: 8 security layers
- CTAFooter: "For You" + "For Your Team" buttons
- Footer: "Created by Visesh Bentula" + Contact Us modal
- All pages have "← Back to home" links

## Development

```bash
# Start both backend + frontend
npm run dev

# Backend only
npm run dev:backend

# Frontend only
npm run dev:frontend

# Create admin
cd backend && python -m app.security.jwt_auth create-admin --username admin --email admin@local

# Build
npm run build
```

## Key Decisions (DO NOT OVERRIDE)
- WebSocket for chat streaming, REST for metadata
- MCP tools call live APIs (GitHub, Slack) — NOT stored data
- PostgreSQL tools query user's existing DB — NOT a separate store
- Zustand over Redux (lightweight)
- Model selector is a card grid, NOT a dropdown
- No conversation persistence in MVP (lives in Zustand)
- Claude CLI: `cmd.exe /c claude -p --output-format json --max-turns 1`
- Pretty logs via structlog + rich (colored, structured)
- All errors return `{ error: "CODE", message: "..." }` with proper HTTP status
- Unhandled exceptions caught globally with full traceback logging
