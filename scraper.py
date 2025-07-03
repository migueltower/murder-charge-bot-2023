import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import random
from datetime import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
]

PROXIES = [
    {"http": "http://123.456.789.001:8080", "https": "http://123.456.789.001:8080"},
    {"http": "http://123.456.789.002:8080", "https": "http://123.456.789.002:8080"},
    {"http": "http://123.456.789.003:8080", "https": "http://123.456.789.003:8080"}
]

PROXY_ROTATION_LIMIT = 15

def timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = int(os.getenv("YEAR", 2023))
prefix = f"CR{year}-"
csv_file = f"charges_CR{year}_{start}-{end}.csv"

print(f"{timestamp()} 🔁 Running case range: {start} to {end} for year {year}", flush=True)

fieldnames = ["Case Number", "URL", "Charge", "Defendant", "Disposition"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    current = start

    while current <= end:
        case_number = f"{prefix}{str(current).zfill(6)}"
        retrying = True
        use_proxies = False
        proxy_cycle_count = 0

        while retrying:
            proxies_to_try = [None] if not use_proxies else PROXIES * ((PROXY_ROTATION_LIMIT // len(PROXIES)) + 1)

            for proxy in proxies_to_try[:PROXY_ROTATION_LIMIT if use_proxies else 1]:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                proxy_display = proxy['http'] if proxy else "No proxy"

                print(f"{timestamp()} [Proxy: {proxy_display}] Checking case: {case_number}", flush=True)
                url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

                try:
                    req = requests.get(url, headers=headers, proxies=proxy, timeout=15)
                    print(f"{timestamp()} [Proxy: {proxy_display}] Request status: {req.status_code} URL: {req.url}", flush=True)
                    soup = BeautifulSoup(req.content, "html.parser")

                    if "Server busy. Please try again later." in soup.get_text():
                        print(f"{timestamp()} [Proxy: {proxy_display}] 🔄 Server busy message detected.", flush=True)
                        use_proxies = True
                        delay = random.uniform(60, 120)
                        print(f"{timestamp()} [Proxy: {proxy_display}] ⏳ Sleeping for {int(delay)}s before retrying...", flush=True)
                        time.sleep(delay)
                        break

                    retrying = False
                    use_proxies = False

                    if soup.find("p", class_="emphasis") and "no cases found" in soup.find("p", class_="emphasis").text.lower():
                        print(f"{timestamp()} [Proxy: {proxy_display}] ❌ No case found message detected for {case_number}", flush=True)
                    else:
                        charges_section = soup.find("div", id="tblDocket12")
                        if not charges_section:
                            print(f"{timestamp()} [Proxy: {proxy_display}] No charges section found for {case_number}", flush=True)
                            snippet = soup.get_text(strip=True)[:300]
                            print(f"{timestamp()} [Proxy: {proxy_display}] 🔎 Page preview for {case_number}: {snippet}", flush=True)
                        else:
                            rows = charges_section.find_all("div", class_="row g-0")
                            print(f"{timestamp()} [Proxy: {proxy_display}] Found {len(rows)} rows for {case_number}", flush=True)

                            total_charges = 0
                            murder_charges = 0
                            manslaughter_charges = 0

                            for row in rows:
                                print(f"{timestamp()} [Proxy: {proxy_display}] Processing row for {case_number}", flush=True)
                                divs = row.find_all("div")
                                fields = [div.get_text(strip=True) for div in divs]

                                description = ""
                                disposition = ""
                                defendant_name = ""

                                for idx, text in enumerate(fields):
                                    if "Party Name" in text and idx + 1 < len(fields):
                                        defendant_name = fields[idx + 1]
                                    if "Description" in text and idx + 1 < len(fields):
                                        description = fields[idx + 1]
                                    if "Disposition" in text and idx + 1 < len(fields):
                                        disposition = fields[idx + 1]

                                if description:
                                    total_charges += 1
                                    if "MURDER" in description.upper() or "MANSLAUGHTER" in description.upper():
                                        charge_type = "MURDER" if "MURDER" in description.upper() else "MANSLAUGHTER"
                                        if charge_type == "MURDER":
                                            murder_charges += 1
                                        else:
                                            manslaughter_charges += 1
                                        print(f"{timestamp()} [Proxy: {proxy_display}] {case_number} → Found {charge_type} charge: '{description}' with disposition: {disposition}", flush=True)
                                        writer.writerow({
                                            "Case Number": case_number,
                                            "URL": url,
                                            "Charge": description,
                                            "Defendant": defendant_name,
                                            "Disposition": disposition
                                        })

                            print(f"{timestamp()} [Proxy: {proxy_display}] {case_number} → Charges found: {total_charges}, Murder charges: {murder_charges}, Manslaughter charges: {manslaughter_charges}", flush=True)

                except requests.exceptions.RequestException as e:
                    print(f"{timestamp()} [Proxy: {proxy_display}] ⚠️ Request error with {case_number}: {e}", flush=True)
                except Exception as e:
                    print(f"{timestamp()} [Proxy: {proxy_display}] ⚠️ General error with {case_number}: {e}", flush=True)

        current += 1
