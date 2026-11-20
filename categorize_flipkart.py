"""
Gives each Flipkart product a category by looking for keywords in its name,
using the same category names as the Amazon data so the home-page buttons cover both.

Usage:  python categorize_flipkart.py
Run it after add_flipkart.py. Safe to re-run after you edit the rules below.
"""
import re
import sqlite3

# First match wins, so put more specific categories first. Add or change keywords as you like.
RULES = [
    ("Computers&Accessories", ["laptop", "mouse", "keyboard", "pen drive", "pendrive", "hard disk", "ssd",
                               "router", "monitor", "printer", "webcam", "memory card", "usb", "hdmi",
                               "cable", "adapter", "tablet", "macbook"]),
    ("Electronics", ["television", "tv", "headphone", "earphone", "earbud", "speaker", "soundbar",
                     "bluetooth", "camera", "mobile", "smartphone", "phone", "power bank", "smartwatch",
                     "smart watch", "watch", "projector", "home theatre", "neckband"]),
    ("Health&PersonalCare", ["trimmer", "shaver", "hair dryer", "straightener", "massager", "thermometer",
                             "bp monitor", "weighing scale", "glucometer", "nebulizer", "epilator"]),
    ("Home&Kitchen", ["air cooler", "cooler", "air conditioner", "ac", "fan", "refrigerator", "washing machine",
                      "microwave", "oven", "toaster", "geyser", "water heater", "room heater", "heater",
                      "water purifier", "vacuum", "cooker", "kettle", "mixer", "grinder", "juicer", "blender",
                      "chopper", "induction", "cooktop", "iron", "sandwich", "air fryer", "chimney",
                      "dishwasher", "bottle", "lunch box", "mattress", "pillow", "curtain", "bedsheet"]),
    ("HomeImprovement", ["drill", "tool kit", "led bulb", "bulb", "lamp", "light", "lock", "wrench",
                         "screwdriver", "paint"]),
    ("Toys&Games", ["toy", "puzzle", "board game", "doll", "lego"]),
    ("MusicalInstruments", ["guitar", "ukulele", "harmonium", "tabla", "piano", "flute"]),
    ("OfficeProducts", ["pen", "stapler", "paper", "marker", "diary"]),
]

patterns = [(cat, re.compile("|".join(rf"\b{re.escape(k)}s?\b" for k in kws))) for cat, kws in RULES]

conn = sqlite3.connect("reviews.db")
cur = conn.cursor()
cur.execute("UPDATE products SET main_category = NULL, full_category = NULL WHERE source = 'Flipkart'")
products = cur.execute("SELECT product_id, product_name FROM products WHERE source = 'Flipkart'").fetchall()

counts, unmatched = {}, []
for product_id, name in products:
    for category, pattern in patterns:
        if pattern.search(name.lower()):
            cur.execute("UPDATE products SET main_category = ?, full_category = ? WHERE product_id = ?",
                        (category, category, product_id))
            counts[category] = counts.get(category, 0) + 1
            break
    else:
        unmatched.append(name)
conn.commit()
conn.close()

print("Flipkart products:", len(products))
print("Given a category:", sum(counts.values()))
for category, n in sorted(counts.items(), key=lambda kv: -kv[1]):
    print("  ", category, n)
print("No category (still searchable by name):", len(unmatched))
for name in unmatched[:40]:
    print("  -", name[:70])