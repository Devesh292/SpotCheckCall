import json, os, re, time, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright

URL = "https://www.micheck123.com/book"
STATE = "state.json"
RUN_MINUTES = 340      # how long one job keeps checking
INTERVAL = 60          # seconds between checks
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M", re.I)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def fetch_text(browser):
    ctx = browser.new_context(user_agent=UA)
    page = ctx.new_page()
    try:
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector(r"text=/\d{1,2}:\d{2}\s*[AP]M/i", timeout=60000)
        return page.inner_text("body")
    finally:
        ctx.close()

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

def main():
    if os.environ.get("TEST") == "true":
        print("TEST MODE: forcing a call")
        call()

    try:
        prev = set(json.load(open(STATE)))
    except Exception:
        prev = set()

    end = time.time() + RUN_MINUTES * 60
    with sync_playwright() as p:
        browser = p.chromium.launch()
        while True:
            started = time.time()
            try:
                slots = parse(fetch_text(browser))
                if not slots:
                    print(time.strftime("%H:%M:%S"), "No slots parsed")
                else:
                    available = {k for k, v in slots.items() if v}
                    new = sorted(available - prev)
                    print(time.strftime("%H:%M:%S"),
                          f"{len(available)} open of {len(slots)}; new: {new or 'none'}")
                    if new:
                        call()          # if this fails, prev is not updated, so it retries
                    prev = available
                    json.dump(sorted(prev), open(STATE, "w"))
            except Exception as e:
                print(time.strftime("%H:%M:%S"), "Check failed:", e)
            if time.time() + INTERVAL > end:
                break
            time.sleep(max(0, INTERVAL - (time.time() - started)))
        browser.close()

main()
