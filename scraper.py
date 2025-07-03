import os
import time
import requests
from bs4 import BeautifulSoup
import csv

# Read parameters from GitHub Action input
start = int(os.getenv("START", 0))
end = int(os.getenv("END", 100))
year = int(os.getenv("YEAR", 2024))
batch_size = 15

prefix = f"CR{year}-"

def scrape_batch(batch_case_numbers):
    results = []
    for case_number in batch_case_numbers:
        url = f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}'
        try:
            req = requests.get(url)
            soup = BeautifulSoup(req.content, "html.parser")
            table = soup.find("div", id="tblDocket12")
            first_charge = None

            if table:
                rows = table.find_all("div", class_='row g-0')
                for row in rows:
                    divs = row.find_all("div")
                    for i in range(len(divs)):
                        if "Description" in divs[i].get_text(strip=True):
                            description = divs[i + 1].get_text(strip=True)
                            if not first_charge:
                                first_charge = description
                            if any(word in description.upper() for word in ["MURDER", "MANSLAUGHTER", "NEGLIGENT HOMICIDE"]):
                                first_charge = description
                                break
                    else:
                        continue
                    break

            results.append({
                "Case Number": case_number,
                "URL": url,
                "First Charge": first_charge or "No charge found"
            })

        except Exception as e:
            print(f"Error with {url}: {e}")
            results.append({
                "Case Number": case_number,
                "URL": url,
                "First Charge": f"Error: {e}"
            })

    # Write to CSV
    first = batch_case_numbers[0].split('-')[-1]
    last = batch_case_numbers[-1].split('-')[-1]
    csv_filename = f"charges_{prefix}{first}-{last}.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Case Number", "URL", "First Charge"])
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved {csv_filename}")
    return csv_filename

# Create and process batches
all_case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
all_filenames = []

for i in range(0, len(all_case_numbers), batch_size):
    batch = all_case_numbers[i:i + batch_size]
    filename = scrape_batch(batch)
    all_filenames.append(filename)
    if i + batch_size < len(all_case_numbers):
        print("Pausing for 1 minute...")
        time.sleep(60)

# Save list of files for GitHub artifact step
with open("csv_manifest.txt", "w") as f:
    for name in all_filenames:
        f.write(name + "\n")
