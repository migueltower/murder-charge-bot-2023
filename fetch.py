import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import random

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = int(os.getenv("YEAR", 2023))
prefix = f"CR{year}-"
csv_file = f"charges_CR{year}_{start}-{end}.csv"

print(f"🔁 Running case range: {start} to {end} for year {year}", flush=True)

fieldnames = ["Case Number", "URL", "Charge", "Defendant", "Disposition"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    current = start
    while current <= end:
        batch = range(current, min(current + 15, end + 1))
        print(f"\n🚀 Starting new batch: {batch.start} to {batch.stop - 1}", flush=True)

        for i in batch:
            case_number = f"{prefix}{str(i).zfill(6)}"
            print(f"Checking case: {case_number}", flush=True)
            url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

            try:
                req = requests.get(url, timeout=15)
                print(f"Request status: {req.status_code} URL: {req.url}", flush=True)

                soup = BeautifulSoup(req.content, "html.parser")

                if soup.find("p", class_="emphasis") and "no cases found" in soup.find("p", class_="emphasis").text.lower():
                    print(f"❌ No case found message detected for {case_number}", flush=True)
                    continue

                charges_section = soup.find("div", id="tblDocket12")
                if not charges_section:
                    print(f"No charges section found for {case_number}", flush=True)
                    snippet = soup.get_text(strip=True)[:300]
                    print(f"🔎 Page preview for {case_number}: {snippet}", flush=True)
                    continue

                rows = charges_section.find_all("div", class_="row g-0")
                print(f"Found {len(rows)} rows for {case_number}", flush=True)

                total_charges = 0
                murder_charges = 0
                manslaughter_charges = 0

                for row in rows:
                    print(f"Processing row for {case_number}", flush=True)
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
                            print(f"{case_number} → Found {charge_type} charge: '{description}' with disposition: {disposition}", flush=True)
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description,
                                "Defendant": defendant_name,
                                "Disposition": disposition
                            })

                print(f"{case_number} → Charges found: {total_charges}, Murder charges: {murder_charges}, Manslaughter charges: {manslaughter_charges}", flush=True)

                sleep_time = random.uniform(3, 30)
                time.sleep(sleep_time)

            except requests.exceptions.RequestException as e:
                print(f"⚠️ Request error with {case_number}: {e}", flush=True)
            except Exception as e:
                print(f"⚠️ General error with {case_number}: {e}", flush=True)

        current += 15
        print("⏳ Sleeping for 60 seconds before next batch...\n", flush=True)
        time.sleep(60)
