Markdown
# 🎯 QA Scout: AI-Powered Job Search Agent

A sophisticated automation engine designed to bypass anti-bot measures and scout for **Senior QA Leadership** roles (Architects & Managers) using Google Search pivoting and Gemini AI.

## 🚀 Features
* **Anti-Bot Bypass:** Uses a "Google Search Pivot" via Apify to scrape Naukri without being blocked by Cloudflare/DataDome.
* **Multi-Source:** Aggregates jobs from **LinkedIn, Indeed, and Naukri**.
* **AI Filtering:** Uses **Gemini 1.5 Flash** to analyze job snippets for seniority (14+ years) and leadership requirements.
* **Automated Alerts:** Delivers high-scoring matches directly to **Telegram** with one-click apply links.
* **Persistence:** Tracks seen jobs in `seen_jobs.csv` to ensure zero spam.
* **Serverless Execution:** Runs automatically every morning at **6:00 AM IST** via GitHub Actions.

## 🏗️ Technical Architecture
* **Language:** Python 3.10+
* **Orchestration:** GitHub Actions (Cron schedule)
* **AI Engine:** Google Gemini (Generative AI SDK)
* **Scraping:** JobSpy & Apify Google Search Scraper
* **Database:** CSV-based persistence (Git-synced)

## ⚙️ Setup & Installation

### Local Development
1. Clone the repository: `git clone <your-repo-url>`
2. Create a virtual environment: `python -m venv venv`
3. Install dependencies: 
   ```bash
   pip install pandas google-genai python-telegram-bot apify-client python-dotenv python-jobspy
Create a .env file with your keys:

Code snippet
TELEGRAM_TOKEN=your_token
CHAT_ID=your_id
GEMINI_KEY=your_key
APIFY_TOKEN=your_token
GitHub Actions Configuration
To run this on a schedule, add the keys above to Settings > Secrets and variables > Actions in your GitHub repository.

📊 Deployment
The system is deployed via GitHub Actions using the .github/workflows/daily_scout.yml configuration. It uses a Node.js 24 environment to ensure future-proof execution.

📝 License
Private Project - Internal Use Only