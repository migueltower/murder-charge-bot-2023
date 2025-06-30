import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import random

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = 2024
prefix = f"CR{year}-"
csv_file = "murder_charges.csv"

print(f"\U0001F501 Running case range: {start} to {end}")

fieldnames = ["Case Number", "URL", "Charge"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for i in range(start, end + 1):
        case_number = f"{prefix}{str(i).zfill(6)}"
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            req = requests.get(url, timeout=20)
            soup = BeautifulSoup(req.content, "html.parser")

            divs = soup.find_all("div")
            descriptions = []
            for i in range(len(divs) - 1):
                label = divs[i].get_text(strip=True).upper()
                if label == "DESCRIPTION":
                    charge = divs[i + 1].get_text(strip=True)
                    descriptions.append(charge)

            num_charges = len(descriptions)
            murder_charges = [c for c in descriptions if "MURDER" in c.upper()]

            print(f"{case_number} → Charges found: {num_charges}, Murder charges: {len(murder_charges)}")

            if murder_charges:
                writer.writerow({
                    "Case Number": case_number,
                    "URL": url,
                    "Charge": murder_charges[0]
                })

            # Random delay between 3-5 seconds
            sleep_time = random.uniform(3, 5)
            time.sleep(sleep_time)

        except Exception as e:
            print(f"⚠️ Error with {case_number}: {e}")
