""import requests
from bs4 import BeautifulSoup
import csv
import time
import os
from datetime import datetime

def timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = int(os.getenv("YEAR", 2023))
prefix = f"CR{year}-"

fieldnames = ["Case Number", "URL", "Charge", "Defendant", "Disposition"]

current = start
last_successful = start

# Track progress for triggering next workflow
with open("progress.txt", "w") as prog:
    prog.write(str(current))

# Temporary file to be renamed later
temp_csv_file = f"charges_CR{year}_{start}-placeholder.csv"

with open(temp_csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    print(f"{timestamp()} 🔁 Running case range: {start} to {end} for year {year}", flush=True)

    while current <= end:
        case_number = f"{prefix}{str(current).zfill(6)}"

        print(f"{timestamp()} Checking case: {case_number}", flush=True)
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            req = requests.get(url, timeout=15)
            print(f"{timestamp()} Request status: {req.status_code} URL: {req.url}", flush=True)

            soup = BeautifulSoup(req.content, "html.parser")

            if "Server busy. Please try again later." in soup.get_text():
                print(f"{timestamp()} 🔄 Server busy message detected. Ending run.", flush=True)
                break

            last_successful = current
            with open("progress.txt", "w") as prog:
                prog.write(str(last_successful + 1))

            if soup.find("p", class_="emphasis") and "no cases found" in soup.find("p", class_="emphasis").text.lower():
                print(f"{timestamp()} ❌ No case found message detected for {case_number}", flush=True)
            else:
                charges_section = soup.find("div", id="tblDocket12")
                if not charges_section:
                    print(f"{timestamp()} No charges section found for {case_number}", flush=True)
                    snippet = soup.get_text(strip=True)[:300]
                    print(f"{timestamp()} 🔎 Page preview for {case_number}: {snippet}", flush=True)
                else:
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

        current += 1

final_csv_file = f"charges_CR{year}_{start}-{last_successful}.csv"
os.rename(temp_csv_file, final_csv_file)
