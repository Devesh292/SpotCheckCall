import json, os, re, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright


URL = "https://www.micheck123.com/book"
STATE = "state.json"
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M", re.I)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get_text():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(user_agent=UA).new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        try:
            page.wait_for_selector(r"text=/\d{1,2}:\d{2}\s*[AP]M/i", timeout=60000)
        except Exception:
            print("Slots never appeared. Page text was:")
            print(page.inner_text("body")[:1500])
            raise
        text = page.inner_text("body")
        browser.close()
    return text


def parse(text):
    slots, day, cur = {}, None, None
    for line in (l.strip(" *\t") for l in text.splitlines()):
        if not line:
            continue
        if line.startswith("Total"):
            break
        if line.startswith(DAYS) and len(line) < 30:
            day, cur = line, None
            continue
        if TIME_RE.match(line):
            name = re.sub(r"spots full", "", line, flags=re.I).strip()
            cur = f"{day} {name}"
            slots[cur] = "spots full" not in line.lower()   # True = available
        elif cur and "spots full" in line.lower():
            slots[cur] = False
    return slots


def call():
    url = ("https://api.callmebot.com/start.php?user=@deveshsalke"
           "&text=" + urllib.parse.quote_plus("Slots are available now")
           + "&lang=en-US-Standard-B&rpt=2&timeout=30")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        print("CallMeBot reply:", r.status, r.read().decode(errors="ignore")[:300])


if os.environ.get("TEST") == "true":
    print("TEST MODE: forcing a call")
    call()


slots = parse(get_text())
print("Slots found:")
for k, v in slots.items():
    print(("  OPEN  " if v else "  full  ") + k)
if not slots:
    raise SystemExit("No slots parsed - page layout may have changed")


available = sorted(k for k, v in slots.items() if v)
try:
    prev = set(json.load(open(STATE)))
except Exception:
    prev = set()


new = [s for s in available if s not in prev]
print("Newly open:", new or "none")
if new:
    call()   # if this fails, state is not saved, so the next run retries


json.dump(available, open(STATE, "w"))
