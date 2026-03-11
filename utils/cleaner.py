import re
import json
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger("Cleaner")

# INR to USD conversion rate (approximate)
INR_TO_USD = 0.012


def load_raw(path: str) -> list:
    p = Path(path)
    if not p.exists():
        logger.warning(f"File not found: {path}")
        return []
    with open(p) as f:
        return json.load(f)


def normalize_location(loc: str):
    """Extract city and country from messy location strings."""
    if not loc or loc == "N/A":
        return "Unknown", "Unknown"

    countries = ["China", "India", "Taiwan", "South Korea", "Japan",
                 "USA", "Germany", "Vietnam", "Bangladesh", "Pakistan"]
    country = "Unknown"
    for c in countries:
        if c.lower() in loc.lower():
            country = c
            break

    parts = [p.strip() for p in loc.split(",")]
    city = parts[0] if parts else "Unknown"
    return city, country


def _extract_moq_numeric(moq_str: str):
    """Extract first number from MOQ string."""
    nums = re.findall(r"\d+", str(moq_str))
    return float(nums[0]) if nums else None


def clean(df: pd.DataFrame) -> pd.DataFrame:

    # 1. Drop exact duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["product_name", "supplier_name", "source"])
    logger.info(f"Dropped {before - len(df)} duplicate rows")

    # 2. Normalize product names
    df["product_name"] = df["product_name"].str.strip().str.title()
    df["product_name"].replace("N/A", pd.NA, inplace=True)

    # 3. Convert all prices to USD
    mask_inr = df["currency"] == "INR"
    df.loc[mask_inr, "price_min"] = df.loc[mask_inr, "price_min"] * INR_TO_USD
    df.loc[mask_inr, "price_max"] = df.loc[mask_inr, "price_max"] * INR_TO_USD
    df["currency"] = "USD"

    # 4. Derived price columns
    df["price_midpoint"] = (df["price_min"] + df["price_max"]) / 2
    df["price_range_width"] = df["price_max"] - df["price_min"]

    # Flag outliers above 99th percentile
    p99 = df["price_midpoint"].quantile(0.99)
    df["is_price_outlier"] = df["price_midpoint"] > p99

    # 5. Normalize locations
    df[["city", "country"]] = df["supplier_location"].apply(
        lambda x: pd.Series(normalize_location(str(x)))
    )

    # 6. Clean MOQ
    df["moq"] = df["moq"].fillna("N/A").astype(str).str.strip()
    df["moq_numeric"] = df["moq"].apply(_extract_moq_numeric)

    # 7. Fix rating and review types
    df["supplier_rating"] = pd.to_numeric(
        df["supplier_rating"], errors="coerce")
    df["review_count"] = pd.to_numeric(
        df["review_count"], errors="coerce").fillna(0).astype(int)

    # 8. Data quality score (0 to 1) based on how many key fields are filled
    required = ["product_name", "price_midpoint",
                "supplier_name", "supplier_location"]
    df["data_quality_score"] = df[required].notna().sum(axis=1) / len(required)

    # 9. Final column ordering
    ordered_cols = [
        "source", "category", "product_name",
        "price_min", "price_max", "price_midpoint", "price_range_width",
        "price_unit", "currency", "is_price_outlier",
        "moq", "moq_numeric",
        "supplier_name", "supplier_location", "city", "country",
        "supplier_rating", "review_count",
        "product_url", "data_quality_score",
    ]
    df = df[[c for c in ordered_cols if c in df.columns]]
    return df


def run_cleaning(
    indiamart_path: str = "data/indiamart_raw.json",
    alibaba_path:   str = "data/alibaba_raw.json",
    output_path:    str = "data/combined_cleaned.csv",
) -> pd.DataFrame:

    logger.info("Loading raw data...")
    im_data = load_raw(indiamart_path)
    ali_data = load_raw(alibaba_path)

    logger.info(
        f"IndiaMART: {len(im_data)} records | Alibaba: {len(ali_data)} records")

    if not im_data and not ali_data:
        raise ValueError("No raw data found. Run scrapers first.")

    df = pd.DataFrame(im_data + ali_data)
    logger.info(f"Combined raw records: {len(df)}")

    df = clean(df)
    logger.info(f"Cleaned records: {len(df)}")

    Path(output_path).parent.mkdir(exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved cleaned data to {output_path}")

    print("\n📊 Data Quality Summary:")
    print(f"  Total records     : {len(df)}")
    print(f"  Sources           : {df['source'].value_counts().to_dict()}")
    print(f"  Categories        : {df['category'].nunique()}")
    print(f"  Avg quality score : {df['data_quality_score'].mean():.2%}")
    print(f"  Price outliers    : {df['is_price_outlier'].sum()}")
    print(f"  Missing prices    : {df['price_midpoint'].isna().sum()}")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    run_cleaning()
