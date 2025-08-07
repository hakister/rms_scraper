import os
import csv
import time
import requests
from bs4 import BeautifulSoup

# Base URL (no page_num yet)
BASE_URL = "https://ratemyserver.net/index.php?page=mob_db&f=1&mlvsn=0&mlv=&mlv2=&bxpsn=0&exp=&exp2=&jxpsn=0&jexp=&jexp2=&rgc=0&mob_name=&mvp=0&flee=&dr=95&hit=&hr=100&aggr=0&minib=0&assi=0&immu=0&loot=0&imkb=0&det=0&sense=0&immo=0&sench=0&natk=0&chcha=0&plt=0&chtar=0&nspawn=1&sort_r=0&sort_o=0&mob_search=Search"

# Output setup
output_dir = "monster_gifs"
os.makedirs(output_dir, exist_ok=True)
csv_file = "monsters.csv"
csv_data = []

def scrape_page(page_num):
    if page_num == 1:
        url = BASE_URL
    else:
        url = BASE_URL + f"&page_num={page_num}"
    print(f"\n🔎 Fetching page {page_num} → {url}")

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        monster_blocks = soup.select("div.mob_grid_container")
        print(f"🔍 Found {len(monster_blocks)} monsters on page {page_num}")
        return monster_blocks
    except Exception as e:
        print(f"❌ Error loading page {page_num}: {e}")
        return []

# Pagination loop
page = 1
while True:
    blocks = scrape_page(page)
    if not blocks:
        print(f"✅ Done! No more monsters found after page {page}.")
        break

    for block in blocks:
        try:
            name_tag = block.select_one(".mob_stat_head span")
            img_tag = block.select_one("img.mob_img")

            if name_tag and img_tag:
                raw_text = name_tag.get_text(strip=True)
                name = raw_text.split(" (")[0]
                mob_id = raw_text.split("#")[-1]  # Extract ID from Mob-ID#1234
                img_url = img_tag["src"]
                filename = f"{mob_id}.gif"
                path = os.path.join(output_dir, filename)

                print(f"🟢 {name} (ID {mob_id}) — {img_url}")

                # Save GIF
                img_data = requests.get(img_url).content
                with open(path, "wb") as f:
                    f.write(img_data)

                csv_data.append([mob_id, name, img_url, path])
        except Exception as e:
            print(f"⚠️ Failed to parse monster block: {e}")

    page += 1
    time.sleep(1)  # Be polite to the server

# Save CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Monster ID", "Monster Name", "Image URL", "Local Filename"])
    writer.writerows(csv_data)

print(f"\n📦 Finished scraping {len(csv_data)} monsters. Data saved to {csv_file}")
