import asyncio
import json
import logging
import re
import time
from io import BytesIO
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
import numpy as np
import requests
import torch
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client, Client
from transformers import AutoProcessor, AutoModel
from webdriver_manager.chrome import ChromeDriverManager

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, CATEGORY_URL, PRODUCT_URL_PATTERN, MAX_PAGES, REQUEST_DELAY, BATCH_SIZE, EMBEDDING_MODEL, EMBEDDING_DIM, BASE_URL, SOURCE, BRAND, SECOND_HAND, TIMEOUT_HOURS

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FootDistrictScraper:
    def __init__(self, limit=None):
        # Initialize Supabase client
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.supabase = None

        self.driver = None
        self.embedding_model = None
        self.processor = None
        self.processed_urls = set()
        self.limit = limit  # Maximum number of products to scrape

    def setup_driver(self):
        """Setup Chrome driver with advanced anti-detection measures"""
        options = Options()

        # Basic options
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # More realistic user agent (matching Windows since user is on Windows)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

        # Additional stealth options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")

        # Language and locale
        options.add_argument("--lang=en-US,en")
        options.add_argument("--accept-lang=en-US,en")

        # Disable various automation indicators
        options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2,  # Block images for speed
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
        })

        # Use service to specify driver path
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=options)

        # Execute anti-detection scripts
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Add more stealth
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        })

        # Set other navigator properties to look more human (Windows)
        stealth_js = """
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});

        // Override webdriver property more thoroughly
        delete window.navigator.__proto__.webdriver;

        // Add some realistic browser properties
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
        Object.defineProperty(navigator, 'cookieEnabled', {get: () => true});
        Object.defineProperty(navigator, 'onLine', {get: () => true});
        """
        self.driver.execute_script(stealth_js)

        # Add realistic cookies that a regular browser would have
        try:
            self.driver.get("https://footdistrict.com")
            time.sleep(3)  # Let initial cookies be set
            self.driver.delete_all_cookies()  # Clear any automation cookies

            # Add some realistic cookies
            self.driver.add_cookie({
                'name': '__cfduid',
                'value': 'd1234567890123456789012345678901234567890',
                'domain': '.footdistrict.com'
            })

        except Exception as e:
            logger.warning(f"Cookie setup failed: {e}")

    def is_cloudflare_challenge_present(self):
        """Check if Cloudflare challenge is currently present"""
        try:
            current_url = self.driver.current_url
            page_source = self.driver.page_source

            return (
                "challenge" in current_url or
                "cf-browser-verification" in page_source or
                "Verify you are human" in page_source or
                "Just a moment" in page_source or
                "cf-chl-widget" in page_source or
                "turnstile" in page_source
            )
        except:
            return True  # Assume challenge if we can't check

    def wait_for_cloudflare_challenge(self, timeout=60):
        """Wait for Cloudflare challenge to complete with better handling"""
        try:
            # Check if we're already on a challenge page
            current_url = self.driver.current_url
            page_source = self.driver.page_source

            challenge_detected = (
                "challenge" in current_url or
                "cf-browser-verification" in page_source or
                "Verify you are human" in page_source or
                "Just a moment" in page_source or
                "cf-chl-widget" in page_source
            )

            if challenge_detected:
                logger.info("Cloudflare challenge detected, waiting for completion...")

                # Add human-like behavior while waiting
                try:
                    # Move mouse around
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)

                    # Simulate human interaction
                    for i in range(5):
                        actions.move_by_offset(50, 50).perform()
                        time.sleep(1)
                        actions.move_by_offset(-25, -25).perform()
                        time.sleep(0.5)

                    # Try clicking somewhere neutral
                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        actions.move_to_element(body).click().perform()
                        time.sleep(2)
                    except:
                        pass

                except Exception as e:
                    logger.warning(f"Human-like interaction failed: {e}")

                # Wait for challenge to complete with longer timeout
                try:
                    WebDriverWait(self.driver, timeout).until(
                        lambda driver: "challenge" not in driver.current_url and
                                      "cf-browser-verification" not in driver.page_source and
                                      "Verify you are human" not in driver.page_source and
                                      "Just a moment" not in driver.page_source and
                                      "cf-chl-widget" not in driver.page_source
                    )
                    logger.info("Cloudflare challenge completed successfully")
                    return True
                except:
                    logger.warning(f"Cloudflare challenge did not complete within {timeout} seconds")
                    return False
            else:
                logger.info("No Cloudflare challenge detected")
                return True

        except Exception as e:
            logger.warning(f"Cloudflare challenge detection failed: {e}")
            return False

    def setup_embedding_model(self):
        """Setup the image embedding model"""
        logger.info("Loading embedding model...")
        self.processor = AutoProcessor.from_pretrained(EMBEDDING_MODEL)
        self.embedding_model = AutoModel.from_pretrained(EMBEDDING_MODEL)
        self.embedding_model.eval()

    def get_category_page_urls(self) -> List[str]:
        """Get all category page URLs with pagination"""
        urls = [CATEGORY_URL]
        page = 2

        while page <= MAX_PAGES:
            url = f"{CATEGORY_URL}?p={page}"
            # Check if page exists by making a quick request
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    urls.append(url)
                    page += 1
                else:
                    break
            except:
                break

        logger.info(f"Found {len(urls)} category pages")
        return urls

    def scrape_category_page(self, url: str) -> List[str]:
        """Scrape a category page to get product URLs with Cloudflare handling"""
        logger.info(f"Scraping category page: {url}")

        # Navigate to page
        self.driver.get(url)

        # Handle Cloudflare challenge with multiple attempts
        logger.info("Checking for Cloudflare challenge...")
        challenge_detected = self.is_cloudflare_challenge_present()

        if challenge_detected:
            logger.info("Cloudflare challenge detected - attempting to resolve...")

            # Try multiple strategies to resolve the challenge
            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info(f"Attempt {attempt + 1}/{max_attempts} to resolve challenge...")

                # Strategy 1: Wait and refresh
                if attempt == 0:
                    time.sleep(20)  # Wait 20 seconds
                    self.driver.refresh()  # Refresh the page
                    time.sleep(10)

                # Strategy 2: Click somewhere and wait
                elif attempt == 1:
                    try:
                        # Try to click on the body or any clickable element
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        body.click()
                        time.sleep(15)
                    except:
                        time.sleep(15)

                # Strategy 3: Just wait longer
                elif attempt == 2:
                    time.sleep(45)  # Wait 45 seconds total

                # Check if challenge is resolved
                if not self.is_cloudflare_challenge_present():
                    logger.info(f"Cloudflare challenge resolved on attempt {attempt + 1}!")
                    break
                else:
                    logger.warning(f"Challenge still present after attempt {attempt + 1}")

            if self.is_cloudflare_challenge_present():
                logger.warning("Cloudflare challenge persists - proceeding anyway (page might still work)")
            else:
                logger.info("Cloudflare challenge successfully resolved!")
        else:
            logger.info("No Cloudflare challenge detected")

        # Wait for page content to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            logger.warning(f"Page load timeout on {url}: {e}")

        # Add human-like behavior: random mouse movements and scrolling
        try:
            # Move mouse randomly
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)

            # More realistic human behavior
            for i in range(5):
                x_offset = (i % 2) * 200 - 100  # Alternate left/right
                y_offset = (i // 2) * 150  # Move down gradually
                actions.move_by_offset(x_offset, y_offset).perform()
                time.sleep(0.3 + (i * 0.2))  # Increasing delays

            # Scroll down slowly to trigger lazy loading
            for i in range(5):
                scroll_amount = (i + 1) * 300
                self.driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
                time.sleep(0.8 + (i * 0.3))  # Increasing delays

            # Scroll back up a bit (human behavior)
            self.driver.execute_script("window.scrollTo(0, 200);")
            time.sleep(1)

        except Exception as e:
            logger.warning(f"Human-like behavior failed: {e}")

        # Extract product URLs
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        product_urls = []

        # Debug: Save page source for inspection
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        logger.info("Saved debug page to debug_page.html")

        # Check if we're still on a Cloudflare challenge page
        if "challenge" in self.driver.current_url or "Just a moment" in soup.get_text():
            logger.warning("Cloudflare challenge still present - proceeding anyway")
            # Don't return empty list - try to find products anyway

        # Try different selectors for product links (more comprehensive)
        selectors = [
            'a[href*=".html"]',
            '.product-item a',
            '.product-card a',
            '[data-product] a',
            '.product a',
            '.item a',
            '.product-link',
            'a[href*="product"]',
            'a[href*="/en/"]'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(BASE_URL, href)
                    # Check if it's a product URL pattern
                    if re.match(PRODUCT_URL_PATTERN, full_url) and full_url not in self.processed_urls:
                        product_urls.append(full_url)
                        self.processed_urls.add(full_url)
                        logger.info(f"Found product URL: {full_url}")

        # Also try to find any links that contain product-like patterns
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and ('samba' in href.lower() or 'adidas' in href.lower() or 'nike' in href.lower() or 'yeezy' in href.lower()):
                full_url = urljoin(BASE_URL, href)
                if re.match(PRODUCT_URL_PATTERN, full_url) and full_url not in self.processed_urls:
                    product_urls.append(full_url)
                    self.processed_urls.add(full_url)
                    logger.info(f"Found brand-specific product URL: {full_url}")

        logger.info(f"Found {len(product_urls)} product URLs on {url}")
        return list(set(product_urls))  # Remove duplicates

    def scrape_product_page(self, url: str) -> Optional[Dict]:
        """Scrape individual product page for all data with Cloudflare handling"""
        logger.info(f"Scraping product: {url}")
        try:
            self.driver.get(url)

            # Handle Cloudflare challenge
            if not self.wait_for_cloudflare_challenge():
                logger.warning("Cloudflare challenge may still be active on product page")

            # Wait for product data to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-info, .product-details, h1, [data-product-title]"))
            )

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Check if we're still on a Cloudflare challenge page
        if "challenge" in self.driver.current_url or "Just a moment" in soup.get_text():
            logger.warning(f"Cloudflare challenge still present for product: {url} - proceeding anyway")
            # Don't return None - try to scrape anyway as the page might still work

            # Extract basic information
            title = self.extract_title(soup)
            price_data = self.extract_price(soup)
            gender = self.extract_gender(soup, title)
            image_urls = self.extract_image_urls(soup)
            description = self.extract_description(soup)

            if not title or not price_data:
                logger.warning(f"Missing essential data for {url}")
                return None

            # Create product data
            product_data = {
                'id': self.generate_product_id(url),
                'source': SOURCE,
                'brand': BRAND,
                'product_url': url,
                'title': title,
                'gender': gender,
                'price': price_data['price'],
                'currency': price_data['currency'],
                'second_hand': SECOND_HAND,
                'metadata': json.dumps({
                    'description': description,
                    'image_urls': image_urls,
                    'scraped_at': time.time()
                })
            }

            # Process main image for embedding
            if image_urls:
                embedding = self.generate_image_embedding(image_urls[0])
                if embedding is not None:
                    product_data['embedding'] = embedding.tolist()
                product_data['image_url'] = image_urls[0]

            return product_data

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None

    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title"""
        selectors = [
            'h1.product-title',
            'h1',
            '.product-name',
            '.product-title',
            '[data-product-title]'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def extract_price(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract price and currency"""
        selectors = [
            '.price',
            '.product-price',
            '.current-price',
            '[data-price]'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)

                # Extract numeric price
                price_match = re.search(r'(\d+(?:[.,]\d+)?)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))

                    # Determine currency
                    currency = 'EUR'  # Default for Foot District EU
                    if '€' in price_text:
                        currency = 'EUR'
                    elif '$' in price_text:
                        currency = 'USD'
                    elif '£' in price_text:
                        currency = 'GBP'

                    return {'price': price, 'currency': currency}
        return None

    def extract_gender(self, soup: BeautifulSoup, title: str) -> str:
        """Extract gender from title or page content"""
        title_lower = title.lower()

        if 'women' in title_lower or 'womens' in title_lower or 'female' in title_lower:
            return 'WOMAN'
        elif 'men' in title_lower or 'mens' in title_lower or 'male' in title_lower:
            return 'MAN'
        elif 'unisex' in title_lower:
            return 'UNISEX'

        # Try to find gender indicators in breadcrumbs or categories
        breadcrumbs = soup.select('.breadcrumb, .breadcrumbs, nav')
        for breadcrumb in breadcrumbs:
            text = breadcrumb.get_text().lower()
            if 'women' in text or 'womens' in text:
                return 'WOMAN'
            elif 'men' in text or 'mens' in text:
                return 'MAN'

        # Default to MAN since we're scraping men's footwear category
        return 'MAN'

    def extract_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract product image URLs"""
        image_urls = []

        # Try different image selectors
        selectors = [
            '.product-gallery img',
            '.product-images img',
            '.gallery img',
            '[data-zoom-image]',
            '.product-image img'
        ]

        for selector in selectors:
            images = soup.select(selector)
            for img in images:
                src = img.get('src') or img.get('data-src') or img.get('data-zoom-image')
                if src:
                    full_url = urljoin(BASE_URL, src)
                    if full_url not in image_urls:
                        image_urls.append(full_url)

        return image_urls

    def extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product description"""
        selectors = [
            '.product-description',
            '.description',
            '.product-details',
            '[data-description]'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def generate_image_embedding(self, image_url: str) -> Optional[np.ndarray]:
        """Generate 768-dim image embedding"""
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Open image
            image = Image.open(BytesIO(response.content)).convert('RGB')

            # Process image
            inputs = self.processor(images=image, return_tensors="pt")

            with torch.no_grad():
                outputs = self.embedding_model(**inputs)

            # Get the pooled embedding (768-dim)
            embedding = outputs.pooler_output.squeeze().numpy()

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding for {image_url}: {str(e)}")
            return None

    def generate_product_id(self, url: str) -> str:
        """Generate unique product ID from URL"""
        # Extract product code from URL
        match = re.search(r'/([^/]+)\.html$', url)
        if match:
            return f"fd_{match.group(1)}"
        else:
            # Fallback to hash of URL
            import hashlib
            return f"fd_{hashlib.md5(url.encode()).hexdigest()[:16]}"

    async def save_to_supabase(self, products: List[Dict]):
        """Save products to Supabase database"""
        if not self.supabase:
            logger.error("Supabase client not initialized")
            return None

        try:
            # Prepare products for insertion
            for product in products:
                if 'embedding' in product and product['embedding'] is not None:
                    # Convert numpy array to list for Supabase
                    if isinstance(product['embedding'], np.ndarray):
                        product['embedding'] = product['embedding'].tolist()

            # Insert products (upsert based on unique constraint)
            result = self.supabase.table('products').upsert(products).execute()

            logger.info(f"Successfully saved {len(products)} products to database")
            return result

        except Exception as e:
            logger.error(f"Error saving to Supabase: {str(e)}")

            # Fallback: save to JSON file
            try:
                import json
                with open('products_backup.json', 'a', encoding='utf-8') as f:
                    for product in products:
                        json.dump(product, f, ensure_ascii=False, default=str)
                        f.write('\n')
                logger.info(f"Saved {len(products)} products to backup JSON file")
            except Exception as backup_error:
                logger.error(f"Failed to save backup: {backup_error}")

            return None

    async def run_scraper_with_timeout(self):
        """Run the complete scraping pipeline with timeout"""
        timeout_seconds = TIMEOUT_HOURS * 3600  # Convert hours to seconds

        try:
            await asyncio.wait_for(self.run_scraper(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(f"Scraping timed out after {TIMEOUT_HOURS} hours")
        except Exception as e:
            logger.error(f"Scraping failed with error: {e}")

    async def run_scraper(self):
        """Run the complete scraping pipeline"""
        logger.info("Starting Foot District scraper...")

        # Setup
        self.setup_driver()
        self.setup_embedding_model()

        try:
            # Get all category pages
            category_urls = self.get_category_page_urls()

            # Scrape all product URLs
            all_product_urls = []
            for category_url in category_urls:
                product_urls = self.scrape_category_page(category_url)
                all_product_urls.extend(product_urls)
                time.sleep(REQUEST_DELAY)

            logger.info(f"Total product URLs found: {len(all_product_urls)}")

            # Apply limit if specified
            if self.limit:
                all_product_urls = all_product_urls[:self.limit]
                logger.info(f"Limited to {len(all_product_urls)} products for testing")

            # Process products in batches
            products_processed = 0
            for i in range(0, len(all_product_urls), BATCH_SIZE):
                batch_urls = all_product_urls[i:i + BATCH_SIZE]
                products = []

                for url in batch_urls:
                    if self.limit and products_processed >= self.limit:
                        break

                    product_data = self.scrape_product_page(url)
                    if product_data:
                        products.append(product_data)
                        products_processed += 1

                        if self.limit and products_processed >= self.limit:
                            logger.info(f"Reached product limit of {self.limit}")
                            break

                    time.sleep(REQUEST_DELAY)

                # Save batch to database
                if products:
                    await self.save_to_supabase(products)

                logger.info(f"Processed batch {i//BATCH_SIZE + 1}/{(len(all_product_urls) + BATCH_SIZE - 1)//BATCH_SIZE}, total products: {products_processed}")

                # Break if we've reached the limit
                if self.limit and products_processed >= self.limit:
                    break

        finally:
            if self.driver:
                self.driver.quit()

        logger.info("Scraping completed!")

if __name__ == "__main__":
    scraper = FootDistrictScraper()
    asyncio.run(scraper.run_scraper())
