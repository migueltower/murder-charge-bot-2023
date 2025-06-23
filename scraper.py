import requests
from bs4 import BeautifulSoup
import csv
import time
import os

# Read case range from environment variables
year = 2024
prefix = f"CR{year}-"
start = int(os.getenv("START", 0))
end = int(os.getenv("END", 19999))
csv_file = "murder_charges.csv"

print(f"🔁 Starting batch: {start} to {end}")

# Prepare output CSV
fieldnames = ["Case Number", "URL", "Charge"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    # Build and scrape each case URL
    for i in range(start, end + 1):
        case_number = f"{prefix}{str(i).zfill(6)}"
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"
        try:
            req = requests.get(url, timeout=15)
            soup = BeautifulSoup(req.content, "html.parser")

            charge_divs = soup.find_all("div", class_="col-6 col-md-3 col-lg-3 col-xl-3")
            found_murder = False

            for div in charge_divs:
                charge = div.get_text(strip=True)
                if "MURDER" in charge.upper():
                    writer.writerow({
                        "Case Number": case_number,
                        "URL": url,
                        "Charge": charge
                    })
                    print(f"{case_number} → MURDER charge found: {charge}")
                    found_murder = True
                    break  # Only need the first match

            if not found_murder:
                print(f"{case_number} → no murder charge found")

            time.sleep(1.5)

        except Exception as e:
            print(f"⚠️ Error with {case_number}: {e}")
