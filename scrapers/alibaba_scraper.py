import re
import json
import logging
from pathlib import Path
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger("Alibaba")

BASE_URL = "https://www.alibaba.com"
SEARCH_URL = "https://www.alibaba.com/trade/search"

ELECTRONICS_QUERIES = [
    "smartphones wholesale",
    "LED TV supplier",
    "laptop wholesale electronics",
    "CCTV camera security system",
    "power bank bulk",
    "PCB printed circuit board manufacturer",
]


def _parse_price(raw: str):
    """Parse Alibaba price strings like '$5.00 - $12.00' or 'Contact Supplier'"""
    if not raw or "contact" in raw.lower():
        return None, None, "USD"
    raw = raw.replace(",", "")
    unit_match = re.search(r"/([\w\s]+)$", raw)
    unit = unit_match.group(1).strip() if unit_match else "Unit"
    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    price_min = float(numbers[0]) if len(numbers) >= 1 else None
    price_max = float(numbers[1]) if len(numbers) >= 2 else price_min
    return price_min, price_max, unit


class AlibabaScraper(BaseScraper):

    def __init__(self):
        # Alibaba is stricter — use longer delays
        super().__init__(source_name="Alibaba", min_delay=4.0, max_delay=9.0)

    def _build_search_url(self, query: str, page: int = 1) -> str:
        return (
            f"{SEARCH_URL}?SearchText={query.replace(' ', '+')}"
            f"&page={page}&IndexArea=product_en"
        )

    def _parse_search_page(self, soup, category_name: str) -> list:
        products = []

        cards = (
            soup.select("div.organic-list-offer-inner")
            or soup.select("div.m-gallery-product-item-v2")
            or soup.select("div[class*='offer-list-item']")
        )

        if not cards:
            logger.warning(f"No product cards found for '{category_name}'.")
            return products

        for card in cards:
            try:
                name_el = card.select_one(".elements-title-normal, .title, h2")
                price_el = card.select_one(
                    ".elements-offer-price-normal, .price")
                moq_el = card.select_one(
                    ".elements-offer-minOrderQuantity, .moq")
                supplier_el = card.select_one(".company-name, .supplier-name")
                loc_el = card.select_one(".location, .country")
                rating_el = card.select_one(".score-num, .rating")
                review_el = card.select_one(".feedback-num, .reviews")
                url_el = card.select_one("a[href]")

                raw_price = price_el.get_text(strip=True) if price_el else ""
                price_min, price_max, price_unit = _parse_price(raw_price)

                href = url_el["href"] if url_el else ""
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = BASE_URL + href

                products.append({
                    "product_name":      name_el.get_text(strip=True) if name_el else "N/A",
                    "category":          category_name,
                    "price_min":         price_min,
                    "price_max":         price_max,
                    "price_unit":        price_unit,
                    "currency":          "USD",
                    "moq":               moq_el.get_text(strip=True) if moq_el else "N/A",
                    "supplier_name":     supplier_el.get_text(strip=True) if supplier_el else "N/A",
                    "supplier_location": loc_el.get_text(strip=True) if loc_el else "N/A",
                    "supplier_rating":   float(re.sub(r"[^\d.]", "", rating_el.get_text()))
                                         if rating_el and rating_el.get_text(strip=True) else None,
                    "review_count":      int(re.sub(r"\D", "", review_el.get_text()))
                                         if review_el and review_el.get_text(strip=True) else 0,
                    "product_url":       href or "N/A",
                    "source":            "Alibaba",
                })

            except Exception as e:
                logger.debug(f"Skipped a card: {e}")
                continue

        logger.info(f"Parsed {len(products)} products for '{category_name}'")
        return products

    def scrape_query(self, query: str, pages: int = 3) -> list:
        all_products = []
        category_name = query.replace(
            " wholesale", "").replace(" supplier", "").title()

        for page in range(1, pages + 1):
            url = self._build_search_url(query, page)
            soup = self.fetch(url)
            if not soup:
                logger.warning(f"Stopping at page {page} for '{query}'")
                break
            products = self._parse_search_page(soup, category_name)
            if not products:
                break
            all_products.extend(products)

        return all_products

    def scrape(self, pages_per_query: int = 3) -> list:
        all_results = []
        logger.info(
            f"Starting Alibaba scrape — {len(ELECTRONICS_QUERIES)} queries")

        for query in ELECTRONICS_QUERIES:
            logger.info(f"Scraping: '{query}'")
            products = self.scrape_query(query, pages=pages_per_query)
            all_results.extend(products)

        logger.info(f"Alibaba done. Total: {len(all_results)} products")
        return all_results


if __name__ == "__main__":
    scraper = AlibabaScraper()
    data = scraper.scrape(pages_per_query=2)

    out_path = Path("data/alibaba_raw.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(data)} records to {out_path}")
