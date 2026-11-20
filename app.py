import re
import sqlite3
from flask import Flask, request, render_template_string, abort

app = Flask(__name__)
@app.template_filter("nice")
def nice(name):
    """Turn 'OfficeProducts' into 'Office Products' and 'Home&Kitchen' into 'Home & Kitchen'."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).replace("&", " & ").replace("  ", " ")
DB_FILE = "reviews.db"
MIN_REVIEWS = 5   # below this, we don't give a verdict

VERDICT_NOTE = {
    "Worth buying": "Most reviewers are happy and few report problems.",
    "Mixed": "Opinions are split, so read the complaints before you decide.",
    "Think twice": "Many reviewers report problems or rate it low.",
    "Not enough data": "There are too few reviews to judge this product.",
}


def query(sql, params=()):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_verdict(n, pos, neg, rating):
    """Simple, explainable rule based on review sentiment and the product's average rating."""
    if n < MIN_REVIEWS:
        return "Not enough data", "grey"
    pos_share, neg_share = pos / n, neg / n
    if (rating is not None and rating < 3.5) or pos_share < 0.55 or neg_share >= 0.30:
        return "Think twice", "bad"
    if pos_share >= 0.75 and neg_share <= 0.15 and (rating is None or rating >= 4.0):
        return "Worth buying", "good"
    return "Mixed", "warn"


HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Should I buy it?</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
 :root{--ink:#1d2433;--muted:#5b6475;--line:#dfe3ea;--page:#f3f5f8;--surface:#fff;--brand:#16324f;
       --accent:#f28c1c;--good:#177a45;--warn:#b36200;--bad:#c0282d;--grey:#5f6877}
 *{box-sizing:border-box}
 body{margin:0;background:var(--page);color:var(--ink);line-height:1.5;
      font-family:"Plus Jakarta Sans","Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif}
 a{color:inherit}
 :focus-visible{outline:3px solid #2f6fed;outline-offset:2px}
 .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

 /* header + search */
 .top{background:var(--brand);color:#fff}
 .top .inner{max-width:1100px;margin:0 auto;padding:12px 16px;display:flex;flex-wrap:wrap;align-items:center;gap:12px}
 .brand{font-weight:800;font-size:20px;text-decoration:none;color:#fff;margin-right:8px}
 .search{flex:1 1 320px;display:flex;gap:8px;min-width:0}
 .search input{flex:1;min-width:0;height:46px;padding:0 14px;font-size:16px;border:0;border-radius:10px;color:var(--ink)}
 .search button{height:46px;padding:0 22px;font-size:16px;font-weight:700;border:0;border-radius:10px;
                background:var(--accent);color:var(--ink);cursor:pointer}
 .top.hero .inner{flex-direction:column;align-items:center;text-align:center;padding:24px 16px 48px;gap:10px}
 .top.hero .brand{align-self:flex-start;margin:0 0 24px}
 .top.hero h1{font-size:clamp(28px,5vw,42px);line-height:1.15;margin:0;max-width:22ch}
 .top.hero p{margin:0;color:#cfd8e6;max-width:46ch}
 .top.hero .search{width:100%;max-width:640px;flex:none;margin-top:12px}
 .top.hero .search input{height:56px;font-size:18px}
 .top.hero .search button{height:56px;padding:0 28px}

 /* page body */
 .wrap{max-width:1100px;margin:0 auto;padding:20px 16px 40px}
 .muted{color:var(--muted)}
 .count{margin:0 0 14px;color:var(--muted)}
 .cats{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}
 .cats a{padding:10px 16px;background:var(--surface);border:1px solid var(--line);border-radius:999px;
         text-decoration:none;font-weight:600}
 .cats a:hover{border-color:var(--brand)}

 /* product grid */
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;list-style:none;margin:0;padding:0}
 .card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px;
       display:flex;flex-direction:column;gap:8px;height:100%}
 .card:hover{border-color:var(--brand)}
 .card a.title{font-weight:700;text-decoration:none;display:-webkit-box;-webkit-line-clamp:3;
               -webkit-box-orient:vertical;overflow:hidden}
 .card a.title::after{content:"";position:absolute;inset:0}
 .rating{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--muted)}
 .stars{--r:0%;display:inline-block;font-size:17px;line-height:1;letter-spacing:2px;
        background:linear-gradient(90deg,#f5a623 var(--r),#d5d9e0 var(--r));
        -webkit-background-clip:text;background-clip:text;color:transparent}
 .price{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
 .price .now{font-size:20px;font-weight:800}
 .price .was{color:var(--muted);text-decoration:line-through;font-size:14px}
 .price .off{color:var(--good);font-weight:700;font-size:14px}
 .pill{display:inline-block;padding:4px 12px;border-radius:999px;color:#fff;font-weight:700;font-size:14px;
       align-self:flex-start;margin-top:auto}
 .pill.big{font-size:22px;padding:8px 20px;margin-top:0}
 .good{background:var(--good)}.warn{background:var(--warn)}.bad{background:var(--bad)}.grey{background:var(--grey)}

 /* product page */
 .detail{display:grid;grid-template-columns:1.2fr 1fr;gap:14px}
 .split{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
 @media (max-width:760px){.detail,.split{grid-template-columns:1fr}}
 .panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px}
 .panel h2{margin:0 0 8px;font-size:clamp(19px,3vw,24px);line-height:1.3}
 .panel h3{margin:0 0 10px;font-size:18px}
 .btn{display:inline-block;margin-top:14px;padding:10px 16px;border:1px solid var(--line);border-radius:10px;
      text-decoration:none;font-weight:600}
 .bar{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:14px 0 8px;background:var(--line)}
 .legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px}
 .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
 .chips{display:flex;flex-wrap:wrap;gap:8px}
 .chip{padding:4px 12px;border-radius:999px;font-size:14px;font-weight:600}
 .chip.like{background:#e3f4ea;color:#11592f}.chip.dislike{background:#fbe6e6;color:#8f1d21}
 blockquote.quote{margin:12px 0 0;padding:10px 12px;border-left:4px solid var(--line);background:#f7f8fa;
                  border-radius:0 8px 8px 0;font-size:15px}
 .empty{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px}
 .src{align-self:flex-start;font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:1px 8px}
 .foot{max-width:1100px;margin:0 auto;padding:0 16px 32px;color:var(--muted);font-size:13px}
</style></head><body>
<header class="top{% if hero %} hero{% endif %}"><div class="inner">
  <a class="brand" href="/">Should I buy it?</a>
  {% if hero %}
    <h1>Check what buyers say before you buy</h1>
    <p>Search a product to see what other customers liked and what they complained about.</p>
  {% endif %}
  <form class="search" action="/" method="get" role="search">
    <label class="sr" for="q">Search products</label>
    <input id="q" type="search" name="q" value="{{ q }}" placeholder="Search products, e.g. headphones" autocomplete="off"{% if hero %} autofocus{% endif %}>
    <button type="submit">Search</button>
  </form>
</div></header>
<main class="wrap">
"""
TAIL = """</main>
<footer class="foot">Reviews come from public Amazon and Flipkart product datasets. Sentiment is scored automatically, so treat verdicts as guidance.</footer>
</body></html>"""

STARS = """<span class="stars" role="img" aria-label="Rated {{ X['rating'] }} out of 5"
 style="--r:{{ (X['rating'] / 5 * 100)|round|int }}%">&#9733;&#9733;&#9733;&#9733;&#9733;</span>"""

HOME = HEAD + """
{% if hero %}
  <p class="muted">Or browse a category</p>
  <div class="cats">
    {% for c in categories %}<a href="/?q={{ c['main_category']|urlencode }}">{{ c['main_category']|nice }}</a>{% endfor %}
  </div>
{% elif cards %}
  <p class="count">{{ cards|length }} product{{ '' if cards|length == 1 else 's' }} for "{{ q }}"</p>
  <ul class="grid">
  {% for X in cards %}
    <li class="card">
      {% if X['source'] %}<span class="src">{{ X['source'] }}</span>{% endif %}
      <a class="title" href="/product/{{ X['product_id'] }}">{{ X['product_name'] }}</a>
      {% if X['rating'] %}
        <div class="rating">""" + STARS + """ <span>{{ X['rating'] }}</span></div>
      {% endif %}
      {% if X['discounted_price'] %}
        <div class="price">
          <span class="now">&#8377;{{ '{:,.0f}'.format(X['discounted_price']) }}</span>
          {% if X['actual_price'] %}<span class="was">&#8377;{{ '{:,.0f}'.format(X['actual_price']) }}</span>{% endif %}
          {% if X['discount_percentage'] %}<span class="off">{{ X['discount_percentage'] }}% off</span>{% endif %}
        </div>
      {% endif %}
      <span class="pill {{ X['colour'] }}">{{ X['verdict'] }}</span>
    </li>
  {% endfor %}
  </ul>
{% else %}
  <div class="empty">
    <strong>No products match "{{ q }}".</strong>
    <p class="muted">Try a shorter word, like "cable" instead of "usb cable 2m", or pick a category from the home page.</p>
  </div>
{% endif %}
""" + TAIL

PRODUCT = HEAD + """
<div class="detail">
  <section class="panel">
    <h2>{{ p['product_name'] }}</h2>
    {% if p['source'] %}<div class="muted">Reviews from {{ p['source'] }}</div>{% endif %}
    {% if p['rating'] %}
      {% set X = p %}
      <div class="rating">""" + STARS + """ <span>{{ p['rating'] }} out of 5</span></div>
    {% endif %}
    {% if p['discounted_price'] %}
      <div class="price" style="margin-top:8px">
        <span class="now">&#8377;{{ '{:,.0f}'.format(p['discounted_price']) }}</span>
        {% if p['actual_price'] %}<span class="was">&#8377;{{ '{:,.0f}'.format(p['actual_price']) }}</span>{% endif %}
        {% if p['discount_percentage'] %}<span class="off">{{ p['discount_percentage'] }}% off</span>{% endif %}
      </div>
    {% endif %}
    {% if p['product_link'] %}
      <a class="btn" href="{{ p['product_link'] }}" target="_blank" rel="noopener noreferrer">View the listing</a>
    {% endif %}
  </section>

  <section class="panel">
    <span class="pill big {{ colour }}">{{ verdict }}</span>
    <p>{{ note }}</p>
    {% if n >= min_reviews %}
      <div class="bar" role="img" aria-label="{{ pct['positive'] }}% positive, {{ pct['neutral'] }}% neutral, {{ pct['negative'] }}% negative">
        <div style="width:{{ pct['positive'] }}%;background:var(--good)"></div>
        <div style="width:{{ pct['neutral'] }}%;background:#9ca3af"></div>
        <div style="width:{{ pct['negative'] }}%;background:var(--bad)"></div>
      </div>
      <div class="legend">
        <span><i class="sw" style="background:var(--good)"></i>Positive {{ pct['positive'] }}%</span>
        <span><i class="sw" style="background:#9ca3af"></i>Neutral {{ pct['neutral'] }}%</span>
        <span><i class="sw" style="background:var(--bad)"></i>Negative {{ pct['negative'] }}%</span>
      </div>
      <p class="muted" style="margin-bottom:0">Based on {{ n }} customer reviews. This is guidance from past reviews, not a guarantee.</p>
    {% else %}
      <p class="muted" style="margin-bottom:0">Only {{ n }} review{{ '' if n == 1 else 's' }} available.</p>
    {% endif %}
  </section>
</div>

{% if n >= min_reviews %}
<div class="split">
  <section class="panel">
    <h3>What buyers like</h3>
    {% if praise %}<div class="chips">{% for t in praise %}<span class="chip like">{{ t|capitalize }}</span>{% endfor %}</div>
    {% elif not good_snips %}<p class="muted">No clear theme in the positive reviews.</p>{% endif %}
    {% for s in good_snips %}<blockquote class="quote">{{ s }}</blockquote>{% endfor %}
  </section>
  <section class="panel">
    <h3>What buyers complain about</h3>
    {% if complaints %}<div class="chips">{% for t in complaints %}<span class="chip dislike">{{ t|capitalize }}</span>{% endfor %}</div>
    {% elif not bad_snips %}<p class="muted">No complaints found.</p>{% endif %}
    {% for s in bad_snips %}<blockquote class="quote">{{ s }}</blockquote>{% endfor %}
  </section>
</div>
{% endif %}
""" + TAIL


@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    if not q:
        categories = query("""SELECT main_category, COUNT(*) AS c FROM products
                              WHERE main_category != '' GROUP BY main_category
                              ORDER BY c DESC LIMIT 8""")
        return render_template_string(HOME, q="", hero=True, categories=categories, cards=[])

    words = q.split()[:6]
    where = " AND ".join(["(p.product_name LIKE ? OR p.full_category LIKE ?)"] * len(words))
    params = []
    for w in words:
        params += [f"%{w}%", f"%{w}%"]
    rows = query(f"""
        SELECT * FROM (
            SELECT p.product_id, p.product_name, p.rating, p.discounted_price, p.actual_price,
                   p.discount_percentage, p.source, p.rating_count,
                   COUNT(a.review_id) AS n,
                   SUM(CASE WHEN a.sentiment = 'positive' THEN 1 ELSE 0 END) AS pos,
                   SUM(CASE WHEN a.sentiment = 'negative' THEN 1 ELSE 0 END) AS neg,
                   ROW_NUMBER() OVER (PARTITION BY p.source
                                      ORDER BY COUNT(a.review_id) DESC, p.rating_count DESC) AS rk
            FROM products p
            LEFT JOIN reviews r ON r.product_id = p.product_id
            LEFT JOIN review_analysis a ON a.review_id = r.review_id
            WHERE {where}
            GROUP BY p.product_id
        )
        ORDER BY rk, source
        LIMIT 24""", params)

    cards = []
    for r in rows:
        verdict, colour = get_verdict(r["n"], r["pos"] or 0, r["neg"] or 0, r["rating"])
        cards.append({**dict(r), "verdict": verdict, "colour": colour})
    return render_template_string(HOME, q=q, hero=False, categories=[], cards=cards)


@app.route("/product/<product_id>")
def product(product_id):
    rows = query("SELECT * FROM products WHERE product_id = ?", (product_id,))
    if not rows:
        abort(404)
    p = rows[0]

    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for row in query("""SELECT a.sentiment, COUNT(*) AS c FROM review_analysis a
                        JOIN reviews r ON r.review_id = a.review_id
                        WHERE r.product_id = ? GROUP BY a.sentiment""", (product_id,)):
        counts[row["sentiment"]] = row["c"]
    n = sum(counts.values())
    pct = {k: round(100 * v / n) if n else 0 for k, v in counts.items()}
    verdict, colour = get_verdict(n, counts["positive"], counts["negative"], p["rating"])
    note = VERDICT_NOTE[verdict]
    if verdict == "Mixed" and counts["positive"] / n >= 0.75 and p["rating"] is not None and p["rating"] < 4.0:
        note = "Most reviewers are positive, but the average rating is below 4 out of 5."

    def top_themes(sentiment):
        rows = query("""SELECT a.theme, COUNT(*) AS c FROM review_analysis a
                        JOIN reviews r ON r.review_id = a.review_id
                        WHERE r.product_id = ? AND a.sentiment = ? AND a.theme != 'other'
                        GROUP BY a.theme ORDER BY c DESC LIMIT 3""", (product_id, sentiment))
        return [r["theme"] for r in rows]

    def snippets(sentiment, order):
        base = """SELECT r.review_content FROM review_analysis a
                  JOIN reviews r ON r.review_id = a.review_id
                  WHERE r.product_id = ? AND a.sentiment = ? {extra}
                  ORDER BY a.sentiment_score {order} LIMIT 2"""
        # prefer short, clear reviews; fall back to any review if there are none
        rows = query(base.format(extra="AND LENGTH(r.review_content) BETWEEN 20 AND 220", order=order),
                     (product_id, sentiment))
        if not rows:
            rows = query(base.format(extra="", order=order), (product_id, sentiment))
        return [(r["review_content"][:220] + ("..." if len(r["review_content"]) > 220 else "")) for r in rows]

    return render_template_string(
        PRODUCT, q="", hero=False, p=p, n=n, pct=pct, verdict=verdict, colour=colour,
        note=note, min_reviews=MIN_REVIEWS,
        praise=top_themes("positive"), complaints=top_themes("negative"),
        good_snips=snippets("positive", "DESC"), bad_snips=snippets("negative", "ASC"))


if __name__ == "__main__":
    app.run(debug=True)