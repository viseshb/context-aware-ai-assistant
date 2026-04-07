# Admin Setup Guide

Complete setup instructions for the Context-Aware AI Assistant.

---

## Step 1: Clone & Install

```bash
git clone https://github.com/viseshb/context-aware-ai-assistant-.git
cd context-aware-ai-assistant-

# Install dependencies
npm install                              # Root (concurrently)
cd frontend && npm install && cd ..      # Frontend
cd backend && pip install -r requirements.txt && cd ..  # Backend
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys. See `.env.example` for detailed instructions on where to get each key.

### Required for LLM (at least one):
```env
GOOGLE_API_KEY=your_key          # Free — https://aistudio.google.com/apikey
NVIDIA_API_KEY=your_key          # Free — https://build.nvidia.com/
OPENAI_API_KEY=your_key          # Paid — https://platform.openai.com/api-keys
ANTHROPIC_API_KEY=your_key       # Paid — https://console.anthropic.com/
CLAUDE_CLI_PATH=claude           # Free with Pro/Max — path to claude binary
```

### Data Sources (optional):
```env
GITHUB_TOKEN=ghp_xxx             # https://github.com/settings/tokens (classic, repo scope)
SLACK_BOT_TOKEN=xoxb-xxx         # https://api.slack.com/apps
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Instance Mode:
```env
# Solo mode (default) — just you, no signup page
INSTANCE_MODE=solo

# Team mode — others can join with a team code
INSTANCE_MODE=team
TEAM_CODE=YOUR-SECRET-CODE       # Team members need this to sign up
```

### Email (for team mode approvals + contact form):
```env
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password  # Gmail App Password (16 chars, no spaces)
ADMIN_EMAIL=your@email.com       # Where approval emails go
```

## Step 3: Create Admin Account

```bash
cd backend
python -m app.security.jwt_auth create-admin --username yourname --email you@email.com
```

You'll be prompted for a password. This is the only way to create an admin — there is no admin signup in the UI.

## Step 4: Start the App

```bash
# From project root
npm run dev
```

This starts:
- **[API]** Backend on http://localhost:8000
- **[WEB]** Frontend on http://localhost:3000

## Step 5: Log In

1. Open http://localhost:3000
2. Click **"For You"** (solo) → goes to login
3. Log in with the admin credentials you just created
4. You're in! Select a model and start chatting.

---

## Team Mode Setup

### As Admin:

1. Set in `.env`:
   ```env
   INSTANCE_MODE=team
   TEAM_CODE=MYTEAM-2026
   ```

2. Share the team code with your team members (securely — don't post it publicly).

3. When someone signs up with the team code:
   - You'll receive an approval email
   - Click the approve link → select their role and permissions
   - They'll see confetti and get redirected to chat

4. You can also approve users from the Admin Panel at `/admin` → Pending Users tab.

### As Team Member:

1. Open the landing page → click **"For Your Team"**
2. Enter: username, email, password, and the **Team Code** your admin gave you
3. Wait for approval (you'll see an animated waiting page)
4. Once approved, you'll see confetti and be redirected to login
5. Log in and start chatting

---

## Admin Panel

Access at `/admin` (admin only). Features:

- **Users tab** — list all users, change roles, view permissions
- **Pending Users** — approve/reject signups with role selection
- **Audit Log** — view all activity: logins, tool calls, security events
- **System** — connected data sources, LLM providers, tool counts

---

## Available Commands

| Command | What It Does |
|---------|-------------|
| `npm run dev` | Start both backend + frontend |
| `npm run dev:backend` | Backend only (port 8000) |
| `npm run dev:frontend` | Frontend only (port 3000) |
| `npm run build` | Production build |
| `npm run create-admin` | Create admin user |

---

## Roles & Permissions

| Permission | Admin | Member | Viewer |
|-----------|:-----:|:------:|:------:|
| Chat with LLMs | Yes | Yes | Yes |
| GitHub tools | All repos | Assigned repos | No |
| Slack tools | All channels | Assigned channels | No |
| Database tools | All tables | Assigned tables | No |
| Admin panel | Yes | No | No |
| Manage users | Yes | No | No |

---

## Troubleshooting

### "Solo mode — admin account is created via CLI"
You're in solo mode. Run:
```bash
cd backend && python -m app.security.jwt_auth create-admin --username admin --email admin@local
```

### "Invalid team code"
The team code in the signup form doesn't match `TEAM_CODE` in `.env`. Check with your admin.

### No models appearing
Add at least one LLM API key to `.env`. Free options: `GOOGLE_API_KEY` or `NVIDIA_API_KEY`.

### SMTP errors
Make sure you're using a Gmail **App Password** (not your regular password). Enable 2FA first at https://myaccount.google.com/security, then create an app password at https://myaccount.google.com/apppasswords.

### Database connection failed
Check your `DATABASE_URL` format. Special characters in passwords must be URL-encoded (e.g. `@` → `%40`).
