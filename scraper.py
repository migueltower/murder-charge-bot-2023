import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import time

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Murder Charges").sheet1

# Define headers
if sheet.cell(1, 1).value != "Case Number":
    sheet.insert_row(["Case Number", "URL", "First Charge"], 1)

year = 2024
prefix = f"CR{year}-"
start = 160502
end = 160504

case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]

for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url, timeout=15)
        soup = BeautifulSoup(req.content, "html.parser")

        # Only look at specific divs with this class
        charge_divs = soup.find_all("div", class_="col-6 col-md-3 col-lg-3 col-xl-3")
        found_murder = False

        if charge_divs:
            print(f"{case_number} → Found {len(charge_divs)} charge-related divs")
        else:
            print(f"{case_number} → No divs with target class found")

        for div in charge_divs:
            charge = div.get_text(strip=True)
            if "MURDER" in charge.upper():
                sheet.append_row([case_number, url, charge])
                found_murder = True
                break  # only need the first one

        if not found_murder:
            print(f"{case_number} → no murder charge found")

        time.sleep(1.5)

    except Exception as e:
        print(f"Error with {case_number}: {e}")
        sheet.append_row([case_number, url, f"Error: {str(e)}"])
