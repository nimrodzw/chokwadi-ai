cd chokwadi-ai
git init
git add .
git commit -m "Chokwadi AI v1.0"
git branch -M main
git remote add origin https://github.com/nimrodzw/chokwadi-ai.git
git push -u origin main
```

### Step 3: Railway Deploy (5 min)
1. Go to https://railway.app → sign up with GitHub
2. **New Project → Deploy from GitHub Repo** → select `chokwadi-ai`
3. Once it creates the project, go to **Variables** and add:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
AI_PROVIDER=auto
ADMIN_PHONE=whatsapp:+263771841532