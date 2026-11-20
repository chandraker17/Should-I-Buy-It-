import sys
import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "amazon.csv"
df = pd.read_csv(path)
print("Rows read:", len(df))

# ---------- products ----------
def to_number(series):
    cleaned = (series.astype(str)
               .str.replace("₹", "", regex=False)
               .str.replace(",", "", regex=False)
               .str.replace("%", "", regex=False)
               .str.strip())
    return pd.to_numeric(cleaned, errors="coerce")

df["discounted_price"] = to_number(df["discounted_price"])
df["actual_price"] = to_number(df["actual_price"])
df["rating"] = to_number(df["rating"])
df["rating_count"] = to_number(df["rating_count"])

df["discount_percentage"] = ((1 - df["discounted_price"] / df["actual_price"]) * 100).round(0)
df["main_category"] = df["category"].str.split("|").str[0]

products = (df.drop_duplicates(subset="product_id")
              [["product_id", "product_name", "main_category", "category",
                "discounted_price", "actual_price", "discount_percentage",
                "rating", "rating_count", "about_product", "product_link"]]
              .rename(columns={"category": "full_category"}))

# ---------- reviews ----------
# Several reviews are packed into one cell, joined by commas.
# Real commas inside a review are usually followed by a space ("good, but"),
# while the commas that JOIN reviews are not. So we split only on commas
# that have no space after them.
import re

def split_packed(text):
    return [p.strip() for p in re.split(r",(?!\s)", str(text))]

rows, skipped, no_title = [], 0, 0

for _, r in df.drop_duplicates(subset="product_id").iterrows():
    ids = split_packed(r["review_id"])
    contents = split_packed(r["review_content"])
    n = len(ids)
    if len(contents) != n:          # review text is what we need; if it won't line up, skip
        skipped += 1
        continue
    titles = split_packed(r["review_title"])
    user_ids = split_packed(r["user_id"])
    user_names = split_packed(r["user_name"])
    if len(titles) != n:
        titles = [""] * n           # title is optional
        no_title += 1
    if len(user_ids) != n:
        user_ids = [""] * n
    if len(user_names) != n:
        user_names = [""] * n
    for i in range(n):
        rows.append({"review_id": ids[i], "product_id": r["product_id"],
                     "user_id": user_ids[i], "user_name": user_names[i],
                     "review_title": titles[i], "review_content": contents[i]})

reviews = pd.DataFrame(rows).drop_duplicates(subset="review_id")

products.to_csv("products_clean.csv", index=False)
reviews.to_csv("reviews_clean.csv", index=False)

print("Unique products:", len(products))
print("Products with usable reviews:", len(products) - skipped)
print("Products skipped (review text didn't line up):", skipped)
print("Products kept but without titles:", no_title)
print("Total reviews kept:", len(reviews))