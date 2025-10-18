import requests
from bs4 import BeautifulSoup
import csv
import os
import random
import time
from datetime import datetime, timedelta

def timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = int(os.getenv("YEAR", 2023))
prefix = f"CR{year}-"

fieldnames = ["Case Number", "URL", "Charge", "Defendant", "Disposition"]

current = start
last_successful = start
request_limit = 100
requests_made = 0
delay_seconds = 21600 / request_limit  # ~864 seconds = 14m24s per request

# Set a deadline to stop just before GitHub's 6-hour job limit
job_start_time = datetime.now()
job_deadline = job_start_time + timedelta(hours=5, minutes=55)

with open("progress.txt", "w") as prog:
    prog.write(str(current))

temp_csv_file = f"charges_CR{year}_{start}-placeholder.csv"

header_pool = [
    {
        "User-Agent": "...",
        "Accept": "...",
        # Add additional headers if desired
    },
]

with open(temp_csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    print(f"{timestamp()} 🔁 Running case range: {start} to {end} for year {year}", flush=True)

    session = requests.Session()

    while current <= end and requests_made < request_limit and datetime.now() < job_deadline:
        case_number = f"{prefix}{str(current).zfill(6)}"
        print(f"{timestamp()} Checking case: {case_number}", flush=True)
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            headers = random.choice(header_pool)
            req = session.get(url, headers=headers, timeout=15)
            print(f"{timestamp()} Request status: {req.status_code} URL: {req.url}", flush=True)

            if not req.content.strip():
                print(f"{timestamp()} ⚠️ Empty response body for {case_number}.", flush=True)
                break

            soup = BeautifulSoup(req.content, "html.parser")
            page_text = soup.get_text(strip=True)

            if "Server busy. Please try again later." in page_text:
                print(f"{timestamp()} 🔄 Server busy message detected. Ending run.", flush=True)
                break
            elif "Please try again later" in page_text or "temporarily unavailable" in page_text:
                print(f"{timestamp()} ⚠️ Similar server message detected. Snippet:\n{page_text[:300]}", flush=True)
                break

            last_successful = current
            with open("progress.txt", "w") as prog:
                prog.write(str(last_successful + 1))

            if soup.find("p", class_="emphasis") and "no cases found" in soup.find("p", class_="emphasis").text.lower():
                print(f"{timestamp()} ❌ No case found for {case_number}", flush=True)
            else:
                charges_section = soup.find("div", id="tblDocket12")
                if not charges_section:
                    print(f"{timestamp()} No charges section found for {case_number}", flush=True)
                else:
                    rows = charges_section.find_all("div", class_="row g-0")
                    print(f"{timestamp()} Found {len(rows)} rows", flush=True)

                    for row in rows:
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
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description,
                                "Defendant": defendant_name,
                                "Disposition": disposition
                            })

        except requests.exceptions.RequestException as e:
            print(f"{timestamp()} ⚠️ Request error with {case_number}: {e}", flush=True)
        except Exception as e:
            print(f"{timestamp()} ⚠️ General error with {case_number}: {e}", flush=True)

        current += 1
        requests_made += 1

        # ✅ SAFETY CHECK before sleeping — prevent GitHub timeout
        time_remaining = (job_deadline - datetime.now()).total_seconds()
        if time_remaining < delay_seconds + 60:  # Leave 60s buffer
            print(f"{timestamp()} ⏰ Time limit approaching — exiting safely after {requests_made} requests.", flush=True)
            break

        print(f"{timestamp()} 💤 Sleeping for {int(delay_seconds)}s", flush=True)
        time.sleep(delay_seconds)

# Finalize file
final_csv_file = f"charges_CR{year}_{start}-{last_successful}.csv"
os.rename(temp_csv_file, final_csv_file)
print(f"{timestamp()} ✅ CSV file saved: {final_csv_file}", flush=True)

print(f"{timestamp()} 🕒 Job duration: {(datetime.now() - job_start_time)}", flush=True)
