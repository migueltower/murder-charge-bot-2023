import requests
from bs4 import BeautifulSoup
import csv
import os
import random
from datetime import datetime

# Returns a formatted timestamp string for consistent logging.
def timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

# Read environment variables or fall back to defaults for scraping range and year.
start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = int(os.getenv("YEAR", 2023))
prefix = f"CR{year}-"  # Prefix used to construct the case number string.

# Field names for the CSV output
fieldnames = ["Case Number", "URL", "Charge", "Defendant", "Disposition"]

# Track current case number and last successful scrape
current = start
last_successful = start
found_relevant_charge = False  # Flag to determine whether to save the file

# Save initial progress to file
with open("progress.txt", "w") as prog:
    prog.write(str(current))

# Define placeholder filename for the CSV
temp_csv_file = f"charges_CR{year}_{start}-placeholder.csv"

# List of different browser headers to randomize requests and reduce detection as a bot
header_pool = [
    {
        "User-Agent": "...",
        "Accept": "...",
        ...
    },
    ...
]

# Begin writing output to CSV
with open(temp_csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    print(f"{timestamp()} 🔁 Running case range: {start} to {end} for year {year}", flush=True)

    session = requests.Session()  # Create a persistent HTTP session for efficiency

    while current <= end:
        case_number = f"{prefix}{str(current).zfill(6)}"
        print(f"{timestamp()} Checking case: {case_number}", flush=True)
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            headers = random.choice(header_pool)  # Randomize headers for each request
            req = session.get(url, headers=headers, timeout=15)
            print(f"{timestamp()} Request status: {req.status_code} URL: {req.url}", flush=True)

            # Check for empty response body
            if not req.content.strip():
                print(f"{timestamp()} ⚠️ Empty response body for {case_number}. Status: {req.status_code}", flush=True)
                print(f"{timestamp()} 🔎 Response headers: {dict(req.headers)}", flush=True)
                break

            soup = BeautifulSoup(req.content, "html.parser")
            page_text = soup.get_text(strip=True)

            # Detect server busy messages and halt if encountered
            if "Server busy. Please try again later." in page_text:
                print(f"{timestamp()} 🔄 Server busy message detected. Ending run.", flush=True)
                break
            elif "Please try again later" in page_text or "temporarily unavailable" in page_text:
                print(f"{timestamp()} ⚠️ Similar server message detected. Snippet:\n{page_text[:300]}", flush=True)
                break
            else:
                print(f"{timestamp()} ℹ️ Page snippet for {case_number}: {page_text[:300]}", flush=True)

            last_successful = current  # Update last successfully scraped case
            with open("progress.txt", "w") as prog:
                prog.write(str(last_successful + 1))

            # Skip if no case was found
            if soup.find("p", class_="emphasis") and "no cases found" in soup.find("p", class_="emphasis").text.lower():
                print(f"{timestamp()} ❌ No case found message detected for {case_number}", flush=True)
            else:
                charges_section = soup.find("div", id="tblDocket12")
                if not charges_section:
                    print(f"{timestamp()} No charges section found for {case_number}", flush=True)
                else:
                    rows = charges_section.find_all("div", class_="row g-0")
                    print(f"{timestamp()} Found {len(rows)} rows for {case_number}", flush=True)

                    for row in rows:
                        print(f"{timestamp()} Processing row for {case_number}", flush=True)
                        divs = row.find_all("div")
                        fields = [div.get_text(strip=True) for div in divs]

                        # Extract fields from charge row
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

                        # Check for murder or manslaughter and write if found
                        if description and ("MURDER" in description.upper() or "MANSLAUGHTER" in description.upper()):
                            charge_type = "MURDER" if "MURDER" in description.upper() else "MANSLAUGHTER"
                            print(f"{timestamp()} {case_number} → Found {charge_type} charge: '{description}' with disposition: {disposition}", flush=True)
                            writer.writerow({
                                "Case Number": case_number,
                                "URL": url,
                                "Charge": description,
                                "Defendant": defendant_name,
                                "Disposition": disposition
                            })
                            found_relevant_charge = True  # Mark that we found at least one match

        except requests.exceptions.RequestException as e:
            print(f"{timestamp()} ⚠️ Request error with {case_number}: {e}", flush=True)
        except Exception as e:
            print(f"{timestamp()} ⚠️ General error with {case_number}: {e}", flush=True)

        current += 1  # Proceed to next case number

# Finalize CSV file based on whether any relevant charges were found
if found_relevant_charge:
    final_csv_file = f"charges_CR{year}_{start}-{last_successful}.csv"
    os.rename(temp_csv_file, final_csv_file)
    print(f"{timestamp()} ✅ CSV file saved: {final_csv_file}", flush=True)
else:
    os.remove(temp_csv_file)
    print(f"{timestamp()} ❌ No murder or manslaughter charges found. CSV not saved.", flush=True)
