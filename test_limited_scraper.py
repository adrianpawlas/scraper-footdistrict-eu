#!/usr/bin/env python3
"""
Test script to run the scraper with a limit
Run this locally to test with just a few products
"""

import asyncio
import logging
from footdistrict_scraper import FootDistrictScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_scraper.log'),
        logging.StreamHandler()
    ]
)

class LimitedFootDistrictScraper(FootDistrictScraper):
    def __init__(self, limit=5):
        super().__init__()
        self.limit = limit

    async def run_limited_scraper(self):
        """Run the scraper with a product limit"""
        logger = logging.getLogger(__name__)
        logger.info(f"Starting LIMITED scraper with limit of {self.limit} products...")

        # Setup
        self.setup_driver()
        self.setup_embedding_model()

        try:
            # Get category pages (just the first one for testing)
            category_urls = ["https://footdistrict.com/en/footwear/"]
            logger.info(f"Testing with {len(category_urls)} category page(s)")

            # Scrape product URLs from first category page
            all_product_urls = []
            for category_url in category_urls:
                product_urls = self.scrape_category_page(category_url)
                all_product_urls.extend(product_urls)
                break  # Only test first category page

            logger.info(f"Found {len(all_product_urls)} product URLs")

            # Limit to specified number
            if len(all_product_urls) > self.limit:
                all_product_urls = all_product_urls[:self.limit]
                logger.info(f"Limited to {len(all_product_urls)} products for testing")

            if not all_product_urls:
                logger.error("No product URLs found! Check debug_page.html for page structure.")
                return

            # Process limited products
            products = []
            for i, url in enumerate(all_product_urls):
                logger.info(f"Testing product {i+1}/{len(all_product_urls)}: {url}")
                product_data = self.scrape_product_page(url)
                if product_data:
                    products.append(product_data)
                    logger.info(f"Successfully scraped: {product_data.get('title', 'Unknown')}")
                else:
                    logger.warning(f"Failed to scrape: {url}")

            # Save test results
            if products:
                logger.info(f"Saving {len(products)} test products...")
                result = await self.save_to_supabase(products)
                if result:
                    logger.info("Test products saved successfully!")
                else:
                    logger.warning("Failed to save to Supabase, but products were extracted successfully")
            else:
                logger.error("No products were successfully scraped!")

        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)

        finally:
            if self.driver:
                self.driver.quit()

        logger.info("Limited test complete!")

async def main():
    """Run the limited test"""
    # Test with just 3 products
    scraper = LimitedFootDistrictScraper(limit=3)

    try:
        await scraper.run_limited_scraper()
        print("\n" + "="*50)
        print("TEST RESULTS:")
        print("- Check test_scraper.log for detailed logs")
        print("- Check debug_page.html for page structure")
        print("- If products were found and scraped, the scraper is working!")
        print("="*50)
    except KeyboardInterrupt:
        print("Test interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
