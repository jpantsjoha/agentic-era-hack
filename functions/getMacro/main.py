#!/usr/bin/env python3
"""
[FILENAME] main.py
[DESCRIPTION] getMacro Cloud Function for Agentic-Era-Hackaton
Author: JP + [2024-07-19]
"""

import os
import json
import time
import datetime
import argparse
import functions_framework
import flask
from typing import Dict, Any, List, Optional
from google.cloud import storage
import logging
from tabulate import tabulate
from logger import configure_logger
# from macroAnalysis import run_macro_analysis  # Commented out API-based analysis
# Import for puppeteer-based extraction
from rate_forecast_puppeteer import scrape_with_puppeteer_and_gemini

# Configure logging
logger = logging.getLogger(__name__)
configure_logger(level=logging.INFO)

# Initialize Storage client
storage_client = None

def init_storage():
    """Initialize Google Cloud Storage client."""
    global storage_client
    if storage_client is None:
        storage_client = storage.Client()
    return storage_client

def read_datasources_file(filepath="DataSources.text") -> List[str]:
    """
    Read URLs from DataSources.text file.
    
    Args:
        filepath: Path to the DataSources.text file
        
    Returns:
        List of URLs to process
    """
    try:
        urls = []
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):  # Skip empty lines and comments
                    urls.append(line)
        logger.info(f"Loaded {len(urls)} URLs from {filepath}")
        return urls
    except Exception as e:
        logger.error(f"Error reading DataSources file: {str(e)}")
        return []

def process_url(url: str) -> Dict[str, Any]:
    """
    Process a single URL using Puppeteer and Gemini Flash 2.0.
    
    Args:
        url: URL to process
        
    Returns:
        Dictionary with extracted data
    """
    logger.info(f"Processing URL: {url}")
    
    # Extract source name from URL (use domain as default)
    import re
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    source_name = domain_match.group(1) if domain_match else "unknown_source"
    
    # Use Puppeteer + Gemini to extract data
    extracted_data = scrape_with_puppeteer_and_gemini(url, source_name)
    
    return extracted_data

def store_data_to_gcs(data: Dict[str, Any], bucket_name="MacroData-Extracts", 
                     filename="LatestMacroData.json") -> bool:
    """
    Store extracted data to Google Cloud Storage.
    
    Args:
        data: Data to store
        bucket_name: GCS bucket name
        filename: Filename in the bucket
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Initialize Storage client
        client = init_storage()
        
        # Get bucket
        bucket = client.bucket(bucket_name)
        
        # Create blob and upload data
        blob = bucket.blob(filename)
        blob.upload_from_string(
            json.dumps(data, indent=2, default=str),
            content_type="application/json"
        )
        
        logger.info(f"Data stored successfully to gs://{bucket_name}/{filename}")
        return True
    except Exception as e:
        logger.error(f"Error storing data to GCS: {str(e)}")
        return False

@functions_framework.http
def run(request):
    """
    Cloud Function entry point.
    
    Args:
        request: HTTP request
        
    Returns:
        HTTP response
    """
    try:
        # Parse parameters from request
        local = request.args.get("local", "").lower() == "true"
        dry_run = request.args.get("dry_run", "").lower() == "true"
        verbose = request.args.get("verbose", "").lower() == "true"
        
        # Run main function
        success = main(local=local, dry_run=dry_run, verbose=verbose)
        
        if success:
            message = "Macro data processing completed successfully."
            status_code = 200
        else:
            message = "Macro data processing failed."
            status_code = 500
            
        # Return appropriate HTTP response
        return flask.jsonify({"status": "success" if success else "error", "message": message}), status_code
        
    except Exception as e:
        logger.exception(f"Error in run function: {str(e)}")
        return flask.jsonify({"status": "error", "message": str(e)}), 500

def main(local=False, dry_run=False, verbose=False) -> bool:
    """
    Main function.
    
    Args:
        local: Run in local mode
        dry_run: Don't store data
        verbose: Print verbose output
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read URLs from DataSources.text
        urls = read_datasources_file()
        
        if not urls:
            logger.error("No URLs found in DataSources.text file")
            return False
        
        # Process each URL
        results = []
        for url in urls:
            result = process_url(url)
            results.append(result)
            
        # Combine results
        combined_data = {
            "metadata": {
                "date": datetime.datetime.now().isoformat(),
                "timestamp": datetime.datetime.now().isoformat(),
                "provider": "COMPOSITE",
                "sources": [url for url in urls],
                "validation": {
                    "status": "OK",
                    "missing_fields": [],
                    "warnings": []
                }
            },
            "data": results
        }
        
        # Display results in local mode
        if local or verbose:
            print(json.dumps(combined_data, indent=2, default=str))
        
        # Store results if not dry run
        if not dry_run:
            store_data_to_gcs(combined_data)
        
        return True
    except Exception as e:
        logger.exception(f"Error in main function: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch and store macroeconomic data")
    parser.add_argument("--local", action="store_true", help="Run in local mode")
    parser.add_argument("--dry-run", action="store_true", help="Don't store data")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    args = parser.parse_args()
    
    main(local=args.local, dry_run=args.dry_run, verbose=args.verbose)
