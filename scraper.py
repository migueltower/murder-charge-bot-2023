import requests
from bs4 import BeautifulSoup
import csv
import time

# Setup
year = 2024
prefix = f"CR{year}-"
start = 160502
end = 160504

case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]

# Output file
csv_file = "murder_charges.csv"
fieldnames = ["Case Number", "URL", "Charge"]

with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for case_number, url in zip(case_numbers, urls):
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
                    break

            if not found_murder:
                print(f"{case_number} → no murder charge found")

            time.sleep(1.5)

        except Exception as e:
            print(f"Error with {case_number}: {e}")
