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

ars_charge_map = {
    "13-1102": "Negligent Homicide",
    "13-1103": "Manslaughter",
    "13-1104": "Second-Degree Murder",
    "13-1105": "First-Degree Murder",
}

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
            qualifying_charges = 0

            for row in rows:
                divs = row.find_all("div")
                defendant_name = ""
                ars_code = ""
                disposition = ""
                for i in range(len(divs)):
                    text = divs[i].get_text(strip=True)

                    if "Party Name" in text and i + 1 < len(divs):
                        defendant_name = divs[i + 1].get_text(strip=True)

                    if "ARSCode" in text and i + 1 < len(divs):
                        ars_code_full = divs[i + 1].get_text(strip=True)
                        for ars_prefix, charge_name in ars_charge_map.items():
                            if ars_prefix in ars_code_full:
                                total_charges += 1
                                qualifying_charges += 1

                                # Find disposition if available
                                for j in range(i + 2, len(divs)):
                                    next_text = divs[j].get_text(strip=True)
                                    if "Disposition" in next_text and j + 1 < len(divs):
                                        disposition = divs[j + 1].get_text(strip=True)
                                        break

                                print(f"{case_number} → Found {charge_name} (ARS {ars_prefix}) with disposition: {disposition}", flush=True)

                                writer.writerow({
                                    "Case Number": case_number,
                                    "URL": url,
                                    "Charge": charge_name,
                                    "Defendant": defendant_name,
                                    "Disposition": disposition
                                })
                                break  # break out of ARSCode loop once one match is found

            print(f"{case_number} → Charges found: {total_charges}, Homicide-related charges: {qualifying_charges}", flush=True)

            time.sleep(random.uniform(4, 7))  # Respectful scraping delay

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error with {case_number}: {e}", flush=True)
        except Exception as e:
            print(f"⚠️ General error with {case_number}: {e}", flush=True)
