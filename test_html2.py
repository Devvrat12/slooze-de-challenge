from bs4 import BeautifulSoup

with open("data/alibaba_test.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Print all div classes to see what's actually in the page
print("=== BODY TEXT (first 1000 chars) ===")
print(soup.get_text()[:1000])

print("\n=== ALL DIV CLASSES FOUND ===")
classes_found = set()
for div in soup.find_all("div", class_=True):
    for c in div.get("class", []):
        classes_found.add(c)

for c in sorted(classes_found)[:50]:
    print(" ", c)
