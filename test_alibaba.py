import json
import logging
from scrapers.alibaba_scraper import AlibabaScraper

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

scraper = AlibabaScraper()

# Test with just ONE query, ONE page
driver = scraper._make_driver()
try:
    products = scraper.scrape_query(driver, "smartphones wholesale", pages=1)
finally:
    driver.quit()

print(f"\nFound {len(products)} products\n")
for p in products[:3]:
    print("=" * 50)
    print("Name    :", p["product_name"][:80])
    print("Price   :", p["price_min"], "-", p["price_max"], "USD")
    print("MOQ     :", p["moq"])
    print("Supplier:", p["supplier_name"])
    print("Country :", p["supplier_location"])
    print("Rating  :", p["supplier_rating"], f"({p['review_count']} reviews)")
