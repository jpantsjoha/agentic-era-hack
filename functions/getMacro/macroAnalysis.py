#!/usr/bin/env python3
"""
[FILENAME] macroAnalysis.py
[DESCRIPTION] Generates AI analysis of macroeconomic data using Gemini
Author: JP + [2024-07-19]
"""

import logging
import os  # Import the os module
import google.generativeai as genai
from google.cloud import firestore
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import argparse  # Import argparse
import datetime

# Assuming logger is in the same directory or accessible via PYTHONPATH
from logger import logger  # Import the custom logger

# Configure Gemini API (replace with your actual API key)
# Best practice: Use environment variables for API keys
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")  # Get API key from environment variable
if not GOOGLE_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set.")
    raise ValueError("GEMINI_API_KEY environment variable not set.") # prevent continuation

genai.configure(api_key=GOOGLE_API_KEY)

def create_macro_analysis_prompt(macro_data_history: List[Dict[str, Any]]) -> str:
    """
    Creates the prompt for Gemini 1.5 Flash, summarizing the last 30 days of macro data.

    Args:
        macro_data_history: A list of dictionaries, each representing a day's macro data.

    Returns:
        A string containing the formatted prompt.
    """
    prompt = """
You are a macroeconomic analyst providing insights on the current and future direction of the economy.
Analyze the following macroeconomic data from the past 30 days.  Provide a concise summary of the
current macroeconomic regime, identify key trends, and predict the likely direction of the
macroeconomic trend in the short to medium term (next 1-3 months).  Be specific and data-driven.

DATA:
"""

    for data_point in macro_data_history:
        date_str = data_point.get("date", "N/A")  # Handle potential missing date
        prompt += f"""
- Date: {date_str}
  - Computed Regime: {data_point.get('computedRegime', 'N/A')}
  - CPI YoY: {data_point.get('cpi_yoy', 'N/A')}
  - PMI: {data_point.get('pmi', 'N/A')}
  - Yield Spread (10Y-2Y): {data_point.get('yieldSpread', 'N/A')}
  - Inflation Composite: {data_point.get('inflationComposite', 'N/A')}
  - M2 YoY: {data_point.get('m2_yoy', 'N/A')}
  - S&P 500: {data_point.get('sp500', 'N/A')}
  - VIX: {data_point.get('vix', 'N/A')}
"""

    prompt += """
Based on the above data:

1.  **Current Regime:**  Clearly state the current macroeconomic regime (e.g., Expansion, Disinflationary Boom, Stagflation Risk, Slowdown/Deflationary).
2.  **Key Trends:** Identify and explain the most important trends in the data.
3.  **Short-Medium Term Outlook:**  Predict the likely direction of the macroeconomic trend over the next 1-3 months.
4.  **Risks and Opportunities:**  Highlight potential risks and opportunities for investors.
5.  **Conflicting Signals:**  If there are any conflicting signals in the data, point them out and explain their potential implications.
6.  **Market Data Relationship:** Briefly relate the market data (S&P 500, VIX) to the macroeconomic indicators.
"""
    return prompt

def generate_macro_analysis(macro_data_history: List[Dict[str, Any]]) -> Optional[str]:
    """
    Generates the macroeconomic analysis using Gemini 1.5 Flash.

    Args:
        macro_data_history: A list of dictionaries, each representing a day's macro data.

    Returns:
        The generated analysis as a string, or None if an error occurred.
    """
    try:
        prompt = create_macro_analysis_prompt(macro_data_history)
        model = genai.GenerativeModel('gemini-1.5-flash-002')
        response = model.generate_content(prompt, stream=False)
        analysis = response.text
        return analysis
    except Exception as e:
        logger.error(f"Error generating macro analysis: {e}")
        return None

def get_macro_data_history(db: firestore.Client, num_days: int = 30) -> List[Dict[str, Any]]:
    """
    Retrieves the last 'num_days' of macro data from Firestore.

    Args:
        db: The Firestore client.
        num_days: The number of days of data to retrieve.

    Returns:
        A list of dictionaries, each representing a day's macro data, ordered by date (oldest first).
        Returns an empty list if no data is found.
    """
    try:
        today = datetime.datetime.utcnow()
        start_date = today - timedelta(days=num_days)
        start_date_str = start_date.strftime('%Y-%m-%d')

        # Query Firestore for documents newer than 'start_date'
        query = (db.collection('macroData')
                 .where('date', '>=', start_date_str)
                 .order_by('date', direction=firestore.Query.ASCENDING))

        documents = query.stream()

        data_history = []
        for doc in documents:
            data = doc.to_dict()
            # Convert Timestamp objects back to strings
            if 'timestamp' in data and isinstance(data['timestamp'], firestore.SERVER_TIMESTAMP.__class__):
                data['timestamp'] = data['timestamp']._to_timestamp().isoformat()
            if 'date' in data and isinstance(data['date'], firestore.Timestamp):
                data['date'] = data['date']._to_timestamp().strftime('%d %B %Y at %H:%M:%S UTC')
            data_history.append(data)

        return data_history

    except Exception as e:
        logger.error(f"Error retrieving macro data history: {e}")
        return []

def store_macro_analysis(db: firestore.Client, analysis: str, dry_run: bool = False) -> None:
    """
    Stores the generated macro analysis in Firestore.

    Args:
        db: The Firestore client.
        analysis: The generated analysis text.
        dry_run: If True, prevents actual Firestore writes.
    """
    try:
        doc_ref = db.collection('analysis').document('macro')  # Store in 'analysis' collection
        if not dry_run:
            doc_ref.set({
                'analysis': analysis,
                'type': 'macro',  # Add a 'type' field to distinguish it
                'ticker': 'N/A',  # Add a 'ticker' field, set to 'N/A'
                "timestamp": firestore.SERVER_TIMESTAMP,
            })
            logger.info("Macro analysis stored successfully.")
        else:
            logger.info("Dry run: Macro analysis would have been stored.")
    except Exception as e:
        logger.error(f"Error storing macro analysis: {e}")

def run_macro_analysis(local: bool = False, dry_run: bool = False) -> str:
    """
    Generates and stores an AI analysis of the latest macroeconomic data.

    Args:
        local: Run in local mode (print to console instead of Firestore).
        dry_run: Do not write to Firestore.

    Returns:
        The generated analysis text, or None if an error occurred.
    """
    logger.info("Starting macroeconomic analysis...")

    # Initialize Firestore client
    db = firestore.Client()

    # Find the most recent document in macroData collection
    logger.debug("Finding most recent date in macroData collection...")
    
    # Try getting the LATEST document first
    latest_ref = db.collection("macroData").document("LATEST")
    latest_doc = latest_ref.get()
    
    most_recent_date = None
    
    if latest_doc.exists:
        logger.debug("Found LATEST document")
        latest_data = latest_doc.to_dict()
        if "date" in latest_data:
            date_str = latest_data["date"]
            if hasattr(date_str, "strftime"):  # Check if it's a date-like object
                most_recent_date = date_str.strftime("%Y-%m-%d")
            else:
                most_recent_date = str(date_str)
            logger.info(f"Most recent date from LATEST: {most_recent_date}")
        else:
            logger.warning("LATEST document doesn't contain 'date' field")
    
    if most_recent_date is None:
        # If LATEST doesn't exist or doesn't have a date, find the most recent document by sorting
        logger.debug("LATEST document not found or missing date, querying by date order...")
        query = db.collection("macroData").order_by("date", direction=firestore.Query.DESCENDING).limit(1)
        docs = list(query.stream())
        
        if docs:
            most_recent_doc = docs[0]
            most_recent_data = most_recent_doc.to_dict()
            if "date" in most_recent_data:
                date_val = most_recent_data["date"]
                if hasattr(date_val, "strftime"):  # Check if it's a date-like object
                    most_recent_date = date_val.strftime("%Y-%m-%d")
                else:
                    most_recent_date = str(date_val)
                logger.info(f"Most recent date from query: {most_recent_date}")
            else:
                logger.warning("Most recent document doesn't contain 'date' field")
        else:
            logger.error("No documents found in macroData collection")
            return None

    if not most_recent_date:
        logger.error("Could not determine most recent date")
        return None

    # Get the last 30 days of macro data starting from the most recent date
    logger.debug(f"Fetching macro data from Firestore starting from {most_recent_date}...")
    
    # Parse the date string if it's not already a date object
    if isinstance(most_recent_date, str):
        try:
            # Try different date formats
            parsed_date = None
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"]:
                try:
                    parsed_date = datetime.datetime.strptime(most_recent_date, fmt).date()
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                logger.error(f"Could not parse date string: {most_recent_date}")
                return None
                
            most_recent_date = parsed_date
        except Exception as e:
            logger.error(f"Error parsing date: {str(e)}")
            return None

    # Now get documents for the last 30 days
    macro_data = []
    for i in range(30):
        date = most_recent_date - datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        doc_ref = db.collection("macroData").document(date_str)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            # Ensure 'indicators' exists and is a dictionary
            if data and "indicators" in data and isinstance(data["indicators"], dict):
                macro_data.append(data)
            else:
                # Try to handle older data format where indicators might be at the top level
                indicators = {}
                for key in ["pmi", "cpi_yoy", "unemployment", "m2_money_supply", "m2_yoy", 
                           "yield_10y", "yield_2y", "yield_spread", "fed_funds_rate", 
                           "gdp_growth", "retail_sales_yoy", "industrial_production"]:
                    if key in data and data[key] is not None:
                        indicators[key] = data[key]
                
                if indicators:
                    data["indicators"] = indicators
                    macro_data.append(data)
                else:
                    logger.warning(f"Document for {date_str} is missing 'indicators' or it's not a dictionary.")
        else:
            logger.warning(f"No data found for {date_str}")

    logger.debug(f"Fetched data for {len(macro_data)} days.")

    if not macro_data:
        logger.error("No macro data found for analysis.")
        return None

    # Construct the prompt for the AI model
    prompt = """Analyze the following US macroeconomic data and provide a structured analysis with these specific sections:

**US Economic Conditions (Current):**
A concise point-in-time summary of current US economic conditions based on the data provided.

**Key Trends and Outlook:**
Provide a short, snappy perspective for each timeframe:
1. Short-term (0-3 months): Immediate outlook based on current momentum
2. Medium-term (3-6 months): Based on leading indicators and expected Fed policy
3. Long-term (6-12 months): Based on structural factors and liquidity dynamics

For the longer-term outlook, consider whether current liquidity conditions represent a temporary slump that could reverse in H2 2024/2025 given potential rate cuts, stabilizing inflation, and debt dynamics. Identify any contrarian indicators that might suggest a different trajectory than the primary trend.

All metrics provided (Fed Funds Rate, PMI, S&P 500, M2 Money Supply, etc.) are specific to the United States economy.
Be concise, specific, and focus your analysis on the US economic landscape:

"""

    for data_point in reversed(macro_data):  # Reverse to present in chronological order
        date_str = data_point.get('date', 'Unknown Date')
        # Check if it's a date object with a strftime method
        if hasattr(date_str, "strftime"):
            date_str = date_str.strftime("%Y-%m-%d")
        
        indicators = data_point.get('indicators', {})
        if isinstance(indicators, dict):  # Ensure indicators is a dictionary
            for key, value in indicators.items():
                if isinstance(value, (int, float)):  # Check if value is a number
                    prompt += f"- {key} ({date_str}): {value}\n"
                else:
                    logger.warning(f"Skipping non-numeric value for {key} on {date_str}: {value}")
        else:
            logger.warning(f"Skipping invalid 'indicators' data for {date_str}")

    logger.debug(f"Generated prompt: {prompt}")

    # Configure the generative AI model
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set")
            return None
            
        # Use the model specified in environment variable, or default to the specified model
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-thinking-exp")
        logger.info(f"Using Gemini model: {model_name}")
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Generate the analysis
        logger.debug("Generating AI analysis...")
        response = model.generate_content(prompt, stream=False)
        analysis = response.text
        logger.debug(f"Generated analysis: {analysis}")

        # Store the analysis in Firestore
        if not dry_run:
            # Always update/overwrite the existing analysis
            if not local:
                # We need to update both the date-specific document and the LATEST document
                latest_date_str = most_recent_date.strftime("%Y-%m-%d") if hasattr(most_recent_date, "strftime") else str(most_recent_date)
                
                logger.debug(f"Updating macroData/{latest_date_str} with AI analysis")
                # Update the specific date document, using set with merge to ensure we update even if field doesn't exist
                date_doc_ref = db.collection("macroData").document(latest_date_str)
                date_doc_ref.set({
                    "aiDataAnalysis": analysis,
                    "analysisTimestamp": datetime.datetime.now()
                }, merge=True)  # Using merge=True ensures other fields aren't affected
                
                # Also update the LATEST document
                logger.debug("Updating LATEST document with AI analysis")
                latest_doc_ref = db.collection("macroData").document("LATEST")
                latest_doc_ref.set({
                    "aiDataAnalysis": analysis,
                    "analysisTimestamp": datetime.datetime.now()
                }, merge=True)  # Using merge=True ensures other fields aren't affected
                
                logger.info(f"Macroeconomic analysis updated in macroData/{latest_date_str} and LATEST documents")
            else:
                logger.info("Local mode: Analysis not stored in Firestore.")
        else:
            logger.info("Dry run: Analysis not stored in Firestore.")

        return analysis  # Return the generated analysis text

    except Exception as e:
        logger.exception(f"Error during AI analysis: {str(e)}")
        return None  # Return None on error

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run macroeconomic analysis.")
    parser.add_argument("--local", action="store_true", help="Run in local mode (print to console).")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Firestore.")
    parser.add_argument("--only-analysis", action="store_true", help="Run only the AI analysis (skip data retrieval).")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    args = parser.parse_args()

    # Configure logger based on command-line argument
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')
    logger.setLevel(numeric_level)  # Set the logger level

    if args.only_analysis:
        analysis_result = run_macro_analysis(local=args.local, dry_run=args.dry_run)
        if analysis_result:
            print("\n--- AI Macroeconomic Analysis ---")
            print(analysis_result)
            print("--- End of Analysis ---\n")
        else:
            print("Error: AI analysis failed to generate a result.")
    else:
        print("Use --only-analysis to run the analysis independently.")
