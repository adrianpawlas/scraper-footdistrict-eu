import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = "https://yqawmzggcgpeyaaynrjk.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxYXdtemdnY2dwZXlhYXlucmprIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTAxMDkyNiwiZXhwIjoyMDcwNTg2OTI2fQ.XtLpxausFriraFJeX27ZzsdQsFv3uQKXBBggoz6P4D4"

# Foot District Configuration
BASE_URL = "https://footdistrict.com"
CATEGORY_URL = "https://footdistrict.com/en/footwear/"
PRODUCT_URL_PATTERN = r"https://footdistrict.com/en/.*\.html"

# Scraping Configuration
MAX_PAGES = 100  # Maximum pages to scrape
REQUEST_DELAY = 2  # Delay between requests in seconds
BATCH_SIZE = 10  # Products to process at once
TIMEOUT_HOURS = 12  # Maximum runtime in hours

# Image Configuration
EMBEDDING_MODEL = "google/siglip-base-patch16-384"
EMBEDDING_DIM = 768

# Database Configuration
SOURCE = "scraper"
BRAND = "Foot District"
SECOND_HAND = False
