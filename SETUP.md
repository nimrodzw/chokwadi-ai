# 🇿🇼 Chokwadi AI - Setup & Deployment Guide

## Architecture

```
User (WhatsApp) → Twilio → Railway (Flask/Gunicorn) → AI Provider → WhatsApp response
                                                    ↗ Claude API (Anthropic)
                                                    ↘ GPT-4o API (OpenAI)
```

---

## Step 1: Get Your API Keys (15 minutes)

### 1a. Twilio (WhatsApp gateway - FREE sandbox)
1. Sign up at https://www.twilio.com/try-twilio
2. Go to: **Messaging → Try it out → Send a WhatsApp message**
3. Note the sandbox number and join code (e.g., "join helpful-cat")
4. From YOUR WhatsApp, send that join message to the sandbox number
5. Copy **Account SID** and **Auth Token** from the dashboard

### 1b. Anthropic API Key
1. Go to https://console.anthropic.com/settings/keys
2. Create a new key, copy it

### 1c. OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new key, copy it
3. (Needed for Whisper voice transcription even if using Claude for analysis)

---

## Step 2: Deploy to Railway (10 minutes)

### 2a. Push code to GitHub
```bash
cd chokwadi-ai
git init
git add .
git commit -m "Initial commit - Chokwadi AI"
git remote add origin https://github.com/YOUR_USERNAME/chokwadi-ai.git
git push -u origin main
```

### 2b. Deploy on Railway
1. Sign up at https://railway.app (free tier: $5 credit/month, more than enough)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `chokwadi-ai` repository
4. Railway will auto-detect it as a Python app

### 2c. Set Environment Variables on Railway
Go to your project → **Variables** tab → Add these:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `OPENAI_API_KEY` | `sk-...` |
| `TWILIO_ACCOUNT_SID` | `AC...` |
| `TWILIO_AUTH_TOKEN` | `your-token` |
| `AI_PROVIDER` | `auto` |
| `ADMIN_PHONE` | `whatsapp:+263771841532` |

Railway automatically sets `PORT` — you don't need to add it.

### 2d. Get Your Railway URL
After deploy, Railway gives you a URL like:
```
https://chokwadi-ai-production.up.railway.app
```

You can also set a custom domain in Railway settings.

---

## Step 3: Connect Twilio to Railway (2 minutes)

1. Go to Twilio Console → **Messaging → Settings → WhatsApp Sandbox Settings**
2. Set **"When a message comes in"** to:
   ```
   https://YOUR-APP.up.railway.app/webhook
   ```
   Method: **POST**
3. Click **Save**

---

## Step 4: Test It!

Send a message from your WhatsApp to the Twilio sandbox number:

| Test | Send this | Expected |
|---|---|---|
| Welcome | `hi` | Welcome message in Shona/English |
| Text | Any suspicious news forward | Credibility analysis |
| Voice | Record a voice note in Shona | Transcription + analysis |
| Image | Screenshot of fake news | Image analysis |
| Link | `https://ecocash-free.xyz` | Security scan + analysis |

---

## Live Provider Switching (Admin Commands)

From your registered admin number (+263771841532), send these commands:

| Command | Effect |
|---|---|
| `!status` | Show current provider and available providers |
| `!claude` | Switch to Anthropic Claude |
| `!gpt` | Switch to OpenAI GPT |
| `!auto` | Switch to auto mode (Claude → GPT fallback) |

This lets you switch AI providers LIVE without redeploying — useful during the demo
if one provider is slow or you want to show both.

---

## AI Provider Modes

| Mode | Behaviour |
|---|---|
| `auto` (recommended) | Uses Claude first. If Claude fails, automatically falls back to GPT |
| `anthropic` | Claude only. Fails with error if Claude API is down |
| `openai` | GPT only. Fails with error if OpenAI API is down |

**Note:** Voice note transcription ALWAYS uses OpenAI Whisper regardless of provider
setting, since Anthropic doesn't have a speech-to-text API.

---

## Demo Day Checklist (Saturday, 21 Feb 2026)

### Before the event:
- [ ] Verify Railway deployment is live (visit your URL in browser)
- [ ] Send test message to WhatsApp bot — confirm response
- [ ] Test all 4 input types (text, voice, image, link)
- [ ] Test `!status` and `!claude` / `!gpt` switching
- [ ] Prepare demo content (fake scam messages, voice note, screenshot)
- [ ] Charge phone + laptop
- [ ] Record a backup screen recording of the bot working (safety net)

### Demo script (2-3 minutes):
1. **Show phone screen** — open WhatsApp chat with Chokwadi AI
2. **Forward a fake EcoCash scam message** (text in Shona) → Show analysis
3. **Send a voice note** about a fake health claim → Show transcription + analysis
4. **Send a screenshot** of a fake government circular → Show image analysis
5. **Paste a phishing link** → Show security scan

### If something goes wrong:
- Switch provider: send `!gpt` or `!claude` from WhatsApp
- If both AI providers are down: show the backup recording
- If Twilio is down: show the backup recording
- If WiFi is down: use phone hotspot

---

## Cost Estimates

| Service | Free tier | Estimated demo cost |
|---|---|---|
| Railway | $5/month credit | $0 (well within free tier) |
| Twilio Sandbox | Free for testing | $0 |
| Claude API | Pay per use | ~$0.05 for demo |
| OpenAI API | Pay per use | ~$0.05 for demo |
| OpenAI Whisper | $0.006/minute | ~$0.01 per voice note |
| **Total** | | **< $1 for entire demo** |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Bot not responding | Check Railway deployment logs for errors |
| "Error processing" | Check API keys in Railway Variables |
| Voice notes fail | Verify OPENAI_API_KEY has credits |
| Image analysis fails | Check active provider has vision support |
| Railway deploy fails | Check build logs; ensure requirements.txt is correct |
| Twilio sandbox expired | Re-send the "join" message from WhatsApp |
| Slow responses | Voice notes take longest (~5-8s); text is fastest (~2-3s) |
| Hit rate limit | Switch provider with `!gpt` or `!claude` |
