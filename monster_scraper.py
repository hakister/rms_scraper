import os
import csv
import json
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageSequence

# Base URL
BASE_URL = "https://ratemyserver.net/index.php?page=mob_db&f=1&mlvsn=0&mlv=&mlv2=&bxpsn=0&exp=&exp2=&jxpsn=0&jexp=&jexp2=&rgc=0&mob_name=&mvp=0&flee=&dr=95&hit=&hr=100&aggr=0&minib=0&assi=0&immu=0&loot=0&imkb=0&det=0&sense=0&immo=0&sench=0&natk=0&chcha=0&plt=0&chtar=0&nspawn=1&sort_r=0&sort_o=0&mob_search=Search"

# Output setup
output_dir = "monster_gifs"
os.makedirs(output_dir, exist_ok=True)
csv_file = "monsters.csv"
json_file = "monsters.json"
csv_data = []

def make_silhouette_gif(input_path, output_path):
    """Create a black silhouette version of an animated GIF while keeping transparency."""
    try:
        with Image.open(input_path) as img:
            frames = []
            durations = []

            for frame in ImageSequence.Iterator(img):
                # Flatten over a transparent background
                rgba = Image.new("RGBA", img.size, (0, 0, 0, 0))
                rgba.paste(frame.convert("RGBA"))

                # Turn any visible pixel to black (keep alpha)
                pixels = rgba.load()
                for y in range(rgba.height):
                    for x in range(rgba.width):
                        r, g, b, a = pixels[x, y]
                        if a > 0:
                            pixels[x, y] = (0, 0, 0, a)

                frames.append(rgba)
                durations.append(frame.info.get("duration", 100))

            # Save as animated GIF
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                loop=0,
                duration=durations,
                disposal=2
            )
    except Exception as e:
        print(f"⚠️ Failed to create silhouette for {input_path}: {e}")

def scrape_page(page_num):
    """Fetch one page of monsters."""
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

                # Clean up spaces and split into array
                name_text = raw_text.split(" (")[0].replace("\xa0", " ").strip()
                name_list = [n.strip() for n in name_text.split(" / ")]

                mob_id = raw_text.split("#")[-1]  # Extract ID from Mob-ID#1234
                img_url = img_tag["src"]
                filename = f"{mob_id}.gif"
                silhouette_filename = f"{mob_id}_silhouette.gif"
                path = os.path.join(output_dir, filename)
                silhouette_path = os.path.join(output_dir, silhouette_filename)

                print(f"🟢 {', '.join(name_list)} (ID {mob_id}) — {img_url}")

                # Download original GIF if missing
                if not os.path.exists(path):
                    img_data = requests.get(img_url).content
                    with open(path, "wb") as f:
                        f.write(img_data)
                else:
                    print(f"   ⏩ Skipping download, already exists: {filename}")

                # Create silhouette GIF if missing
                if not os.path.exists(silhouette_path):
                    make_silhouette_gif(path, silhouette_path)
                else:
                    print(f"   ⏩ Skipping silhouette, already exists: {silhouette_filename}")

                # Store data
                csv_data.append([mob_id, name_list, img_url, path, silhouette_path])
        except Exception as e:
            print(f"⚠️ Failed to parse monster block: {e}")

    page += 1
    time.sleep(1)  # Be polite to the server

# Save CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Monster ID", "Monster Name(s)", "Image URL", "Original Filename", "Silhouette Filename"])
    writer.writerows(csv_data)

# Save JSON
json_data = []
for row in csv_data:
    mob_id, name_list, img_url, image_path, silhouette_path = row
    json_data.append({
        "name": name_list,
        "image": image_path.replace("/", "\\"),
        "silhouette": silhouette_path.replace("/", "\\")
    })

with open(json_file, "w", encoding="utf-8") as jf:
    json.dump(json_data, jf, ensure_ascii=False, indent=2)

print(f"\n📦 Finished scraping {len(csv_data)} monsters.")
print(f"   CSV saved to {csv_file}")
print(f"   JSON saved to {json_file}")
