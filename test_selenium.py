from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Auto downloads the correct ChromeDriver for your Chrome version
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

url = "https://www.alibaba.com/trade/search?SearchText=smartphones+wholesale"
driver.get(url)

# Wait up to 10 seconds for products to load
time.sleep(5)

# Save the page
with open("data/alibaba_selenium.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

soup = BeautifulSoup(driver.page_source, "lxml")
print("Title:", driver.title)
print("\nAll div classes found:")
classes_found = set()
for div in soup.find_all("div", class_=True):
    for c in div.get("class", []):
        classes_found.add(c)
for c in sorted(classes_found)[:60]:
    print(" ", c)

driver.quit()
print("\nDone! Check data/alibaba_selenium.html in your browser")
