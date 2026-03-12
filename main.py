import sys
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Main")


def main():
    print("\n" + "=" * 60)
    print("  Slooze Electronics Supplier Intelligence Pipeline")
    print("  By: Devvrat Tiwari")
    print("=" * 60 + "\n")

    Path("data").mkdir(exist_ok=True)

    logger.info("STEP 1: Scraping IndiaMART...")
    try:
        from scrapers.indiamart_scraper import IndiaMARTScraper
        im_data = IndiaMARTScraper().scrape(pages_per_category=3)
        with open("data/indiamart_raw.json", "w") as f:
            json.dump(im_data, f, indent=2, ensure_ascii=False)
        logger.info(f"IndiaMART: {len(im_data)} products saved")
    except Exception as e:
        logger.error(f"IndiaMART failed: {e}")
        with open("data/indiamart_raw.json", "w") as f:
            json.dump([], f)

    # ── Step 2: Alibaba ────────────────────────────────────────────
    logger.info("STEP 2: Scraping Alibaba...")
    try:
        from scrapers.alibaba_scraper import AlibabaScraper
        ali_scraper = AlibabaScraper()
        ali_data = ali_scraper.scrape(pages_per_query=2)
        with open("data/alibaba_raw.json", "w", encoding="utf-8") as f:
            json.dump(ali_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Alibaba: {len(ali_data)} products saved")
    except Exception as e:
        logger.error(f"Alibaba failed: {e}")
        with open("data/alibaba_raw.json", "w") as f:
            json.dump([], f)

    logger.info("STEP 3: Cleaning & Normalizing...")
    try:
        from utils.cleaner import run_cleaning
        df = run_cleaning(
            indiamart_path="data/indiamart_raw.json",
            alibaba_path="data/alibaba_raw.json",
            output_path="data/combined_cleaned.csv",
        )
        logger.info(f"Cleaned dataset: {len(df)} records")
    except Exception as e:
        logger.error(f"Cleaning failed: {e}")
        sys.exit(1)

    logger.info("STEP 4: Running EDA...")
    try:
        from eda.eda_analysis import run_eda
        run_eda(csv_path="data/combined_cleaned.csv")
    except Exception as e:
        logger.error(f"EDA failed: {e}")

    print("\n" + "=" * 60)
    print("  Pipeline Complete!")
    print("=" * 60)
    print("  data/indiamart_raw.json    — Raw IndiaMART data")
    print("  data/alibaba_raw.json      — Raw Alibaba data")
    print("  data/combined_cleaned.csv  — Cleaned merged dataset")
    print("  data/eda_report/*.png      — EDA charts")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
