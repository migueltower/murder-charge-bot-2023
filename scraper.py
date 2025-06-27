import requests
from bs4 import BeautifulSoup
import csv
import time
import os

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = 2023
prefix = f"CR{year}-"
csv_file = "murder_charges.csv"

print(f"🔁 Running case range: {start} to {end}")

fieldnames = ["Case Number", "URL", "Charge"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for i in range(start, end + 1):
        case_number = f"{prefix}{str(i).zfill(6)}"
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            req = requests.get(url, timeout=15)
            soup = BeautifulSoup(req.content, "html.parser")
            
            charges_section = soup.find("div", id="tblDocket12")
            if not charges_section:
                continue

            rows = charges_section.find_all("div", class_="row g-0")
            total_charges = 0
            murder_charges = 0
            manslaughter_charges = 0

            for row in rows:
                divs = row.find_all("div")
                for i in range(len(divs)):
                    if "Description" in divs[i].get_text(strip=True):
                        description = divs[i + 1].get_text(strip=True)
                        total_charges +=1
                        if "MURDER" in description.upper():
                            murder_charges +=1
                            print(f"{case_number} → Found MURDER charge")
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description
                            })
                        if "MANSLAUGHTER" in description.upper():
                            manslaughter_charges +=1
                            print(f"{case_number} → Found MANSLAUGHTER charge")
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description
                            })

            print(f"{case_number} → Charges found: {total_charges}, Murder charges: {murder_charges}, Manslaughter charges: {manslaughter_charges}")

            time.sleep(1.5)

        except Exception as e:
            print(f"⚠️ Error with {case_number}: {e}")
