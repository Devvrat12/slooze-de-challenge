import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

url = "https://www.alibaba.com/trade/search?SearchText=smartphones+wholesale"
r = requests.get(url, headers=headers, timeout=15)
print("Status:", r.status_code)

soup = BeautifulSoup(r.text, "lxml")

# Save full HTML to a file so we can inspect it
with open("data/alibaba_test.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())

print("HTML saved to data/alibaba_test.html")
print("Page title:", soup.title.text if soup.title else "No title found")
