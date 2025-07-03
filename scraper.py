import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import random
from datetime import datetime

# Rotate User-Agents to simulate different browser sessions
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
]

# Optional: List of rotating proxy IPs
PROXIES = [
    None,  # No proxy
    {"http": "http://123.456.789.001:8080", "https": "http://123.456.789.001:8080"},
    {"http": "http://123.456.789.002:8080", "https": "http://123.456.789.002:8080"},
    {"http": "http://123.456.789.003:8080", "https": "http://123.456.789.003:8080"}
    # Add more if needed
]

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
        batch = range(current, min(current + 15, end + 1))
        print(f"\n{timestamp()} 🚀 Starting new batch: {batch.start} to {batch.stop - 1}", flush=True)

        # Rotate User-Agent and Proxy
        headers = {
            "User-Agent": random.choice(USER_AGENTS)
        }
        proxy = random.choice(PROXIES)

        for i in batch:
            case_number = f"{prefix}{str(i).zfill(6)}"
            print(f"{timestamp()} Checking case: {case_number}", flush=True)
            url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

            try:
                req = requests.get(url, headers=headers, proxies=proxy, timeout=15)
                print(f"{timestamp()} Request status: {req.status_code} URL: {req.url}", flush=True)

                soup = BeautifulSoup(req.content, "html.parser")

                if soup.find("p", class_="emphasis") and "no cases found" in soup.find("p", class_="emphasis").text.lower():
                    print(f"{timestamp()} ❌ No case found message detected for {case_number}", flush=True)
                    continue

                charges_section = soup.find("div", id="tblDocket12")
                if not charges_section:
                    print(f"{timestamp()} No charges section found for {case_number}", flush=True)
                    snippet = soup.get_text(strip=True)[:300]
                    print(f"{timestamp()} 🔎 Page preview for {case_number}: {snippet}", flush=True)
                    continue

                rows = charges_section.find_all("div", class_="row g-0")
                print(f"{timestamp()} Found {len(rows)} rows for {case_number}", flush=True)

                total_charges = 0
                murder_charges = 0
                manslaughter_charges = 0

                for row in rows:
                    print(f"{timestamp()} Processing row for {case_number}", flush=True)
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
                            print(f"{timestamp()} {case_number} → Found {charge_type} charge: '{description}' with disposition: {disposition}", flush=True)
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description,
                                "Defendant": defendant_name,
                                "Disposition": disposition
                            })

                print(f"{timestamp()} {case_number} → Charges found: {total_charges}, Murder charges: {murder_charges}, Manslaughter charges: {manslaughter_charges}", flush=True)

            except requests.exceptions.RequestException as e:
                print(f"{timestamp()} ⚠️ Request error with {case_number}: {e}", flush=True)
            except Exception as e:
                print(f"{timestamp()} ⚠️ General error with {case_number}: {e}", flush=True)

        current += 15

        delay = random.uniform(60, 120)
        print(f"{timestamp()} ⏳ Sleeping for {int(delay)} seconds before next batch...\n", flush=True)
        time.sleep(delay)
