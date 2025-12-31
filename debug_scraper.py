#!/usr/bin/env python3
"""
Debug script to inspect Foot District page structure
Run this locally to see what the page actually contains
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def debug_page():
    """Debug the Foot District page structure"""
    print("Starting page inspection...")

    # Setup Chrome
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        url = "https://footdistrict.com/en/footwear/"
        print(f"Loading page: {url}")

        driver.get(url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        print("Page loaded successfully")

        # Scroll down to load products
        print("Scrolling down to load products...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Get page source
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Save debug HTML
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("Saved debug_page.html")

        # Analyze the page
        print("\nANALYZING PAGE STRUCTURE:")
        print("=" * 50)

        # Look for common product selectors
        selectors_to_check = [
            '.product-item',
            '.product-card',
            '.product',
            '[data-product]',
            '.item',
            'article',
            '.grid-item'
        ]

        print("Checking for product containers:")
        for selector in selectors_to_check:
            elements = soup.select(selector)
            print(f"  {selector}: {len(elements)} elements found")

        # Look for links
        print("\nChecking for links:")
        all_links = soup.find_all('a', href=True)
        product_links = [link for link in all_links if '.html' in link.get('href', '')]
        print(f"  Total links: {len(all_links)}")
        print(f"  .html links: {len(product_links)}")

        # Show sample product links
        print("\nSample product links (first 10):")
        for i, link in enumerate(product_links[:10]):
            href = link.get('href')
            text = link.get_text().strip()[:50]
            print(f"  {i+1}. {href} -> '{text}'")

        # Look for specific brands
        brand_patterns = ['adidas', 'nike', 'samba', 'air', 'jordan']
        print(f"\nChecking for brand mentions:")
        for brand in brand_patterns:
            brand_links = [link for link in all_links if brand.lower() in link.get('href', '').lower()]
            print(f"  {brand}: {len(brand_links)} links")

        # Check page title and basic info
        print(f"\nPage info:")
        print(f"  Title: {driver.title}")
        print(f"  URL: {driver.current_url}")
        print(f"  Page length: {len(driver.page_source)} characters")

    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()
        print("\nDebug complete! Check debug_page.html for full HTML source.")

if __name__ == "__main__":
    debug_page()
