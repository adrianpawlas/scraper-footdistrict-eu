#!/usr/bin/env python3
"""
Import products from JSON backup file to Supabase
Run this after fixing Supabase permissions
"""

import json
import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_from_backup():
    """Import products from backup JSON file to Supabase"""
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Supabase client initialized")

        # Read backup file
        products = []
        with open('products_backup.json', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    product = json.loads(line.strip())
                    products.append(product)

        logger.info(f"Found {len(products)} products in backup file")

        if not products:
            logger.info("No products to import")
            return

        # Import in batches
        batch_size = 10
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            try:
                result = supabase.table('products').upsert(batch).execute()
                logger.info(f"Imported batch {i//batch_size + 1}/{(len(products) + batch_size - 1)//batch_size}")
            except Exception as e:
                logger.error(f"Failed to import batch {i//batch_size + 1}: {e}")

        logger.info("Import completed successfully!")

    except FileNotFoundError:
        logger.error("Backup file 'products_backup.json' not found")
    except Exception as e:
        logger.error(f"Import failed: {e}")

if __name__ == "__main__":
    import_from_backup()
