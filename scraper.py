import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import time

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Murder Charges").sheet1  # name of your Google Sheet

# Define headers
if sheet.cell(1, 1).value != "Case Number":
    sheet.insert_row(["Case Number", "URL", "First Charge"], 1)

# --- Generate list of case numbers and URLs ---
year = 2024
prefix = f"CR{year}-"
batch_size = 600
start = 160000
end = 160600  # adjust this range as needed

case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]

# --- Loop through URLs and extract charges ---
for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url, timeout=15)
        soup = BeautifulSoup(req.content, "html.parser")

        first_charge = None
        divs = soup.find_all("div")

        for i in range(len(divs) -
