import json, re, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright


URL = "https://www.micheck123.com/book"
STATE = "state.json"
DAYS = {"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"}


def get_slots():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector("text=Available Spots", timeout=60000)
        text = page.inner_text("body")
        browser.close()


    slots, day, cur = {}, None, None
    for line in (l.strip() for l in text.splitlines()):
        if not line:
            continue
        if line.startswith("Total"):
            break
        if line in DAYS:
            day, cur = line, None
            continue
        if re.match(r"^\d{1,2}:\d{2}\s*[AP]M", line):
            name = re.sub(r"Spots Full", "", line).strip()
            cur = f"{day} {name}"
            slots[cur] = "Spots Full" not in line   # True = available
        elif cur and "Spots Full" in line:
            slots[cur] = False
    return slots


def notify(msg):
    print(msg)
    url = ("https://api.callmebot.com/start.php?user=@deveshsalke"
           "&text=" + urllib.parse.quote_plus("Slots are available now")
           + "&lang=en-US-Standard-B&rpt=2&timeout=30")
    urllib.request.urlopen(url, timeout=60)


slots = get_slots()
if not slots:
    raise SystemExit("No slots parsed - page layout may have changed")


available = sorted(k for k, v in slots.items() if v)
try:
    prev = set(json.load(open(STATE)))
except Exception:
    prev = set()


new = [s for s in available if s not in prev]
if new:
    notify("New open mic spots:\n" + "\n".join(new) + "\n" + URL)


json.dump(available, open(STATE, "w"))
