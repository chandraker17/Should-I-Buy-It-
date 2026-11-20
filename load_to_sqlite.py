import sqlite3
import pandas as pd

DB_FILE = "reviews.db"

products = pd.read_csv("products_clean.csv")
reviews = pd.read_csv("reviews_clean.csv").fillna("")

# only keep reviews whose product exists in the products table
reviews = reviews[reviews["product_id"].isin(products["product_id"])]

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# create the tables (re-running this script starts fresh)
cur.executescript("""
DROP TABLE IF EXISTS review_analysis;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    main_category TEXT,
    full_category TEXT,
    discounted_price REAL,
    actual_price REAL,
    discount_percentage INTEGER,
    rating REAL,
    rating_count INTEGER,
    about_product TEXT,
    product_link TEXT
);

CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    product_id TEXT,
    user_id TEXT,
    user_name TEXT,
    review_title TEXT,
    review_content TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE review_analysis (
    review_id TEXT PRIMARY KEY,
    sentiment TEXT,
    sentiment_score REAL,
    complaint_theme TEXT,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);

CREATE INDEX idx_reviews_product ON reviews(product_id);
""")

products.to_sql("products", conn, if_exists="append", index=False)
reviews.to_sql("reviews", conn, if_exists="append", index=False)
conn.commit()

print("products loaded:", cur.execute("SELECT COUNT(*) FROM products").fetchone()[0])
print("reviews loaded:", cur.execute("SELECT COUNT(*) FROM reviews").fetchone()[0])
conn.close()