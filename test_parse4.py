from bs4 import BeautifulSoup

with open("data/alibaba_selenium2.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Find elements containing prices
print("=== PRICE ELEMENTS ===")
for el in soup.find_all(string=lambda t: t and "$" in t and len(t.strip()) < 20):
    parent = el.find_parent("div")
    if parent:
        grandparent = parent.find_parent("div")
        print("Price text     :", el.strip())
        print("Parent classes :", parent.get("class", []))
        if grandparent:
            print("Grandp classes :", grandparent.get("class", []))
        print()

# Find supplier names
print("\n=== SUPPLIER ELEMENTS ===")
for el in soup.find_all(string=lambda t: t and "Co., Ltd" in t):
    parent = el.find_parent("div")
    if parent:
        print("Supplier       :", el.strip()[:80])
        print("Parent classes :", parent.get("class", []))
        print()
