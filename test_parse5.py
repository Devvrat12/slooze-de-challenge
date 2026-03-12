from bs4 import BeautifulSoup

with open("data/alibaba_selenium2.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

cards = soup.find_all("div", class_="gallery-card-layout-info")
print(f"Found {len(cards)} product cards\n")

for card in cards[:3]:
    print("=" * 50)
    for el in card.find_all(True):
        text = el.get_text(strip=True)
        classes = el.get("class", [])
        if text and len(text) < 150 and classes:
            print(f"  Classes: {classes}")
            print(f"  Text   : {text[:100]}")
            print()
