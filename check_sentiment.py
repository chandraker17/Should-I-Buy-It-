import sqlite3
import pandas as pd

conn = sqlite3.connect("reviews.db")
df = pd.read_sql("""SELECT r.star_rating, a.sentiment
                    FROM reviews r JOIN review_analysis a ON a.review_id = r.review_id
                    WHERE r.star_rating IS NOT NULL""", conn)

def from_stars(s):
    return "positive" if s >= 4 else ("neutral" if s == 3 else "negative")

df["stars say"] = df["star_rating"].apply(from_stars)
print("Reviews checked:", len(df))
print("Agreement with star ratings (all reviews): {:.1f}%".format(100 * (df["sentiment"] == df["stars say"]).mean()))

clear = df[df["star_rating"] != 3]   # 3-star reviews are ambiguous, so also check without them
print("Agreement on 1-2 and 4-5 star reviews: {:.1f}%".format(100 * (clear["sentiment"] == clear["stars say"]).mean()))
print()
print(pd.crosstab(df["stars say"], df["sentiment"], rownames=["stars say"], colnames=["VADER says"]))