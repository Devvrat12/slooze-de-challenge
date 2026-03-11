import seaborn as sns
import matplotlib.pyplot as plt
import re
import logging
import warnings
from collections import Counter
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Save to file instead of opening a window

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EDA")

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
COLORS = {"IndiaMART": "#FF6B35", "Alibaba": "#1890FF"}
OUTPUT_DIR = Path("data/eda_report")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_fig(name: str):
    path = OUTPUT_DIR / f"{name}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved chart: {path}")


def load_data(csv_path: str = "data/combined_cleaned.csv") -> pd.DataFrame:
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Cleaned data not found at '{csv_path}'.\n"
            "Run main.py first to scrape and clean data."
        )
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} records")
    return df


def print_overview(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("  DATASET OVERVIEW")
    print("=" * 60)
    print(f"  Total records     : {len(df):,}")
    print(f"  Columns           : {len(df.columns)}")
    print(f"  Sources           : {df['source'].value_counts().to_dict()}")
    print(f"  Categories        : {df['category'].nunique()} unique")
    print(f"  Countries         : {df['country'].nunique()} unique")
    print(f"  Avg quality score : {df['data_quality_score'].mean():.1%}")

    print("\n  Price summary (USD):")
    for stat, val in df["price_midpoint"].dropna().describe().items():
        print(f"    {stat:6s}: ${val:,.2f}")

    print("\n  Supplier rating summary:")
    for stat, val in df["supplier_rating"].dropna().describe().items():
        print(f"    {stat:6s}: {val:.2f}")
    print("=" * 60 + "\n")


def plot_source_distribution(df: pd.DataFrame):
    counts = df["source"].value_counts()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Source Distribution: IndiaMART vs Alibaba",
                 fontweight="bold")

    colors = [COLORS.get(s, "#999") for s in counts.index]
    axes[0].bar(counts.index, counts.values, color=colors, width=0.5)
    axes[0].set_title("Product Count by Source")
    axes[0].set_ylabel("Count")
    for i, (idx, val) in enumerate(counts.items()):
        axes[0].text(i, val + 1, str(val), ha="center", fontweight="bold")

    axes[1].pie(counts.values, labels=counts.index, autopct="%1.1f%%",
                colors=colors, startangle=140,
                wedgeprops=dict(edgecolor="white"))
    axes[1].set_title("Share of Listings")
    plt.tight_layout()
    save_fig("01_source_distribution")


def plot_category_distribution(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("Electronics Category Distribution", fontweight="bold")

    cat_counts = df["category"].value_counts()
    axes[0].barh(cat_counts.index, cat_counts.values,
                 color=sns.color_palette("muted", len(cat_counts)))
    axes[0].set_title("Overall Category Count")
    axes[0].set_xlabel("Listings")

    pivot = df.groupby(["category", "source"]).size().unstack(fill_value=0)
    pivot.plot(kind="barh", ax=axes[1],
               color=[COLORS.get(c, "#999") for c in pivot.columns])
    axes[1].set_title("Category Count by Source")
    axes[1].set_xlabel("Listings")
    plt.tight_layout()
    save_fig("02_category_distribution")


def plot_price_distribution(df: pd.DataFrame):
    price_df = df.dropna(subset=["price_midpoint"])
    p95 = price_df["price_midpoint"].quantile(0.95)
    price_df = price_df[price_df["price_midpoint"] <= p95]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Price Distribution (USD, excl. top 5% outliers)",
                 fontweight="bold")

    axes[0, 0].hist(price_df["price_midpoint"], bins=40,
                    color="#4C72B0", edgecolor="white")
    axes[0, 0].set_title("Overall Price Distribution")
    axes[0, 0].set_xlabel("Price (USD)")

    for src, grp in price_df.groupby("source"):
        grp["price_midpoint"].plot.kde(ax=axes[0, 1], label=src,
                                       color=COLORS.get(src, "#999"), linewidth=2)
    axes[0, 1].set_title("Price Density by Source")
    axes[0, 1].legend()

    price_df.boxplot(column="price_midpoint", by="category",
                     ax=axes[1, 0], vert=False)
    axes[1, 0].set_title("Price Range by Category")
    axes[1, 0].set_xlabel("Price (USD)")
    plt.sca(axes[1, 0])
    plt.title("Price Range by Category")

    axes[1, 1].hist(price_df[price_df["price_midpoint"] > 0]["price_midpoint"],
                    bins=40, color="#DD8452", edgecolor="white")
    axes[1, 1].set_xscale("log")
    axes[1, 1].set_title("Price Distribution (Log Scale)")
    axes[1, 1].set_xlabel("Price USD (log)")

    plt.tight_layout()
    save_fig("03_price_distribution")


def plot_price_by_category(df: pd.DataFrame):
    price_df = df.dropna(subset=["price_midpoint", "category", "source"])
    p95 = price_df["price_midpoint"].quantile(0.95)
    price_df = price_df[price_df["price_midpoint"] <= p95]

    fig, ax = plt.subplots(figsize=(14, 7))
    sns.boxplot(data=price_df, x="category", y="price_midpoint",
                hue="source", palette=COLORS, ax=ax)
    ax.set_title(
        "Price Comparison: IndiaMART vs Alibaba by Category", fontweight="bold")
    ax.set_xlabel("Category")
    ax.set_ylabel("Price (USD)")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    save_fig("04_price_by_category")


def plot_supplier_geography(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("Supplier Geography", fontweight="bold")

    country_counts = df["country"].value_counts().head(12)
    axes[0].barh(country_counts.index[::-1], country_counts.values[::-1],
                 color=sns.color_palette("Set2", len(country_counts)))
    axes[0].set_title("Top Supplier Countries")
    axes[0].set_xlabel("Listings")

    city_counts = df["city"].value_counts().head(15)
    axes[1].barh(city_counts.index[::-1], city_counts.values[::-1],
                 color=sns.color_palette("Set3", len(city_counts)))
    axes[1].set_title("Top 15 Supplier Cities")
    axes[1].set_xlabel("Listings")
    plt.tight_layout()
    save_fig("05_supplier_geography")


def plot_moq_analysis(df: pd.DataFrame):
    moq_df = df.dropna(subset=["moq_numeric"])
    moq_df = moq_df[moq_df["moq_numeric"] <=
                    moq_df["moq_numeric"].quantile(0.95)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Minimum Order Quantity (MOQ) Analysis", fontweight="bold")

    axes[0].hist(moq_df["moq_numeric"], bins=30,
                 color="#55A868", edgecolor="white")
    axes[0].set_title("MOQ Distribution")
    axes[0].set_xlabel("MOQ (units)")

    sns.boxplot(data=moq_df, x="source", y="moq_numeric",
                palette=COLORS, ax=axes[1])
    axes[1].set_title("MOQ by Source")
    axes[1].set_ylabel("MOQ (units)")
    plt.tight_layout()
    save_fig("06_moq_analysis")


def plot_rating_analysis(df: pd.DataFrame):
    rating_df = df.dropna(subset=["supplier_rating"])

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Supplier Rating Analysis", fontweight="bold")

    axes[0].hist(rating_df["supplier_rating"], bins=20,
                 color="#C44E52", edgecolor="white")
    axes[0].set_title("Rating Distribution")
    axes[0].set_xlabel("Rating")

    sns.violinplot(data=rating_df, x="source", y="supplier_rating",
                   palette=COLORS, ax=axes[1])
    axes[1].set_title("Rating by Source")

    axes[2].scatter(rating_df["supplier_rating"], rating_df["review_count"],
                    alpha=0.4, color="#8172B3", edgecolors="none")
    axes[2].set_title("Rating vs Review Count")
    axes[2].set_xlabel("Rating")
    axes[2].set_ylabel("Reviews")
    plt.tight_layout()
    save_fig("07_rating_analysis")


def plot_data_quality(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Data Quality Audit", fontweight="bold")

    key_cols = [c for c in ["product_name", "price_min", "price_max",
                            "supplier_name", "supplier_location",
                            "supplier_rating", "moq", "review_count"]
                if c in df.columns]
    missing = df[key_cols].isnull().mean() * 100
    axes[0].barh(missing.index, missing.values, color="#DD8452")
    axes[0].set_title("Missing Values per Column (%)")
    axes[0].set_xlabel("Missing (%)")
    for i, v in enumerate(missing.values):
        axes[0].text(v + 0.3, i, f"{v:.1f}%", va="center")

    axes[1].hist(df["data_quality_score"], bins=10,
                 color="#4C72B0", edgecolor="white")
    axes[1].set_title("Data Quality Score Distribution")
    axes[1].set_xlabel("Score (0–1)")
    plt.tight_layout()
    save_fig("08_data_quality")


def plot_keyword_frequency(df: pd.DataFrame):
    STOPWORDS = {"the", "and", "for", "with", "in", "of", "a", "an",
                 "to", "at", "by", "on", "is", "na", "pcs", "set", "n"}
    all_words = []
    for name in df["product_name"].dropna():
        words = re.findall(r"[a-zA-Z]{3,}", str(name).lower())
        all_words.extend([w for w in words if w not in STOPWORDS])

    top_words = Counter(all_words).most_common(25)
    if not top_words:
        return
    words, counts = zip(*top_words)

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.barh(list(words)[::-1], list(counts)[::-1],
            color=sns.color_palette("Blues_d", len(words)))
    ax.set_title("Top 25 Keywords in Product Names", fontweight="bold")
    ax.set_xlabel("Frequency")
    plt.tight_layout()
    save_fig("09_keyword_frequency")


def plot_price_vs_moq(df: pd.DataFrame):
    scatter_df = df.dropna(subset=["price_midpoint", "moq_numeric"])
    p95_price = scatter_df["price_midpoint"].quantile(0.95)
    p95_moq = scatter_df["moq_numeric"].quantile(0.95)
    scatter_df = scatter_df[
        (scatter_df["price_midpoint"] <= p95_price) &
        (scatter_df["moq_numeric"] <= p95_moq)
    ]

    fig, ax = plt.subplots(figsize=(12, 7))
    for src, grp in scatter_df.groupby("source"):
        ax.scatter(grp["moq_numeric"], grp["price_midpoint"],
                   label=src, alpha=0.5,
                   color=COLORS.get(src, "#999"), edgecolors="none", s=40)
    ax.set_title("Price vs MOQ by Source", fontweight="bold")
    ax.set_xlabel("Minimum Order Quantity")
    ax.set_ylabel("Price (USD)")
    ax.legend(title="Source")
    plt.tight_layout()
    save_fig("10_price_vs_moq")


# ── Insight Summary ────────────────────────────────────────────────────────────

def print_insights(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("  KEY INSIGHTS")
    print("=" * 60)

    for src, val in df.groupby("source")["price_midpoint"].median().items():
        print(f"  Median price on {src}: ${val:.2f}")

    cheapest = df.groupby("category")["price_midpoint"].median().idxmin()
    priciest = df.groupby("category")["price_midpoint"].median().idxmax()
    print(f"  Cheapest category : {cheapest}")
    print(f"  Priciest category : {priciest}")

    print(f"  Top supplier country : {df['country'].value_counts().idxmax()}")
    print(f"  Top supplier city    : {df['city'].value_counts().idxmax()}")

    if df["moq_numeric"].notna().any():
        for src, val in df.groupby("source")["moq_numeric"].median().items():
            print(f"  Median MOQ on {src}: {val:.0f} units")

    if df["supplier_rating"].notna().any():
        for src, val in df.groupby("source")["supplier_rating"].mean().items():
            print(f"  Avg rating on {src}: {val:.2f}")

    low_q = (df["data_quality_score"] < 0.5).sum()
    print(f"  Low quality records  : {low_q} ({low_q/len(df):.1%})")
    print("=" * 60 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def run_eda(csv_path: str = "data/combined_cleaned.csv"):
    df = load_data(csv_path)
    print_overview(df)

    logger.info("Generating charts...")
    plot_source_distribution(df)
    plot_category_distribution(df)
    plot_price_distribution(df)
    plot_price_by_category(df)
    plot_supplier_geography(df)
    plot_moq_analysis(df)
    plot_rating_analysis(df)
    plot_data_quality(df)
    plot_keyword_frequency(df)
    plot_price_vs_moq(df)

    print_insights(df)
    logger.info(f"EDA complete! All charts saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    run_eda()
