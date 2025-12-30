#!/usr/bin/env python3
"""
Test script for Foot District Scraper
Tests the scraper with just a few products to verify functionality.
"""

import asyncio
import logging
from footdistrict_scraper import FootDistrictScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_scraper():
    """Test the scraper with a few products"""
    scraper = FootDistrictScraper()

    # Test URLs from the user
    test_product_urls = [
        "https://footdistrict.com/en/adidas-originals-womens-samba-og-ki6956.html",
        "https://footdistrict.com/en/asics-gel-1130-1203b045-020.html"
    ]

    logger = logging.getLogger(__name__)
    logger.info("Starting test scrape...")

    try:
        # Setup
        scraper.setup_driver()
        scraper.setup_embedding_model()

        # Test product scraping
        products = []
        for url in test_product_urls:
            logger.info(f"Testing product: {url}")
            product_data = scraper.scrape_product_page(url)
            if product_data:
                products.append(product_data)
                logger.info(f"Successfully scraped: {product_data['title']}")
                logger.info(f"Product data keys: {list(product_data.keys())}")
                logger.info(f"Price: {product_data.get('price')}, Currency: {product_data.get('currency')}")
                logger.info(f"Gender: {product_data.get('gender')}")
            else:
                logger.error(f"Failed to scrape: {url}")

        # Test database save
        if products:
            logger.info(f"Saving {len(products)} test products to database...")
            result = await scraper.save_to_supabase(products)
            if result:
                logger.info("Successfully saved test products!")
            else:
                logger.error("Failed to save test products")
        else:
            logger.warning("No products to save")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        if scraper.driver:
            scraper.driver.quit()

    logger.info("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_scraper())
