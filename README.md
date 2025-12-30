# Foot District Scraper

A comprehensive scraper for Foot District (EU) that extracts product data, generates image embeddings, and stores everything in Supabase.

## Features

- **Cloudflare Bypass**: Uses Selenium with Chrome to handle anti-bot protection
- **Complete Product Data**: Extracts all required fields including title, price, gender, images
- **Image Embeddings**: Generates 768-dimensional embeddings using Google SigLIP model
- **Supabase Integration**: Automatically stores data in your Supabase database
- **Error Handling**: Robust error handling and retry logic
- **Batch Processing**: Processes products in batches for efficiency

## Required Fields Extracted

- `source`: Automatically set to "scraper"
- `brand`: Automatically set to "Foot District"
- `product_url`: Product page URL
- `image_url`: Main product image URL
- `title`: Product name
- `gender`: MAN, WOMAN, or UNISEX
- `price`: Numeric price (e.g., 45.9)
- `currency`: EUR, USD, or GBP
- `second_hand`: Automatically set to FALSE
- `embedding`: 768-dim vector from google/siglip-base-patch16-384
- `metadata`: JSON with additional product information
- `created_at`: Timestamp when added to database

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Chrome Browser** (required for Selenium):
   - The scraper will automatically download ChromeDriver
   - Make sure Google Chrome is installed on your system

## Configuration

All configuration is in `config.py`:
- Supabase credentials (already configured)
- Scraping parameters (delays, batch sizes, etc.)
- Model settings

## Usage

**Run the scraper**:
```bash
python run_scraper.py
```

**Or run directly**:
```bash
python footdistrict_scraper.py
```

## What It Does

1. **Category Scraping**: Starts from https://footdistrict.com/en/footwear/ and follows pagination (?p=2, ?p=3, etc.)
2. **Product Discovery**: Extracts all product URLs from category pages
3. **Product Scraping**: Visits each product page to extract data
4. **Image Processing**: Downloads product images and generates embeddings
5. **Database Storage**: Saves all data to Supabase with upsert (updates existing products)

## Database Schema

The scraper works with your existing `products` table structure and respects the unique constraint on `(source, product_url)`.

## Current Status

✅ **Working Features:**
- Cloudflare bypass with Selenium
- Product data extraction (title, price, gender, etc.)
- Image embedding generation with google/siglip-base-patch16-384
- JSON backup saving
- Comprehensive error handling

⚠️ **Supabase Integration Issue:**
The current anon key doesn't have insert permissions for the products table. You need to:

1. Go to your Supabase dashboard
2. Navigate to Authentication > Policies
3. Add INSERT policy for the products table for anonymous users, OR
4. Replace the anon key in `config.py` with a service role key

Once permissions are fixed, run:
```bash
python import_backup.py
```

## Error Handling

- Automatic retries for failed requests
- Detailed logging to both console and `scraper.log`
- Graceful handling of missing data
- Batch processing to minimize memory usage

## Performance

- Processes products in batches of 10
- 2-second delay between requests to be respectful
- Handles up to 100 category pages (configurable)
- Image embeddings are generated locally using GPU if available

## Troubleshooting

**Chrome Driver Issues**:
- Make sure Chrome browser is installed
- The webdriver-manager will handle driver downloads automatically

**Cloudflare Blocking**:
- The scraper uses Selenium with anti-detection measures
- If blocked, try running with different timing or user agents

**Memory Issues**:
- Reduce `BATCH_SIZE` in config.py
- Process fewer products at once

**Supabase Errors**:
- Check your internet connection
- Verify Supabase credentials in config.py
- Check Supabase dashboard for quota limits

## Logs

All activity is logged to `scraper.log` with timestamps and error details.
