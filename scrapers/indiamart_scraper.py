"""
indiamart_scraper.py
---------------------
Scrapes electronics listings from IndiaMART using Selenium.
CSS selectors verified against live page structure March 2026.
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

logger = logging.getLogger("IndiaMART")

ELECTRONICS_CATEGORIES = [
    {"name": "Mobile Phones",
        "url": "https://dir.indiamart.com/impcat/mobile-phones.html"},
    {"name": "LED TV",            "url": "https://dir.indiamart.com/impcat/led-tv.html"},
    {"name": "Laptops",           "url": "https://dir.indiamart.com/impcat/laptops.html"},
    {"name": "CCTV Camera",
        "url": "https://dir.indiamart.com/impcat/cctv-camera.html"},
    {"name": "Power Bank",
        "url": "https://dir.indiamart.com/impcat/power-banks.html"},
    {"name": "PCB Circuit Board",
        "url": "https://dir.indiamart.com/impcat/printed-circuit-board.html"},
]


def _parse_price(raw: str):
    """Extract price from strings like '₹ 2,500'"""
    if not raw or "ask" in raw.lower():
        return None, None
    raw = raw.replace(",", "").replace("₹", "").strip()
    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    price_min = float(numbers[0]) if numbers else None
    return price_min, price_min  # IndiaMART shows single price


def _parse_rating(raw: str):
    """Extract rating and review count from '4.1(645)'"""
    if not raw:
        return None, 0
    rating_match = re.search(r"(\d+\.\d+)", raw)
    review_match = re.search(r"\((\d+)\)", raw)
    rating = float(rating_match.group(1)) if rating_match else None
    reviews = int(review_match.group(1)) if review_match else 0
    return rating, reviews


def _make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


class IndiaMARTScraper:

    def __init__(self):
        self.logger = logging.getLogger("IndiaMART")

    def _parse_page(self, html: str, category_name: str) -> list:
        products = []
        soup = BeautifulSoup(html, "lxml")

        cards = soup.find_all("li", class_="temp4-card")
        if not cards:
            self.logger.warning(f"No cards found for '{category_name}'")
            return products

        for card in cards:
            try:
                # Product name
                name_el = card.find("a", class_="prdtitle")

                # Price
                price_el = card.find("span", class_="prc")
                unit_el = card.find("span", class_="prcut")

                # Supplier
                supplier_el = card.find("div", class_="wlc1")

                # Rating — span.b contains the number like "4.1"
                rating_el = card.find("span", class_="b")

                # Review count — div.dag5 contains "4.1(645)"
                review_el = card.find("div", class_="dag5")

                # URL
                url = name_el["href"] if name_el and name_el.get(
                    "href") else "N/A"

                # Parse price
                raw_price = price_el.get_text(strip=True) if price_el else ""
                price_min, price_max = _parse_price(raw_price)

                # Parse rating
                raw_review = review_el.get_text(
                    strip=True) if review_el else ""
                _, review_count = _parse_rating(raw_review)
                rating = float(rating_el.get_text(
                    strip=True)) if rating_el else None

                products.append({
                    "product_name":      name_el.get_text(strip=True) if name_el else "N/A",
                    "category":          category_name,
                    "price_min":         price_min,
                    "price_max":         price_max,
                    "price_unit":        unit_el.get_text(strip=True) if unit_el else "Unit",
                    "currency":          "INR",
                    "moq":               "N/A",
                    "supplier_name":     supplier_el.get_text(strip=True) if supplier_el else "N/A",
                    "supplier_location": "India",
                    "supplier_rating":   rating,
                    "review_count":      review_count,
                    "product_url":       url,
                    "source":            "IndiaMART",
                })

            except Exception as e:
                self.logger.debug(f"Skipped card: {e}")
                continue

        self.logger.info(
            f"Parsed {len(products)} products for '{category_name}'")
        return products

    def scrape_category(self, driver, category: dict) -> list:
        self.logger.info(f"Scraping: {category['name']}")
        driver.get(category["url"])
        time.sleep(4)
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 2000);")
        time.sleep(2)
        return self._parse_page(driver.page_source, category["name"])

    def scrape(self) -> list:
        all_results = []
        self.logger.info(
            f"Starting IndiaMART — {len(ELECTRONICS_CATEGORIES)} categories")

        driver = _make_driver()
        try:
            for cat in ELECTRONICS_CATEGORIES:
                products = self.scrape_category(driver, cat)
                all_results.extend(products)
                time.sleep(3)
        finally:
            driver.quit()

        self.logger.info(f"IndiaMART done. Total: {len(all_results)} products")
        return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = IndiaMARTScraper()
    data = scraper.scrape()

    out_path = Path("data/indiamart_raw.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(data)} records to {out_path}")
