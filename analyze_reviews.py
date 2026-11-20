import sqlite3
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DB_FILE = "reviews.db"

# Topic keywords. A review gets the theme with the most keyword matches.
THEMES = {
    "quality": ["quality", "build", "material", "flimsy", "cheap", "sturdy", "fake", "original"],
    "durability": ["broke", "broken", "stopped working", "stop working", "durable", "last", "lasted",
                   "damaged", "defective", "faulty", "died", "tear", "torn","not work", "doesn't work", "does not work", "stopped", "waste", "defect"],
    "value for money": ["price", "value", "worth", "money", "costly", "expensive", "affordable", "budget", "overpriced"],
    "delivery & packaging": ["delivery", "delivered", "packaging", "packed", "package", "late", "shipping", "box"],
    "performance": ["speed", "fast", "slow", "battery", "charging", "charge", "performance", "sound", "picture",
                    "display", "works", "working", "lag", "signal", "connect"],
    "design & fit": ["size", "fit", "design", "look", "color", "colour", "light", "heavy", "length", "comfortable"],
    "service & returns": ["service", "return", "refund", "replacement", "warranty", "support", "seller", "customer care"],
}

def find_theme(text):
    text = text.lower()
    best, best_count = "other", 0
    for theme, words in THEMES.items():
        count = sum(text.count(w) for w in words)
        if count > best_count:
            best, best_count = theme, count
    return best

def label(score):
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"

conn = sqlite3.connect(DB_FILE)
reviews = pd.read_sql("SELECT review_id, review_title, review_content FROM reviews", conn)

analyzer = SentimentIntensityAnalyzer()
results = []
for _, r in reviews.iterrows():
    text = f"{r['review_title']}. {r['review_content']}".strip(". ")
    score = analyzer.polarity_scores(text)["compound"]
    results.append((r["review_id"], label(score), round(score, 3), find_theme(text)))

# the analysis table now stores a 'theme' (what the review talks about) for every review
conn.executescript("""
DROP TABLE IF EXISTS review_analysis;
CREATE TABLE review_analysis (
    review_id TEXT PRIMARY KEY,
    sentiment TEXT,
    sentiment_score REAL,
    theme TEXT,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);
""")
conn.executemany("INSERT INTO review_analysis VALUES (?, ?, ?, ?)", results)
conn.commit()

print("Reviews analysed:", len(results))
print(pd.read_sql("SELECT sentiment, COUNT(*) AS reviews FROM review_analysis GROUP BY sentiment", conn))
print(pd.read_sql("""SELECT theme, COUNT(*) AS negative_reviews FROM review_analysis
                     WHERE sentiment='negative' GROUP BY theme ORDER BY 2 DESC""", conn))
conn.close()