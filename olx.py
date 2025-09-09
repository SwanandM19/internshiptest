

import argparse
import csv
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://www.olx.in/items/q-car-cover"

def normalize_url(base, href):
    if not href:
        return None
    return urllib.parse.urljoin(base, href)

def extract_text_safe(el):
    try:
        text = el.inner_text().strip()
        return text if text else None
    except Exception:
        return None

def scrape_olx_listings(url, headless=True, max_items=500, scroll_pause=1.2):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
         
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            locale="en-IN",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        print(f"Opening {url} ...")
        page.goto(url, timeout=60000)

        page.wait_for_selector("a[href*='/item/'], a[data-testid*='listing']", timeout=60000)
        last_height = page.evaluate("() => document.body.scrollHeight")
        scroll_rounds = 0
        while len(results) < max_items and scroll_rounds < 30:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(scroll_pause)
            page.wait_for_timeout(2000)
            new_height = page.evaluate("() => document.body.scrollHeight")
            if new_height == last_height:
            
                page.evaluate("window.scrollBy(0, 400)")
                time.sleep(scroll_pause)
                new_height = page.evaluate("() => document.body.scrollHeight")
                if new_height == last_height:
                    break
            last_height = new_height
            scroll_rounds += 1

      
            anchors = page.query_selector_all("a[href*='/item/'], a[href*='/p/'], a[data-testid*='listing']")
            seen_urls = set([r["url"] for r in results])
            for a in anchors:
                try:
                    href = a.get_attribute("href")
                    full = normalize_url(url, href)
                    if not full or full in seen_urls:
                        continue

        
                    anchor_text = extract_text_safe(a) or ""

               
                    title = None
                    for sel in ["h3", "h2", "h4", "h5", "span"]:
                        t_el = a.query_selector(sel)
                        if t_el:
                            t = extract_text_safe(t_el)
                            if t and len(t) > 1:
                                title = t
                                break
                    if not title:
                
                        title = anchor_text.splitlines()[0].strip() if anchor_text else None

                   
                    price = None
                
                    price_el = None
                   
                    price_el = a.query_selector("span:has-text('₹')") or a.query_selector("div:has-text('₹')")
                    if price_el:
                        price = extract_text_safe(price_el)
                    else:
                     
                        import re
                        m = re.search(r"₹\s?[\d,]+", anchor_text)
                        if m:
                            price = m.group(0)

              
                    img_url = None
                    img = a.query_selector("img")
                    if img:
                        src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy")
                        if src and not src.startswith("data:"):
                            img_url = normalize_url(url, src)

                    
                    location = None
                    # sometimes OLX keeps location in a small/span/div with certain attributes; search near the anchor
                    nearby = a.query_selector_all("span, small, div")
                    for n in nearby:
                        txt = extract_text_safe(n)
                        if not txt:
                            continue
                        # crude heuristic: Indian city names are often short; look for strings with commas or known separators
                        if len(txt) < 80 and any(x in txt for x in [",", " - ", "•"]) or ("IN" in txt) or ("India" in txt) or ("₹" not in txt and len(txt) < 40):
                            # prefer ones that look like a place
                            if "km" in txt or "away" in txt:
                                # skip distance markers
                                continue
                            location = txt
                            break

                    # If many fields missing, try to open the listing page to get structured info (only if necessary)
                    # (keep this commented by default to prevent many page loads — enable by setting open_details=True)
                    listing = {
                        "title": title,
                        "price": price,
                        "location": location,
                        "url": full,
                        "image": img_url,
                    }
                    results.append(listing)
                    seen_urls.add(full)

                    if len(results) >= max_items:
                        break
                except Exception:
                    continue

        print(f"Found {len(results)} candidate listings (may include duplicates or partial data).")
        browser.close()
    # dedupe by url preserve order
    seen = set()
    deduped = []
    for r in results:
        if r["url"] and r["url"] not in seen:
            deduped.append(r)
            seen.add(r["url"])
    return deduped

def save_results(results, base_name="olx_car_cover_results"):
    csv_file = base_name + ".csv"
    json_file = base_name + ".json"
    # Write CSV
    fieldnames = ["title", "price", "location", "url", "image"]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: (r.get(k) or "") for k in fieldnames})
    # Write JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(results)} results to {csv_file} and {json_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape OLX search results")
    parser.add_argument("--url", "-u", default=DEFAULT_URL, help="OLX search URL")
    parser.add_argument("--max", "-m", type=int, default=300, help="Maximum number of items to collect")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (useful for servers)")
    args = parser.parse_args()

    data = scrape_olx_listings(args.url, headless=args.headless, max_items=args.max)
    save_results(data)
    print("Done.")
