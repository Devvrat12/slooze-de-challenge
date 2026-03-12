from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://www.alibaba.com/trade/search?SearchText=smartphones+wholesale")

# Wait longer for JS to load products
print("Waiting for page to load...")
time.sleep(10)

# Scroll down to trigger lazy loading
driver.execute_script("window.scrollTo(0, 1000);")
time.sleep(3)
driver.execute_script("window.scrollTo(0, 2000);")
time.sleep(3)

soup = BeautifulSoup(driver.page_source, "lxml")

# Save updated HTML
with open("data/alibaba_selenium2.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

# Look for prices
prices = soup.find_all(string=lambda t: t and "$" in t)
print(f"\nFound {len(prices)} price-like elements")
for p in prices[:5]:
    print(" ", p.strip())

# Look for product titles — usually in h2 or anchor tags
print("\nFirst 5 anchor texts (possible product names):")
for a in soup.find_all("a", href=True)[:20]:
    text = a.get_text(strip=True)
    if len(text) > 20:
        print(" ", text[:100])

driver.quit()
print("\nDone!")
