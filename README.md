# 📱 Phone Deal Alert Bot

**Real-time Telegram bot** that tracks Amazon.in and Flipkart for mobile phone deals and price drops. Get instant alerts when phones go on sale!

---

## 🎯 Features

- **Automatic Scanning** — Checks Amazon & Flipkart every 30 minutes
- **Smart Alerts** — Notifies when phones hit your discount threshold
- **Price Tracking** — Tracks price drops from previous scans
- **Customizable Thresholds** — Set your own discount % and max budget
- **24/7 Monitoring** — Runs on cloud (Replit, Railway, etc.)

---

## 🚀 Quick Start

### **Prerequisites**
- **Python 3.10+**
- **Telegram Bot Token** (from @BotFather)
- **ScraperAPI Key** (free tier: 1000 requests/month)

### **Installation**

```bash
git clone https://github.com/yourusername/Price-drop-alert-bot.git
cd Price-drop-alert-bot
pip install -r requirements.txt
```

### **Setup**

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Add your credentials to `.env`:


---

## 🌍 Cloud Deployment

### **Option 1: Replit (Recommended)**
1. Fork this repo on GitHub
2. Go to [replit.com](https://replit.com)
3. Import from GitHub
4. Add secrets: `BOT_TOKEN`, `SCRAPER_KEY`
5. Click **Run**


## 📊 How It Works

1. **Scanning** — Bot scans Amazon & Flipkart search results
2. **Parsing** — Extracts phone names, prices, MRP
3. **Comparison** — Checks against your thresholds
4. **Alerting** — Sends Telegram message if deal qualifies


## ⚠️ Limitations

- **Scraping** — Amazon/Flipkart may block requests
- **MRP Accuracy** — Some phones show inflated MRP
- **Real-time** — 30-minute scan intervals (customizable)

---

## 🛠️ Tech Stack

- **Language:** Python 3.13
- **Bot Framework:** python-telegram-bot
- **Scraping:** BeautifulSoup4 + ScraperAPI
- **Database:** SQLite
- **Hosting:** Replit


---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file.

---

## 💡 Future Ideas

- [ ] SMS alerts support
- [ ] Email notifications
- [ ] Discord webhook integration
- [ ] Web dashboard
- [ ] Specific phone tracking
- [ ] Price history graphs

---

## ⚡ Troubleshooting

**No alerts coming?**
- Thresholds too high (try `/discount 30`)
- Check Telegram connection: `/start`
- Run manual scan: `/scan`

**Bot crashed?**
- Check logs on hosting platform
- Verify `BOT_TOKEN` & `SCRAPER_KEY` are correct
- Restart the bot

---

## 📧 Contact

- EMAIL: kumar.saurav.div@gmaail.com


---

**Made with ❤️ for phone deal hunters** 📱🔥
