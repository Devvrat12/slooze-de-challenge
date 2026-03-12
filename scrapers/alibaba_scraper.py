"""
alibaba_scraper.py
-------------------
Scrapes electronics product listings from Alibaba using Selenium.
Uses real class names discovered by inspecting live page structure.
"""

import re
import json
import logging
import time
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger("Alibaba")

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
    """Parse price strings like '$5.00 - $12.00' or '$650-1,480'"""
    if not raw or "contact" in raw.lower():
        return None, None
    raw = raw.replace(",", "").replace("$", "").strip()
    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    price_min = float(numbers[0]) if len(numbers) >= 1 else None
    price_max = float(numbers[1]) if len(numbers) >= 2 else price_min
    return price_min, price_max


def _parse_rating(raw: str):
    """Parse '4.5/5.0 (49)' into rating and review count."""
    if not raw:
        return None, 0
    rating_match = re.search(r"(\d+\.\d+)/5\.0", raw)
    review_match = re.search(r"\((\d+)\)", raw)
    rating = float(rating_match.group(1)) if rating_match else None
    reviews = int(review_match.group(1)) if review_match else 0
    return rating, reviews


def _parse_location(raw: str):
    """Extract country code from strings like '9 yrsCN' or '3 yrsIN'"""
    if not raw:
        return "Unknown"
    # Country codes at the end of the string
    match = re.search(r"[A-Z]{2}$", raw.strip())
    country_codes = {
        "CN": "China", "IN": "India", "TW": "Taiwan",
        "KR": "South Korea", "JP": "Japan", "DE": "Germany",
        "US": "USA", "VN": "Vietnam", "BD": "Bangladesh",
    }
    if match:
        code = match.group(0)
        return country_codes.get(code, code)
    return "Unknown"


class AlibabaScraper:

    def __init__(self):
        self.logger = logging.getLogger("Alibaba")

    def _make_driver(self):
        """Create a new Selenium Chrome driver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver

    def _build_url(self, query: str, page: int = 1) -> str:
        return (
            f"{SEARCH_URL}?SearchText={query.replace(' ', '+')}"
            f"&page={page}&IndexArea=product_en"
        )

    def _parse_page(self, html: str, category_name: str) -> list:
        products = []
        soup = BeautifulSoup(html, "lxml")

        cards = soup.find_all("div", class_="gallery-card-layout-info")
        if not cards:
            self.logger.warning(f"No cards found for '{category_name}'")
            return products

        for card in cards:
            try:
                # Title
                title_el = card.find(class_="search-card-e-title")

                # Price
                price_el = card.find(class_="search-card-e-price-main")

                # MOQ
                moq_el = card.find(class_="search-card-m-sale-features__item")

                # Supplier name
                supplier_el = card.find(class_="search-card-e-company")

                # Rating + reviews
                review_el = card.find(class_="search-card-e-review")

                # Location (supplier year + country)
                year_el = card.find(class_="search-card-e-supplier__year")

                # URL
                url_el = card.find_parent(
                    "div", class_=lambda c: c and "J-search-card-wrapper" in str(c))
                link = card.find("a", href=True)

                raw_price = price_el.get_text(strip=True) if price_el else ""
                price_min, price_max = _parse_price(raw_price)

                raw_review = review_el.get_text(
                    strip=True) if review_el else ""
                rating, review_count = _parse_rating(raw_review)

                raw_location = year_el.get_text(strip=True) if year_el else ""
                country = _parse_location(raw_location)

                href = link["href"] if link else "N/A"
                if href.startswith("//"):
                    href = "https:" + href

                moq_text = moq_el.get_text(strip=True) if moq_el else "N/A"
                # Clean MOQ: "Min. order: 3,000 pieces" → "3000 pieces"
                moq_clean = re.sub(r"Min\.\s*order:\s*", "",
                                   moq_text).replace(",", "")

                products.append({
                    "product_name":      title_el.get_text(strip=True) if title_el else "N/A",
                    "category":          category_name,
                    "price_min":         price_min,
                    "price_max":         price_max,
                    "price_unit":        "Unit",
                    "currency":          "USD",
                    "moq":               moq_clean,
                    "supplier_name":     supplier_el.get_text(strip=True) if supplier_el else "N/A",
                    "supplier_location": country,
                    "supplier_rating":   rating,
                    "review_count":      review_count,
                    "product_url":       href,
                    "source":            "Alibaba",
                })

            except Exception as e:
                self.logger.debug(f"Skipped card: {e}")
                continue

        self.logger.info(
            f"Parsed {len(products)} products for '{category_name}'")
        return products

    def scrape_query(self, driver, query: str, pages: int = 3) -> list:
        all_products = []
        category_name = (query
                         .replace(" wholesale", "")
                         .replace(" supplier", "")
                         .replace(" bulk", "")
                         .title())

        for page in range(1, pages + 1):
            url = self._build_url(query, page)
            self.logger.info(f"Fetching page {page}: {url}")
            driver.get(url)

            # Wait for products to load + scroll to trigger lazy loading
            time.sleep(6)
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 2000);")
            time.sleep(2)

            products = self._parse_page(driver.page_source, category_name)
            if not products:
                self.logger.warning(f"No products on page {page}, stopping.")
                break
            all_products.extend(products)
            self.logger.info(
                f"  Running total for '{category_name}': {len(all_products)}")

        return all_products

    def scrape(self, pages_per_query: int = 2) -> list:
        all_results = []
        self.logger.info(
            f"Starting Alibaba scrape — {len(ELECTRONICS_QUERIES)} queries")

        driver = self._make_driver()
        try:
            for query in ELECTRONICS_QUERIES:
                self.logger.info(f"Scraping: '{query}'")
                products = self.scrape_query(
                    driver, query, pages=pages_per_query)
                all_results.extend(products)
                # Pause between queries
                time.sleep(5)
        finally:
            driver.quit()

        self.logger.info(f"Alibaba done. Total: {len(all_results)} products")
        return all_results


# ── Run standalone ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = AlibabaScraper()
    data = scraper.scrape(pages_per_query=2)

    out_path = Path("data/alibaba_raw.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(data)} records to {out_path}")
