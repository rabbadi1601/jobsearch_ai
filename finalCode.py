import asyncio
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from jobspy import scrape_jobs
from google import genai
from telegram import Bot
from apify_client import ApifyClient

# 1. Configuration
load_dotenv()
CONFIG = {
    "TELEGRAM_TOKEN": os.getenv('TELEGRAM_TOKEN'),
    "CHAT_ID": os.getenv('CHAT_ID'),
    "GEMINI_KEY": os.getenv('GEMINI_KEY'),
    "APIFY_TOKEN": os.getenv('APIFY_TOKEN'),
    "DB_FILE": "seen_jobs.csv",
    "MODEL_ID": "gemini-3.1-flash-lite-preview"
}

client = genai.Client(api_key=CONFIG["GEMINI_KEY"])
apify_client = ApifyClient(CONFIG["APIFY_TOKEN"])

# Seniority-focused search terms
TARGET_ROLES = ["QA Architect", "QA Manager", "Automation Architect", "Quality Engineering Manager"]
LOCATIONS = "(Hyderabad OR Bengaluru OR India)"


def load_seen_jobs():
    if os.path.exists(CONFIG["DB_FILE"]):
        try:
            return set(pd.read_csv(CONFIG["DB_FILE"])['url'].tolist())
        except:
            return set()
    return set()


def save_job(url, title):
    df = pd.DataFrame([{'url': url, 'title': title, 'date_found': datetime.now()}])
    df.to_csv(CONFIG["DB_FILE"], mode='a', index=False, header=not os.path.exists(CONFIG["DB_FILE"]))


async def ai_analyze_match(title, description):
    """Refined AI Prompt: Focuses on Seniority/Title rather than just snippets."""
    prompt = f"""
    Is this a Senior QA Leadership role (Manager or Architect)?
    TITLE: {title}
    SNIPPET: {str(description)[:800]}

    CRITERIA:
    1. If Title contains 'Manager', 'Architect', or 'Lead', Decision = YES.
    2. If Experience mentioned is 10-15+ years, Decision = YES.

    Output exactly: SCORE: [1-10], DECISION: [YES/NO]
    """
    try:
        await asyncio.sleep(4)  # Protect Free Tier Rate Limits
        response = client.models.generate_content(model=CONFIG["MODEL_ID"], contents=prompt)
        text = response.text.upper()
        is_match = "DECISION: YES" in text
        score = text.split("SCORE:")[1].split(",")[0].strip() if "SCORE:" in text else "N/A"
        return is_match, score
    except Exception as e:
        print(f"      ⚠️ AI Error: {e}")
        return False, "0"


async def get_naukri_via_google(roles):
    """The Surgical Extractor: Visible logs and clean data mapping."""
    results = []
    for role in roles:
        try:
            search_query = f'site:naukri.com/job-listings "{role}" {LOCATIONS}'
            print(f"\n🔎 Scanning Naukri for: {role}")

            run_input = {
                "queries": search_query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": 20,
                "timeRange": "d"  # Past 7 days
            }

            run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())

            for item in items:
                organic = item.get('organicResults', [])
                for res in organic:
                    raw_url = res.get('url', '')

                    # Log every link found to the console
                    print(f"     🔗 RAW DATA: {raw_url[:80]}")

                    if "/job-listings-" in raw_url:
                        clean_url = raw_url.split('?')[0]
                        results.append({
                            'title': res.get('title'),
                            'company': 'Naukri (Google Pivot)',
                            'job_url': clean_url,
                            'description': res.get('description', ''),
                            'site': 'naukri'
                        })
            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ ERROR in Naukri Loop: {e}")

    return pd.DataFrame(results)


async def main():
    print(f"\n--- 🕒 SCOUT START: {datetime.now().strftime('%H:%M:%S')} ---")
    seen_jobs = load_seen_jobs()
    all_found_jobs = []

    # 1. Indeed/LinkedIn
    print("\n🔵 STEP 1: Fetching Indeed/LinkedIn...")
    for role in TARGET_ROLES:
        try:
            df = scrape_jobs(site_name=["indeed", "linkedin"], search_term=role, location="Hyderabad",
                             results_wanted=10, hours_old=36, country_indeed='india')
            if not df.empty:
                all_found_jobs.append(df)
                print(f"   ✅ Collected leads for {role}")
        except:
            pass

    # 2. Naukri
    print("\n🟠 STEP 2: Fetching Naukri (Surgical Scan)...")
    df_naukri = await get_naukri_via_google(TARGET_ROLES)
    if not df_naukri.empty:
        all_found_jobs.append(df_naukri)

    # 3. Merging & Analysis
    if not all_found_jobs:
        print("\n📭 RESULT: No jobs found across all platforms.")
        return

    all_jobs = pd.concat(all_found_jobs, ignore_index=True)
    all_jobs['job_url'] = all_jobs['job_url'].str.split('?').str[0]
    all_jobs = all_jobs.drop_duplicates(subset=['job_url'])

    print(f"\n📊 TOTAL UNIQUE JOBS TO ANALYZE: {len(all_jobs)}")

    bot = Bot(token=CONFIG["TELEGRAM_TOKEN"])

    for _, job in all_jobs.iterrows():
        url = job['job_url']
        if url in seen_jobs:
            continue

        print(f"   🧪 AI Analyzing: {job['title'][:50]}...")
        is_match, score = await ai_analyze_match(job['title'], job['description'])

        if is_match:
            msg = (
                f"<b>🎯 Match Found ({score}/10)</b>\n\n"
                f"💼 <b>{job['title']}</b>\n"
                f"🏢 <b>Company:</b> {job.get('company', 'Naukri/Partner')}\n"
                f"📡 <b>Source:</b> {job['site']}\n\n"
                f"<a href='{url}'>👉 View & Apply Here</a>"
            )
            try:
                await bot.send_message(chat_id=CONFIG["CHAT_ID"], text=msg, parse_mode='HTML')
                save_job(url, job['title'])
                print(f"      ✅ ALERT SENT!")
            except Exception as e:
                print(f"      ❌ Telegram Error: {e}")
        else:
            print(f"      ❌ REJECTED (Score: {score})")

    print(f"\n--- ✅ SCOUT FINISHED: {datetime.now().strftime('%H:%M:%S')} ---")


if __name__ == "__main__":
    asyncio.run(main())