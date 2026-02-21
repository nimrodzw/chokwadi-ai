# 🇿🇼 Chokwadi AI

**Multimodal Misinformation Detection Toolkit for Zimbabwean Youth**

> *"Chokwadi"* means *"truth"* in Shona. *Zvokwadi Zvinobatsira — The Truth Helps.*

Chokwadi AI is a WhatsApp-based tool that helps Zimbabwean youth verify suspicious content they encounter online. It analyses text messages, voice notes, images, screenshots, and URLs — in **Shona**, **Ndebele**, and **English** — and returns credibility assessments with explanations.

## 🎯 Features

- **📝 Text Analysis** — Paste any suspicious WhatsApp forward, social media post, or news claim
- **🎤 Voice Note Analysis** — Send voice notes for automatic transcription and credibility assessment
- **🖼️ Image/Screenshot Analysis** — Forward screenshots of fake news, scam graphics, or doctored documents
- **🔗 Link Security Scanning** — Phishing detection, typosquatting checks, and scam pattern matching
- **🇿🇼 Zimbabwean Context Engine** — Trained on local scam patterns, institutions, and misinformation trends
- **🌍 Multilingual** — Responds in Shona, Ndebele, or English based on user input
- **⚡ Dual AI Provider** — Supports both Anthropic Claude and OpenAI GPT with automatic fallback

## 🏗️ Architecture

```
User (WhatsApp) → Twilio API → Flask/Gunicorn (Railway) → AI Analysis → WhatsApp Response
                                      │
                                      ├── Input
                                      ├── Local LLM — Text + Vision  
                                      ├── Whisper API (OpenAI) — Voice transcription
                                      └── Link Scanner — Cybersecurity module
```

## 🚀 Quick Start

See [SETUP.md](SETUP.md) for full deployment instructions.

## 📋 Challenge Track

Built for **Track 6: Youth Voice and Governance** of the [#ClicksToImpact](https://www.zitechno.org) National Youth Day Challenge 2026, addressing combating misinformation, responsible use of technology, and youth-led accountability.

## 📄 License

MIT License

## 👤 Author

**Nimrod Moyo** — Cybersecurity & AI Engineer
