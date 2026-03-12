from bs4 import BeautifulSoup

with open("data/alibaba_selenium.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Look for anything that contains a price symbol
print("=== ELEMENTS CONTAINING PRICES ===")
for el in soup.find_all(string=lambda t: t and "$" in t):
    parent = el.find_parent("div")
    if parent:
        classes = parent.get("class", [])
        print("Class:", classes)
        print("Text :", el.strip()[:100])
        print()

# Also print ALL unique class names containing common keywords
print("\n=== CLASSES WITH 'product' or 'offer' or 'item' ===")
for div in soup.find_all("div", class_=True):
    for c in div.get("class", []):
        if any(k in c.lower() for k in ["product", "offer", "item", "card"]):
            print(c)
