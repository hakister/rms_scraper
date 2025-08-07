import os
import csv
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
csv_data = []

def make_silhouette_gif(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            frames = []
            durations = []
            transparency_index = img.info.get("transparency", None)

            for frame in ImageSequence.Iterator(img):
                # Convert to RGBA and composite over transparent background
                rgba = Image.new("RGBA", img.size, (0, 0, 0, 0))
                rgba.paste(frame.convert("RGBA"))

                # Create black silhouette
                pixels = rgba.load()
                for y in range(rgba.height):
                    for x in range(rgba.width):
                        r, g, b, a = pixels[x, y]
                        if a > 0:
                            pixels[x, y] = (0, 0, 0, a)

                frames.append(rgba)
                durations.append(frame.info.get("duration", 100))

            # Convert all frames to P mode for GIF
            palette_frames = []
            for rgba in frames:
                palette_frame = rgba.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE, colors=255)
                palette_frame.info["transparency"] = palette_frame.getpixel((0, 0))  # Assume corner is transparent
                palette_frames.append(palette_frame)

            palette_frames[0].save(
                output_path,
                save_all=True,
                append_images=palette_frames[1:],
                loop=0,
                duration=durations,
                disposal=2
            )
    except Exception as e:
        print(f"⚠️ Failed to create silhouette for {input_path}: {e}")


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
                silhouette_filename = f"{mob_id}_silhouette.gif"
                path = os.path.join(output_dir, filename)
                silhouette_path = os.path.join(output_dir, silhouette_filename)

                print(f"🟢 {name} (ID {mob_id}) — {img_url}")

                # Save original GIF
                img_data = requests.get(img_url).content
                with open(path, "wb") as f:
                    f.write(img_data)

                # Create silhouette GIF
                make_silhouette_gif(path, silhouette_path)

                csv_data.append([mob_id, name, img_url, path, silhouette_path])
        except Exception as e:
            print(f"⚠️ Failed to parse monster block: {e}")

    page += 1
    time.sleep(1)  # Be polite to the server

# Save CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Monster ID", "Monster Name", "Image URL", "Original Filename", "Silhouette Filename"])
    writer.writerows(csv_data)

print(f"\n📦 Finished scraping {len(csv_data)} monsters. Data saved to {csv_file}")
