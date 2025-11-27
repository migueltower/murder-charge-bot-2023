import requests
from bs4 import BeautifulSoup
import csv
import os
import random
import time
from datetime import datetime, timedelta

def timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

# 🔹 Helper: print snippet of fetched page for diagnostics
def print_snippet(page_text, case_number):
    snippet = page_text[:300].replace("\n", " ").replace("\r", " ")
    print(f"{timestamp()} 🌐 Page snippet for {case_number}: {snippet}...", flush=True)

# 🔹 NEW: SSL-tolerant request wrapper (added without modifying any other function)
def safe_session_get(session, url, headers, timeout=15):
    """Try normal SSL request; on SSL certificate failure, retry with verify=False.
    This handles the court's intermittent broken certificate chain."""
    try:
        return session.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.SSLError as e:
        print(f"{timestamp()} 🔐 SSL error on first attempt for {url}: {e}", flush=True)
        print(f"{timestamp()} 🔄 Retrying without certificate verification (court SSL issue).", flush=True)
        return session.get(url, headers=headers, timeout=timeout, verify=False)

start = int(os.getenv("START", 0))
end = int(os.getenv("END", 9999))
year = int(os.getenv("YEAR", 2023))
prefix = f"CR{year}-"

# Expanded fields for richer data
fieldnames = [
    "Case Number", "URL",
    "Case Type", "Location",
    "Defendant", "Sex", "Attorney", "Judge",
    "Charge", "ARS Code", "Disposition Code", "Disposition", "Crime Date", "Disposition Date",
    "Next Hearing Date", "Next Hearing Event",
    "Most Recent Filing", "Most Recent Filing Date"
]

current = start
last_successful = start
request_limit = 1000
requests_made = 0
delay_seconds = 31  # always sleep 69 seconds between requests
job_start_time = datetime.now()
job_deadline = job_start_time + timedelta(hours=5, minutes=55)

with open("progress.txt", "w") as prog:
    prog.write(str(current))

temp_csv_file = f"charges_CR{year}_{start}-placeholder.csv"

header_pool = [
    {
        "User-Agent": "Mozilla/5.0 (compatible; CourtScraper/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
]

with open(temp_csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    print(f"{timestamp()} 🔁 Running case range: {start} to {end} for year {year}", flush=True)
    session = requests.Session()

    while current <= end and requests_made < request_limit and datetime.now() < job_deadline:
        case_number = f"{prefix}{str(current).zfill(6)}"
        print(f"{timestamp()} Checking case: {case_number}", flush=True)
        url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"

        try:
            headers = random.choice(header_pool)

            # 🔹 PATCHED REQUEST (replaces session.get)
            req = safe_session_get(session, url, headers=headers, timeout=15)

            print(f"{timestamp()} Request status: {req.status_code} URL: {req.url}", flush=True)

            if not req.content.strip():
                print(f"{timestamp()} ⚠️ Empty response body for {case_number}.", flush=True)
                break

            soup = BeautifulSoup(req.content, "html.parser")
            page_text = soup.get_text(strip=True)

            # 🔹 Diagnostic: print a short snippet from the page
            print_snippet(page_text, case_number)

            # 🔹 Handle server-busy or unavailable messages clearly
            if any(msg in page_text for msg in ["Server busy", "Please try again later", "temporarily unavailable"]):
                print(f"{timestamp()} 🚫 Server busy or unavailable message detected for {case_number}. Ending run safely.", flush=True)
                break

            last_successful = current
            with open("progress.txt", "w") as prog:
                prog.write(str(last_successful + 1))

            # --- Initialize defaults
            case_type = location = ""
            defendant_name = sex = attorney = judge = ""
            charge = ars_code = disposition_code = disposition = crime_date = disposition_date = ""
            next_hearing_date = next_hearing_event = ""
            most_recent_filing = most_recent_filing_date = ""

            # --- CASE INFO
            case_info = soup.find("div", id="tblForms")
            if case_info:
                divs = case_info.find_all("div")
                print(f"{timestamp()} 🧾 Case Info rows found: {len(divs)}", flush=True)
                for i, div in enumerate(divs):
                    text = div.get_text(strip=True)
                    if "Case Type" in text and i + 1 < len(divs):
                        case_type = divs[i + 1].get_text(strip=True)
                    if "Location" in text and i + 1 < len(divs):
                        location = divs[i + 1].get_text(strip=True)

            # --- PARTY INFO
            party_info = soup.find("div", id="tblDocket2")
            if party_info:
                rows = party_info.find_all("div", class_="row")
                print(f"{timestamp()} 👤 Party Info rows found: {len(rows)}", flush=True)
                for row in rows:
                    fields = [d.get_text(strip=True) for d in row.find_all("div")]
                    if any("Defendant" in f for f in fields):
                        for i, text in enumerate(fields):
                            if "Party Name" in text and i + 1 < len(fields):
                                defendant_name = fields[i + 1]
                            if "Sex" in text and i + 1 < len(fields):
                                sex = fields[i + 1]
                            if "Attorney" in text and i + 1 < len(fields):
                                attorney = fields[i + 1]
                            if "Judge" in text and i + 1 < len(fields):
                                judge = fields[i + 1]

            # --- DISPOSITION INFO
            disp_section = soup.find("div", id="tblDocket12")
            if disp_section:
                rows = disp_section.find_all("div", class_="row g-0")
                print(f"{timestamp()} ⚖️ Disposition rows found: {len(rows)}", flush=True)
                for row in rows:
                    divs = row.find_all("div")
                    fields = [div.get_text(strip=True) for div in divs]
                    if any("Description" in f for f in fields):
                        for i, text in enumerate(fields):
                            if "Description" in text and i + 1 < len(fields):
                                charge = fields[i + 1]
                            if "ARSCode" in text and i + 1 < len(fields):
                                ars_code = fields[i + 1]
                            if "Disposition Code" in text and i + 1 < len(fields):
                                disposition_code = fields[i + 1]
                            if "Disposition" in text and i + 1 < len(fields):
                                disposition = fields[i + 1]
                            if "Crime Date" in text and i + 1 < len(fields):
                                crime_date = fields[i + 1]
                            if "Date" in text and i + 1 < len(fields):
                                disposition_date = fields[i + 1]
                        break  # just first charge row

            # --- CALENDAR INFO (next upcoming hearing)
            cal_section = soup.find("div", id="tblForms4")
            if cal_section:
                rows = cal_section.find_all("div", class_="row g-0")
                print(f"{timestamp()} 📅 Calendar rows found: {len(rows)}", flush=True)
                for row in rows:
                    cols = [d.get_text(strip=True) for d in row.find_all("div")]
                    if len(cols) >= 3 and "Date" not in cols[0]:
                        next_hearing_date = cols[1]
                        next_hearing_event = cols[-1]
                        break

            # --- CASE DOCUMENTS (most recent)
            doc_section = soup.find("div", id="tblForms3")
            if doc_section:
                rows = doc_section.find_all("div", class_="row g-0")
                print(f"{timestamp()} 📄 Document rows found: {len(rows)}", flush=True)
                for row in reversed(rows):
                    cols = [d.get_text(strip=True) for d in row.find_all("div")]
                    if any("Description" in c for c in cols):
                        continue
                    if len(cols) >= 4:
                        most_recent_filing_date = cols[1]
                        most_recent_filing = cols[3]
                        break

            # --- WRITE TO CSV
            writer.writerow({
                "Case Number": case_number,
                "URL": url,
                "Case Type": case_type,
                "Location": location,
                "Defendant": defendant_name,
                "Sex": sex,
                "Attorney": attorney,
                "Judge": judge,
                "Charge": charge,
                "ARS Code": ars_code,
                "Disposition Code": disposition_code,
                "Disposition": disposition,
                "Crime Date": crime_date,
                "Disposition Date": disposition_date,
                "Next Hearing Date": next_hearing_date,
                "Next Hearing Event": next_hearing_event,
                "Most Recent Filing": most_recent_filing,
                "Most Recent Filing Date": most_recent_filing_date
            })

        except requests.exceptions.RequestException as e:
            print(f"{timestamp()} ⚠️ Request error with {case_number}: {e}", flush=True)
        except Exception as e:
            print(f"{timestamp()} ⚠️ General error with {case_number}: {e}", flush=True)

        current += 1
        requests_made += 1
        time_remaining = (job_deadline - datetime.now()).total_seconds()
        if time_remaining < delay_seconds + 60:
            print(f"{timestamp()} ⏰ Time limit approaching — exiting safely after {requests_made} requests.", flush=True)
            break

        print(f"{timestamp()} 💤 Sleeping for {int(delay_seconds)}s", flush=True)
        time.sleep(delay_seconds)

final_csv_file = f"charges_CR{year}_{start}-{last_successful}.csv"
os.rename(temp_csv_file, final_csv_file)
print(f"{timestamp()} ✅ CSV file saved: {final_csv_file}", flush=True)
print(f"{timestamp()} 🕒 Job duration: {(datetime.now() - job_start_time)}", flush=True)
