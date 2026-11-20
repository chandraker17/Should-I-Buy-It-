"""
Adds Flipkart reviews to reviews.db (the database you already built).

Usage:  python add_flipkart.py flipkart.csv
Safe to re-run: it removes the earlier Flipkart rows first.
"""
import hashlib
import re
import sqlite3
import sys

import pandas as pd

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "flipkart.csv"
DB_FILE = "reviews.db"
MIN_REVIEWS_PER_PRODUCT = 20   # skip products with very few reviews
MAX_PRODUCTS = 300             # keep the 300 products with the most reviews
MAX_REVIEWS_PER_PRODUCT = 50   # random sample per product, keeps the database small

# ---------- read ----------
try:
    df = pd.read_csv(CSV_PATH)
except UnicodeDecodeError:
    df = pd.read_csv(CSV_PATH, encoding="latin-1")
print("Rows read:", len(df))

# In this file 'Review' is the short headline and 'Summary' is the full review text.
df = df.rename(columns={"Product_name": "product_name", "Price": "price", "Rate": "rating",
                        "Review": "review_title", "Summary": "review_content"})
df = df[["product_name", "price", "rating", "review_title", "review_content"]]

# ---------- clean ----------
def clean_text(x):
    x = "" if pd.isna(x) else str(x)
    x = re.sub(r"\?{2,}", " ", x)            # broken emoji show up as ????
    x = re.sub(r"READ MORE\s*$", "", x)
    return x.strip()

df["product_name"] = df["product_name"].fillna("").astype(str).str.strip()
df["review_title"] = df["review_title"].apply(clean_text)
df["review_content"] = df["review_content"].apply(clean_text)
# the rupee sign is garbled in this file, so keep only the digits of the price
df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce")
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

df = df[(df["product_name"] != "") & (df["review_content"] != "")]
df = df[df["rating"].between(1, 5)]
df["rating"] = df["rating"].astype(int)
df = df.drop_duplicates(subset=["product_name", "review_title", "review_content"])
print("Rows after cleaning:", len(df))

# ---------- pick products ----------
stats = (df.groupby("product_name")
           .agg(n=("rating", "size"), avg_rating=("rating", "mean"),
                price=("price", lambda s: s.mode().iloc[0] if s.notna().any() else None))
           .reset_index())
stats = stats[stats["n"] >= MIN_REVIEWS_PER_PRODUCT].sort_values("n", ascending=False).head(MAX_PRODUCTS)
print("Products kept:", len(stats))
if stats.empty:
    sys.exit("No product has enough reviews. Lower MIN_REVIEWS_PER_PRODUCT at the top of the script.")

stats["product_id"] = "FK" + stats["product_name"].apply(lambda s: hashlib.md5(s.encode()).hexdigest()[:10])

kept = df[df["product_name"].isin(stats["product_name"])]
# shuffle, then take the first 50 reviews of each product (a random sample)
kept = kept.sample(frac=1, random_state=42).groupby("product_name").head(MAX_REVIEWS_PER_PRODUCT)
kept = kept.merge(stats[["product_name", "product_id"]], on="product_name")
kept = kept.reset_index(drop=True)
kept["review_id"] = ["FKR" + str(i + 1) for i in range(len(kept))]

# ---------- write into the database ----------
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

def add_column(table, column, decl):
    existing = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

add_column("products", "source", "TEXT")
add_column("reviews", "star_rating", "INTEGER")
cur.execute("UPDATE products SET source = 'Amazon' WHERE source IS NULL")

# remove earlier Flipkart rows so the script can be re-run
cur.execute("""DELETE FROM review_analysis WHERE review_id IN
               (SELECT review_id FROM reviews WHERE product_id IN
                (SELECT product_id FROM products WHERE source = 'Flipkart'))""")
cur.execute("""DELETE FROM reviews WHERE product_id IN
               (SELECT product_id FROM products WHERE source = 'Flipkart')""")
cur.execute("DELETE FROM products WHERE source = 'Flipkart'")

cur.executemany(
    """INSERT INTO products (product_id, product_name, discounted_price, rating, rating_count, source)
       VALUES (?, ?, ?, ?, ?, 'Flipkart')""",
    [(r.product_id, r.product_name, None if pd.isna(r.price) else float(r.price),
      round(float(r.avg_rating), 1), int(r.n)) for r in stats.itertuples()])

cur.executemany(
    """INSERT INTO reviews (review_id, product_id, user_id, user_name, review_title, review_content, star_rating)
       VALUES (?, ?, '', '', ?, ?, ?)""",
    [(r.review_id, r.product_id, r.review_title, r.review_content, int(r.rating)) for r in kept.itertuples()])
conn.commit()

print("Flipkart products added:", len(stats))
print("Flipkart reviews added:", len(kept))
print("Database now has", cur.execute("SELECT COUNT(*) FROM products").fetchone()[0], "products and",
      cur.execute("SELECT COUNT(*) FROM reviews").fetchone()[0], "reviews")
conn.close()