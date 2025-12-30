#!/usr/bin/env python3
"""
Foot District Scraper Runner
Run this script to start scraping Foot District products.
"""

import asyncio
import logging
from footdistrict_scraper import FootDistrictScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

async def main():
    """Main runner function"""
    scraper = FootDistrictScraper()

    try:
        await scraper.run_scraper_with_timeout()
        print("Scraping completed successfully!")
    except KeyboardInterrupt:
        print("Scraping interrupted by user")
    except Exception as e:
        print(f"Scraping failed with error: {e}")
        logging.error(f"Scraping failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
