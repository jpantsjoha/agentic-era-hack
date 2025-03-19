#!/usr/bin/env python3
"""
[FILENAME] start_puppeteer_service.py
[DESCRIPTION] Utility to start and check Puppeteer screenshot service
Author: JP + [2024-07-19]
"""

import os
import sys
import time
import logging
import subprocess
import socket
import requests
import argparse
from typing import Optional, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_service_running(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a service is running at the given host and port"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            # Try making a test request to the /status endpoint if it exists
            try:
                response = requests.get(f"http://{host}:{port}/status", timeout=timeout)
                return response.status_code == 200
            except:
                # If the endpoint doesn't exist, at least we know something's listening
                return True
    except (socket.timeout, ConnectionRefusedError, OSError, requests.RequestException):
        return False

def find_puppeteer_service_dir() -> Optional[str]:
    """Find the puppeteer-service directory"""
    # Look for the directory in the current directory first
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_service_dir = os.path.join(current_dir, "puppeteer-service")
    
    if os.path.exists(os.path.join(local_service_dir, "package.json")):
        return local_service_dir
    
    # Directories to check relative to this script
    service_dirs = [
        "../../../puppeteer-service",  # Relative to functions/getMacro
        "../../puppeteer-service",     # Relative to functions
        "../puppeteer-service",        # Relative to getMacro parent
        "./puppeteer-service",         # In current directory
    ]
    
    for dir_path in service_dirs:
        if os.path.exists(os.path.join(dir_path, "package.json")):
            return os.path.abspath(dir_path)
    
    return None

def start_puppeteer_service(port: int = 8080) -> subprocess.Popen:
    """Start the Puppeteer service on the specified port"""
    service_dir = find_puppeteer_service_dir()
    if not service_dir:
        raise FileNotFoundError("Could not find puppeteer-service directory")
    
    logger.info(f"Starting Puppeteer service from {service_dir} on port {port}")
    
    # Set environment variables for the service
    env = os.environ.copy()
    env["PORT"] = str(port)
    
    # Start the service in a separate process
    process = subprocess.Popen(
        ["npm", "start"],
        cwd=service_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for service to start (up to 30 seconds)
    start_time = time.time()
    timeout = 30  # seconds
    
    while time.time() - start_time < timeout:
        if is_service_running("localhost", port):
            logger.info(f"Puppeteer service started successfully on port {port}")
            return process
            
        # Check if process failed to start
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"Failed to start Puppeteer service: {stderr.decode('utf-8')}")
            
        # Wait a bit before checking again
        time.sleep(1)
        logger.info(f"Waiting for service to start... ({int(time.time() - start_time)}s)")
    
    # If we get here, the service didn't start in time
    raise TimeoutError(f"Puppeteer service didn't respond in {timeout} seconds")

def test_puppeteer_service(url: str = "https://www.google.com") -> bool:
    """Test the Puppeteer service with a simple screenshot request"""
    try:
        service_url = "http://localhost:8080"
        logger.info(f"Testing Puppeteer service with URL: {url}")
        
        # Prepare the request payload
        payload = {
            "symbol": "test",
            "url": url,
            "timeframe": "1d",
            "indicators": []
        }
        
        # Call the snapshot endpoint
        response = requests.post(
            f"{service_url}/snapshot", 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Check if successful
        if response.status_code != 200:
            logger.error(f"Test failed: HTTP {response.status_code}, {response.text}")
            return False
            
        # Parse the response
        response_data = response.json()
        
        # Check if we got the image data
        if "image_base64" not in response_data:
            logger.error(f"Test failed: No image data in response: {response_data}")
            return False
            
        logger.info("Puppeteer service test successful")
        return True
        
    except Exception as e:
        logger.exception(f"Error testing Puppeteer service: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Start and test Puppeteer service")
    parser.add_argument("--port", type=int, default=8080, help="Port for the service (default: 8080)")
    parser.add_argument("--test-url", default="https://www.google.com", help="URL to test with")
    parser.add_argument("--test-only", action="store_true", help="Only test the service, don't start it")
    args = parser.parse_args()
    
    if args.test_only:
        # Just test the service
        if is_service_running("localhost", args.port):
            logger.info(f"Puppeteer service is running on port {args.port}")
            if test_puppeteer_service(args.test_url):
                print("✅ Puppeteer service is working properly")
                return 0
            else:
                print("❌ Puppeteer service is running but failed the test")
                return 1
        else:
            print(f"❌ Puppeteer service is not running on port {args.port}")
            return 1
    else:
        # Start and test the service
        try:
            if is_service_running("localhost", args.port):
                logger.info(f"Puppeteer service is already running on port {args.port}")
            else:
                process = start_puppeteer_service(args.port)
                logger.info(f"Puppeteer service started with PID {process.pid}")
                
            # Test the service
            if test_puppeteer_service(args.test_url):
                print("✅ Puppeteer service is working properly")
                return 0
            else:
                print("❌ Puppeteer service started but failed the test")
                return 1
                
        except Exception as e:
            logger.exception(f"Error: {str(e)}")
            print(f"❌ Failed to start Puppeteer service: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main()) 