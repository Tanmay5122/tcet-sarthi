from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

options = Options()
options.add_argument('--headless')

driver = webdriver.Chrome(options=options)
driver.get("https://tcetcercd.in/")

html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')

# Print all divs with class names
divs = soup.find_all('div', limit=20)
for div in divs:
    classes = div.get('class', [])
    if classes:
        print(f"Class: {' '.join(classes)}")

driver.quit()