import os
import re
import csv
import json
import time
import requests
import html
from bs4 import BeautifulSoup

BASE_URL = "https://ratemyserver.net/index.php?page=item_db&itype=6&iclass=0&tabj=on&iju=-1&iname=&idesc=&iscript=&islot_sign=-1&islot=-1&icfix=&i_ele=-1&i_status=-1&i_race=-1&i_bonus=-1&hnd=1&hns=1&sort_r=0&sort_o=0&isearch=Search&page_num={}"
IMAGE_DIR = "monster_cards"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Referer": "https://ratemyserver.net/"
}

def scrape_from_url(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table", class_="content_box_m")
    data = []

    for idx, table in enumerate(tables, start=1):
        try:
            title_tr = table.find("tr", class_="lmd")
            if not title_tr:
                continue

            # --- Large image ---
            img_tag = title_tr.find("img")
            large_img_url = None
            if img_tag and "onmouseover" in img_tag.attrs:
                raw = img_tag["onmouseover"]
                decoded = html.unescape(raw)
                match = re.search(r"(https://file5s\.ratemyserver\.net/items/large/\d+\.gif)", decoded)
                if match:
                    large_img_url = match.group(1)

            # --- Item name, category, ID ---
            title_div = title_tr.find("div", style=lambda v: v and "padding-left" in v)
            if not title_div:
                continue
            title_text = title_div.get_text(strip=True, separator=" ")
            m = re.match(r"(.+?)\s*\[(.+?)\].*Item ID#\s*(\d+)", title_text)
            if not m:
                continue
            item_name, item_category, item_id = m.groups()

            # --- Info grid row ---
            info_tr = title_tr.find_next_sibling("tr")
            prefix_suffix = None
            if info_tr:
                items = info_tr.select("div.info_grid_item")
                for i in range(0, len(items), 2):
                    label = items[i].get_text(strip=True)
                    value = items[i+1].get_text(strip=True)
                    if label.lower() == "pre/suffix":
                        prefix_suffix = value
                        break

            # --- Description ---
            desc_th = table.find("th", string="Description")
            description = ""
            if desc_th:
                desc_td = desc_th.find_next_sibling("td")
                if desc_td:
                    for br in desc_td.find_all("br"):
                        br.replace_with("\n")
                    description = desc_td.get_text("\n", strip=True)

            # --- Download image ---
            if large_img_url:
                save_image(large_img_url, os.path.join(IMAGE_DIR, f"{item_id}.gif"))

            # Progress message
            print(f"🟢 Retrieved: {item_name} (ID: {item_id})")

            data.append({
                "item_name": item_name,
                "item_category": item_category,
                "item_id": item_id,
                "large_img_url": large_img_url,
                "prefix_suffix": prefix_suffix,
                "description": description
            })

        except Exception as e:
            print(f"Error parsing table: {e}")

    return data

def save_image(url, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    with open(filename, "wb") as f:
        f.write(resp.content)

def save_to_json(data, filename="cards.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_to_csv(data, filename="cards.csv"):
    if not data:
        return
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    all_results = []
    page = 1

    while True:
        url = BASE_URL.format(page)
        print(f"📖 Fetching page {page}...")
        page_results = scrape_from_url(url)

        if not page_results:
            print("No more items found. Stopping.")
            break

        all_results.extend(page_results)
        page += 1
        time.sleep(2)  # Delay between requests

    save_to_json(all_results)
    save_to_csv(all_results)
    print(f"🔥 Found {len(all_results)} total items and saved to cards.json, cards.csv, and downloaded images to {IMAGE_DIR}/")
