import re
import json
import logging
from pathlib import Path
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger("IndiaMART")

BASE_URL = "https://www.indiamart.com"

ELECTRONICS_CATEGORIES = [
    {"name": "Mobile Phones",     "path": "/proddetail/mobile-phones.html"},
    {"name": "LED TV",            "path": "/proddetail/led-tv.html"},
    {"name": "Laptops",           "path": "/proddetail/laptops.html"},
    {"name": "CCTV Camera",       "path": "/proddetail/cctv-camera.html"},
    {"name": "Power Bank",        "path": "/proddetail/power-bank.html"},
    {"name": "PCB Circuit Board", "path": "/proddetail/printed-circuit-board.html"},
]


def _parse_price(raw: str):
    """Extract min/max price from strings like '₹ 5,000 - ₹ 15,000 / Piece'"""
    if not raw:
        return None, None, ""
    raw = raw.replace(",", "").replace("₹", "").strip()
    unit_match = re.search(r"/([\w\s]+)$", raw)
    unit = unit_match.group(1).strip() if unit_match else "Unit"
    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    price_min = float(numbers[0]) if len(numbers) >= 1 else None
    price_max = float(numbers[1]) if len(numbers) >= 2 else price_min
    return price_min, price_max, unit


def _parse_moq(raw: str) -> str:
    """Extract MOQ from strings like 'Min. Order: 10 Piece'"""
    if not raw:
        return "N/A"
    match = re.search(r"(\d[\d,]*\s*\w+)", raw)
    return match.group(1).replace(",", "") if match else raw.strip()


class IndiaMARTScraper(BaseScraper):

    def __init__(self):
        super().__init__(source_name="IndiaMART", min_delay=3.0, max_delay=7.0)

    def _parse_listing_page(self, soup, category_name: str) -> list:
        products = []

        cards = soup.select(
            "div.prd-detail") or soup.select("div.product-list-item")

        if not cards:
            logger.warning(f"No product cards found for '{category_name}'.")
            return products

        for card in cards:
            try:
                name_el = card.select_one("a.prd-name, h2.lcname, .prd-title")
                price_el = card.select_one(".prc, .price, .prd-price")
                moq_el = card.select_one(".moq, .min-qty, .min-order")
                supplier_el = card.select_one(
                    ".lcname, .sup-name, .seller-name")
                loc_el = card.select_one(".lcadr, .loc, .city")
                rating_el = card.select_one(".star-val, .rating-value")
                review_el = card.select_one(".rating-count, .review-cnt")
                url_el = card.select_one("a[href]")

                raw_price = price_el.get_text(strip=True) if price_el else ""
                price_min, price_max, price_unit = _parse_price(raw_price)

                products.append({
                    "product_name":      name_el.get_text(strip=True) if name_el else "N/A",
                    "category":          category_name,
                    "price_min":         price_min,
                    "price_max":         price_max,
                    "price_unit":        price_unit,
                    "currency":          "INR",
                    "moq":               _parse_moq(moq_el.get_text() if moq_el else ""),
                    "supplier_name":     supplier_el.get_text(strip=True) if supplier_el else "N/A",
                    "supplier_location": loc_el.get_text(strip=True) if loc_el else "N/A",
                    "supplier_rating":   float(rating_el.get_text(strip=True)) if rating_el else None,
                    "review_count":      int(re.sub(r"\D", "", review_el.get_text())) if review_el else 0,
                    "product_url":       BASE_URL + url_el["href"] if url_el else "N/A",
                    "source":            "IndiaMART",
                })

            except Exception as e:
                logger.debug(f"Skipped a card: {e}")
                continue

        logger.info(f"Parsed {len(products)} products for '{category_name}'")
        return products

    def scrape_category(self, category: dict, pages: int = 3) -> list:
        all_products = []
        for page in range(1, pages + 1):
            url = BASE_URL + category["path"]
            params = {"page": page} if page > 1 else {}
            soup = self.fetch(url, params=params)
            if not soup:
                logger.warning(
                    f"Stopping at page {page} for {category['name']}")
                break
            products = self._parse_listing_page(soup, category["name"])
            if not products:
                break
            all_products.extend(products)
        return all_products

    def scrape(self, pages_per_category: int = 3) -> list:
        all_results = []
        logger.info(
            f"Starting IndiaMART scrape — {len(ELECTRONICS_CATEGORIES)} categories")

        for cat in ELECTRONICS_CATEGORIES:
            logger.info(f"Scraping: {cat['name']}")
            products = self.scrape_category(cat, pages=pages_per_category)
            all_results.extend(products)

        logger.info(f"IndiaMART done. Total: {len(all_results)} products")
        return all_results


if __name__ == "__main__":
    scraper = IndiaMARTScraper()
    data = scraper.scrape(pages_per_category=2)

    out_path = Path("data/indiamart_raw.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(data)} records to {out_path}")
