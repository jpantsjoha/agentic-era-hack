#!/usr/bin/env python3
"""
[FILENAME] truflation_data.py
[DESCRIPTION] Extracts economic indicators data from Truflation using UI snapshots
Author: JP + [2024-07-19]
"""

import os
import json
import logging
import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import google.generativeai as genai
from google.cloud import firestore
import tempfile
from PIL import Image
from tabulate import tabulate

# Import the puppeteer screenshot service client
from rate_forecast_puppeteer import take_site_screenshot

# Configure logging
logger = logging.getLogger(__name__)

class EconomicIndicator:
    """Class representing an economic indicator from Truflation"""
    def __init__(self, name: str, value: str, trend: Optional[str] = None, 
                 updated: Optional[str] = None, source: str = "Truflation"):
        self.name = name
        self.value = value
        self.trend = trend
        self.updated = updated
        self.source = source
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "trend": self.trend,
            "updated": self.updated,
            "source": self.source
        }

def extract_data_with_gemini_vision(image_path: str) -> List[EconomicIndicator]:
    """
    Extract data from an image using Google's Gemini Vision API.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        List of EconomicIndicator objects
    """
    # Initialize Gemini API
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set in environment variables")
        return []
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro-vision')
    
    # Load the image
    image = Image.open(image_path)
    
    # Create the prompt
    prompt = """
    You are an economic data extraction assistant. Please analyze this screenshot from the Truflation website and extract all economic indicators visible, including their names, values, trends, and last updated dates.
    
    IMPORTANT: Pay special attention to key indicators like:
    - Federal Funds Rate (Critical)
    - Inflation Rate / CPI
    - GDP Growth Rate
    - Unemployment Rate
    - Treasury Yields (2yr, 10yr)
    - Any other economic indicators visible
    
    Please format each indicator as a JSON object with the following fields:
    - name: The exact name of the indicator
    - value: The numeric value with its unit (e.g., "5.25%", "$102.5B")
    - trend: The trend direction if shown (e.g., "up", "down", "stable")
    - updated: The last updated date if available
    
    Provide your complete response as a JSON array of these objects.
    """
    
    try:
        # Generate a response
        response = model.generate_content([prompt, image])
        response_text = response.text
        
        # Extract JSON data from the response
        indicators = []
        
        # Look for JSON in the response (between ```json and ```)
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try finding array directly
            json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', response_text)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Just use the whole text as a fallback
                json_str = response_text
        
        try:
            # Parse the JSON
            data = json.loads(json_str)
            
            # Convert to EconomicIndicator objects
            for item in data:
                indicator = EconomicIndicator(
                    name=item.get("name", "Unknown"),
                    value=item.get("value", "N/A"),
                    trend=item.get("trend"),
                    updated=item.get("updated"),
                    source="Truflation"
                )
                indicators.append(indicator)
                
            logger.info(f"Successfully extracted {len(indicators)} indicators from Truflation")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.debug(f"Raw response: {response_text}")
            # Try a more flexible approach as fallback
            indicators = extract_indicators_fallback(response_text)
            
        return indicators
    
    except Exception as e:
        logger.exception(f"Error in Gemini Vision: {str(e)}")
        return []

def extract_indicators_fallback(text: str) -> List[EconomicIndicator]:
    """
    Fallback method to extract indicators when JSON parsing fails
    
    Args:
        text: Raw text from Gemini
        
    Returns:
        List of EconomicIndicator objects
    """
    indicators = []
    
    # Look for patterns like "Name: Value" or "Name - Value"
    lines = text.split('\n')
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Look for Federal Funds Rate specifically (highest priority)
        if "federal funds" in line.lower() or "fed funds" in line.lower():
            rate_match = re.search(r'(\d+\.\d+%|\d+%)', line)
            if rate_match:
                indicators.append(EconomicIndicator(
                    name="Federal Funds Rate",
                    value=rate_match.group(1),
                    trend=extract_trend(line),
                    updated=extract_date(line),
                    source="Truflation"
                ))
        
        # Try to extract other indicators
        # Pattern: Name: Value or Name - Value
        matches = re.findall(r'([A-Za-z\s\(\)]+)[:|-]\s*([0-9\.\,\+\-%\$]+)', line)
        if matches:
            for name, value in matches:
                indicators.append(EconomicIndicator(
                    name=name.strip(),
                    value=value.strip(),
                    trend=extract_trend(line),
                    updated=extract_date(line),
                    source="Truflation"
                ))
    
    return indicators

def extract_trend(text: str) -> Optional[str]:
    """Extract trend information from text"""
    if "increase" in text.lower() or "up" in text.lower() or "↑" in text:
        return "up"
    elif "decrease" in text.lower() or "down" in text.lower() or "↓" in text:
        return "down"
    elif "stable" in text.lower() or "unchanged" in text.lower() or "→" in text:
        return "stable"
    return None

def extract_date(text: str) -> Optional[str]:
    """Extract date information from text"""
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
        r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        r'\w+ \d{1,2},? \d{4}'       # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            return date_match.group(0)
    return None

def extract_truflation_data(rate_forecast_enabled: bool = True, 
                            write_to_firestore: bool = True,
                            display_table: bool = True) -> Dict[str, Any]:
    """
    Extract economic indicators data from Truflation.
    
    Args:
        rate_forecast_enabled: Whether to also fetch rate forecasts
        write_to_firestore: Whether to write results to Firestore
        display_table: Whether to display results in table format
        
    Returns:
        Dictionary with extracted indicators and rate forecasts
    """
    # Set the Truflation URL
    truflation_url = "https://truflation.com/inflation" # Updated URL - their marketplace page may be deprecated
    
    # Step 1: Take screenshot using Puppeteer service
    logger.info("Taking screenshot of Truflation marketplace")
    screenshot_path = take_site_screenshot(truflation_url, "Truflation")
    
    if not screenshot_path:
        logger.error("Failed to take screenshot of Truflation marketplace")
        return {"error": "Failed to take screenshot"}
    
    # Step 2: Extract data using Gemini Vision
    logger.info("Extracting data from screenshot using Gemini Vision")
    indicators = extract_data_with_gemini_vision(screenshot_path)
    
    # Clean up screenshot file
    try:
        os.remove(screenshot_path)
    except Exception as e:
        logger.warning(f"Failed to delete screenshot: {str(e)}")
    
    # Step 3: Display table if requested
    if display_table and indicators:
        display_indicators_table(indicators)
    
    # Step 4: Write to Firestore if requested
    if write_to_firestore and indicators:
        try:
            db = firestore.Client()
            store_truflation_data(indicators, db)
        except Exception as e:
            logger.error(f"Error writing to Firestore: {str(e)}")
    
    # Convert indicators to dictionary format
    all_indicators = [indicator.to_dict() for indicator in indicators]
    
    # Step 5: Include rate forecast data if enabled
    rate_forecasts = None
    if rate_forecast_enabled:
        try:
            logger.info("Fetching rate forecast data")
            from RATE_FORECAST_DATA import get_consolidated_rate_forecasts, display_meeting_forecasts, display_bank_forecasts
            
            rate_forecasts = get_consolidated_rate_forecasts(write_to_firestore=write_to_firestore)
            
            # Display rate forecasts if requested
            if display_table and rate_forecasts:
                display_meeting_forecasts(rate_forecasts)
                display_bank_forecasts(rate_forecasts)
        except Exception as e:
            logger.error(f"Error fetching rate forecast data: {str(e)}")
    
    # Return results
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "indicators": all_indicators,
        "rate_forecasts": rate_forecasts
    }

def store_truflation_data(indicators: List[EconomicIndicator], db: firestore.Client) -> bool:
    """
    Store the Truflation indicators in Firestore in the macroData collection
    
    Args:
        indicators: List of EconomicIndicator objects
        db: Firestore client
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Storing {len(indicators)} Truflation indicators in Firestore")
        
        # Create a document with today's date
        today = datetime.datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        # Prepare indicators data in the appropriate format for macroData
        indicators_dict = {}
        for indicator in indicators:
            # Convert to standard format - normalize name to snake_case for consistency
            key = indicator.name.lower().replace(' ', '_').replace('-', '_')
            indicators_dict[key] = {
                "value": indicator.value,
                "trend": indicator.trend,
                "updated": indicator.updated,
                "source": indicator.source
            }
        
        # Create the document data structure that matches macroData format
        doc_data = {
            "date": today,
            "timestamp": today,
            "provider": "TRUFLATION",
            "indicators": indicators_dict,
            "validation": {
                "status": "OK",
                "message": f"Extracted {len(indicators)} indicators"
            }
        }
        
        # Write to macroData collection
        doc_ref = db.collection('macroData').document(date_str + "_TRUFLATION")
        doc_ref.set(doc_data)
        
        logger.info(f"Successfully wrote Truflation data to Firestore: {doc_ref.id}")
        return True
        
    except Exception as e:
        logger.exception(f"Error storing Truflation data: {str(e)}")
        return False

def display_indicators_table(indicators: List[EconomicIndicator]) -> None:
    """
    Display a table of economic indicators.
    
    Args:
        indicators: List of EconomicIndicator objects
    """
    # Prepare data for tabulation
    table_data = []
    for indicator in indicators:
        trend_display = indicator.trend if indicator.trend else "N/A"
        updated_display = indicator.updated if indicator.updated else "N/A"
        table_data.append([indicator.name, indicator.value, trend_display, updated_display])
    
    # Display the table
    headers = ["Indicator", "Value", "Trend", "Last Updated"]
    print("\n=== Truflation Economic Indicators ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal indicators: {len(indicators)}")

if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Extract Truflation economic indicators")
    parser.add_argument("--no-firestore", action="store_true", help="Skip writing to Firestore")
    parser.add_argument("--no-rate-forecast", action="store_true", help="Disable rate forecast extraction")
    args = parser.parse_args()
    
    # Extract the data
    results = extract_truflation_data(
        rate_forecast_enabled=not args.no_rate_forecast,
        write_to_firestore=not args.no_firestore
    )
    
    # Print the results
    print(json.dumps(results, indent=2, default=str)) 