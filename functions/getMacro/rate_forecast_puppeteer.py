#!/usr/bin/env python3
"""
[FILENAME] puppeteer_client.py
[DESCRIPTION] Client for the Puppeteer screenshot microservice with fallback mechanism
Author: JP + [2024-07-19]
"""

import os
import json
import logging
import base64
import requests
import tempfile
import subprocess
import time
import socket
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Update to use localhost in development/testing environments
PUPPETEER_SERVICE_URL = os.environ.get(
    "PUPPETEER_SERVICE_URL", 
    "http://localhost:8080"  # Default to localhost instead of the cloud URL
)

def is_service_running(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a service is running at the given host and port"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def start_puppeteer_service() -> bool:
    """
    Attempt to start the Puppeteer microservice locally.
    
    Returns:
        bool: True if service started successfully, False otherwise
    """
    try:
        logger.info("Attempting to start Puppeteer service locally...")
        
        # Check if already running
        if is_service_running("localhost", 8080):
            logger.info("Puppeteer service is already running")
            return True
            
        # Construct the npm start command for the puppeteer service
        # This assumes the puppeteer-service directory is in a known location
        service_dirs = [
            "../../../puppeteer-service",  # Relative to functions/getMacro
            "../../puppeteer-service",     # Relative to functions
            "../puppeteer-service",        # Relative to getMacro parent
            "./puppeteer-service",         # In current directory
        ]
        
        service_dir = None
        for dir_path in service_dirs:
            if os.path.exists(os.path.join(dir_path, "package.json")):
                service_dir = dir_path
                break
                
        if not service_dir:
            logger.error("Could not find puppeteer-service directory")
            return False
            
        # Start the service in a separate process
        logger.info(f"Starting Puppeteer service from {service_dir}")
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=service_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for service to start (up to 10 seconds)
        for _ in range(10):
            if is_service_running("localhost", 8080):
                logger.info("Puppeteer service started successfully")
                return True
            time.sleep(1)
            
        # Check if process failed to start
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"Failed to start Puppeteer service: {stderr.decode('utf-8')}")
            return False
            
        logger.warning("Puppeteer service might be starting, but didn't respond in time")
        return False
        
    except Exception as e:
        logger.exception(f"Error starting Puppeteer service: {str(e)}")
        return False

def take_site_screenshot(url: str, source_name: str) -> Optional[str]:
    """
    Takes a screenshot of a website using the Puppeteer microservice with fallbacks.
    
    Args:
        url: URL to take screenshot of
        source_name: Name of the source (used for filename)
        
    Returns:
        Path to the screenshot image or None if failed
    """
    try:
        logger.info(f"Taking screenshot of {url} using Puppeteer service at {PUPPETEER_SERVICE_URL}")
        
        # Check if service is running
        host = PUPPETEER_SERVICE_URL.split("://")[1].split(":")[0]
        port = int(PUPPETEER_SERVICE_URL.split(":")[-1].split("/")[0])
        
        if not is_service_running(host, port):
            logger.warning(f"Puppeteer service not running at {PUPPETEER_SERVICE_URL}")
            
            # Try to start it if it's localhost
            if host == "localhost":
                if not start_puppeteer_service():
                    logger.error("Could not start Puppeteer service")
                    return None
        
        # Prepare the request payload
        payload = {
            "symbol": source_name,  # Using source_name as symbol for tracking
            "url": url,             # Adding url parameter to payload
            "timeframe": "1d",      # Default timeframe
            "indicators": []        # No indicators needed
        }
        
        # Call the snapshot endpoint
        response = requests.post(
            f"{PUPPETEER_SERVICE_URL}/snapshot", 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Some financial sites load slowly
        )
        
        # Check if successful
        if response.status_code != 200:
            logger.error(f"Failed to get screenshot: HTTP {response.status_code}, {response.text}")
            return None
        
        # Parse the response
        response_data = response.json()
        
        # Check if we got the image data
        if "image_base64" not in response_data:
            logger.error(f"No image data in response: {response_data}")
            return None
            
        # Decode the base64 image and save to a temp file
        image_data = base64.b64decode(response_data["image_base64"])
        
        # Create a temp filename
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=".png", 
            prefix=f"{source_name.lower().replace(' ', '_')}_"
        ).name
        
        # Write the image to a file
        with open(temp_file, "wb") as f:
            f.write(image_data)
            
        logger.info(f"Screenshot saved to {temp_file}")
        return temp_file
        
    except Exception as e:
        logger.exception(f"Error taking screenshot of {url}: {str(e)}")
        return None

def scrape_with_puppeteer_and_gemini(url: str, source_name: str) -> Dict[str, Any]:
    """
    Scrape a website using Puppeteer screenshot + Gemini Flash 2.0 analysis.
    
    Args:
        url: The URL to scrape
        source_name: Name of the source for specific extraction
        
    Returns:
        Dict containing the extracted data
    """
    try:
        logger.info(f"Taking screenshot of {url} for {source_name}")
        
        # Step 1: Take a screenshot of the site using Puppeteer service
        screenshot_path = take_site_screenshot(url, source_name)
        
        if not screenshot_path:
            logger.error(f"Failed to take screenshot of {url}")
            return {
                "source": source_name,
                "url": url,
                "method": "puppeteer_screenshot_failed",
                "error": "Failed to take screenshot",
            }
        
        # Step 2: Import and use Gemini Flash 2.0 for analysis
        import google.generativeai as genai
        
        try:
            # Initialize Gemini API
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                logger.error("GEMINI_API_KEY not set in environment variables")
                return {
                    "source": source_name,
                    "url": url,
                    "method": "gemini_api_key_missing",
                    "error": "Gemini API key missing",
                }
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro-vision')
            
            # Load the image
            from PIL import Image
            image = Image.open(screenshot_path)
            
            # Create the prompt
            prompt = """
            You are an economic data extraction assistant. Please analyze this screenshot and extract all economic indicators visible, including their names, values, trends, and other relevant information.
            
            Please extract key economic data such as:
            - Interest rates (Fed funds rate, Treasury yields)
            - Inflation rates (CPI, PCE)
            - Growth metrics (GDP, PMI)
            - Employment data (Unemployment rate, Job numbers)
            - Market indicators (Stock indices, VIX)
            - Any other economic indicators present
            
            Format your response as a JSON object with indicators grouped by category.
            """
            
            # Generate a response
            response = model.generate_content([prompt, image])
            
            # Parse the response to extract structured data
            extracted_data = {
                "source": source_name,
                "url": url,
                "method": "puppeteer_gemini",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "data": response.text
            }
            
            # Clean up the temporary screenshot file
            try:
                os.remove(screenshot_path)
                logger.info(f"Deleted temporary screenshot: {screenshot_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary screenshot: {screenshot_path}, error: {str(e)}")
            
            return extracted_data
            
        except Exception as e:
            logger.exception(f"Error in Gemini Vision extraction: {str(e)}")
            return {
                "source": source_name,
                "url": url,
                "method": "puppeteer_gemini_failed",
                "error": f"Gemini Vision error: {str(e)}",
            }
            
    except Exception as e:
        logger.exception(f"Error in Puppeteer+Gemini for {source_name}: {str(e)}")
        return {
            "source": source_name,
            "url": url,
            "method": "puppeteer_gemini_failed",
            "error": str(e),
        } 