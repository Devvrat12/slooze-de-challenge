from bs4 import BeautifulSoup

with open("data/alibaba_selenium.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Find product cards using the real class we discovered
cards = soup.find_all("div", class_=lambda c: c and "cardList--card--" in c)
print(f"Found {len(cards)} product cards\n")

for i, card in enumerate(cards[:3]):  # show first 3 only
    print(f"--- Product {i+1} ---")

    # Title
    title = card.find(class_=lambda c: c and "card_title" in str(c))
    print("Name   :", title.get_text(strip=True) if title else "N/A")

    # Price
    price = card.find(class_=lambda c: c and "price" in str(c).lower())
    print("Price  :", price.get_text(strip=True) if price else "N/A")

    # All text in card (fallback to see what's there)
    print("Text   :", card.get_text(separator=" | ", strip=True)[:200])
    print()
