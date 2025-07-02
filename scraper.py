import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import random

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = 2023
prefix = f"CR{year}-"
csv_file = "murder_charges.csv"

print(f"🔁 Running case range: {start} to {end}", flush=True)

fieldnames = ["Case Number", "URL", "Charge", "Defendant", "Disposition"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for i in range(start, end + 1):
        case_number = f"{prefix}{str(i).zfill(6)}"
        print(f"Checking case: {case_number}", flush=True)
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            req = requests.get(url, timeout=15)
            print(f"Request status: {req.status_code} URL: {req.url}", flush=True)

            soup = BeautifulSoup(req.content, "html.parser")

            charges_section = soup.find("div", id="tblDocket12")
            if not charges_section:
                print(f"No charges section found for {case_number}", flush=True)
                continue

            rows = charges_section.find_all("div", class_="row g-0")
            print(f"Found {len(rows)} rows for {case_number}", flush=True)

            total_charges = 0
            murder_charges = 0
            manslaughter_charges = 0

            for row in rows:
                print(f"Processing row for {case_number}", flush=True)
                divs = row.find_all("div")
                defendant_name = ""
                found_disposition = False
                for i in range(len(divs)):
                    text = divs[i].get_text(strip=True)
                    if "Party Name" in text and i + 1 < len(divs):
                        defendant_name = divs[i + 1].get_text(strip=True)
                    if "Description" in text and i + 1 < len(divs):
                        description = divs[i + 1].get_text(strip=True)
                        total_charges += 1
                        if "MURDER" in description.upper() or "MANSLAUGHTER" in description.upper():
                            charge_type = "MURDER" if "MURDER" in description.upper() else "MANSLAUGHTER"
                            if charge_type == "MURDER":
                                murder_charges += 1
                            else:
                                manslaughter_charges += 1
                            disposition = ""
                            for j in range(i + 2, len(divs)):
                                next_text = divs[j].get_text(strip=True)
                                if "Disposition" in next_text and j + 1 < len(divs):
                                    disposition = divs[j + 1].get_text(strip=True)
                                    print(f"{case_number} → Found {charge_type} charge with disposition: {disposition}", flush=True)
                                    break
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description,
                                "Defendant": defendant_name,
                                "Disposition": disposition
                            })

            print(f"{case_number} → Charges found: {total_charges}, Murder charges: {murder_charges}, Manslaughter charges: {manslaughter_charges}", flush=True)

            sleep_time = random.uniform(4, 7)  # Increased delay
            time.sleep(sleep_time)

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error with {case_number}: {e}", flush=True)
        except Exception as e:
            print(f"⚠️ General error with {case_number}: {e}", flush=True)
