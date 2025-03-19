#!/usr/bin/env python3
"""
[FILENAME] setup_and_run_puppeteer.py
[DESCRIPTION] Setup and run the Puppeteer screenshot service
Author: JP + [2024-07-19]
"""

import os
import sys
import subprocess
import logging
import argparse
import tempfile
import glob
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_puppeteer_service():
    """Install dependencies for the Puppeteer service"""
    try:
        # Get the directory of this script
        current_dir = Path(__file__).parent.absolute()
        puppeteer_dir = current_dir / "puppeteer-service"
        
        if not puppeteer_dir.exists():
            logger.error(f"Puppeteer service directory not found: {puppeteer_dir}")
            return False
            
        logger.info(f"Setting up Puppeteer service in {puppeteer_dir}")
        
        # Create a simple package.json and index.js if they don't exist
        # This avoids complex npm dependencies
        if not (puppeteer_dir / "package.json").exists():
            create_simplified_puppeteer_service(puppeteer_dir)
            return True
            
        # Run npm install with a timeout
        logger.info("Installing dependencies...")
        try:
            # Use a timeout to prevent hanging
            process = subprocess.run(
                ["npm", "install"], 
                cwd=puppeteer_dir,
                timeout=120,  # 2 minute timeout
                check=True
            )
            logger.info("Dependencies installed successfully")
            
            # Clean up any temporary files
            clean_temp_files(puppeteer_dir)
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("npm install timed out after 2 minutes")
            return False
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing dependencies: {e}")
        return False
    except Exception as e:
        logger.exception(f"Error setting up Puppeteer service: {str(e)}")
        return False

def clean_temp_files(directory):
    """Clean up any temporary npm files"""
    try:
        # Common patterns for npm temporary files
        patterns = [
            "*.tmp",
            "*.temp",
            "npm-debug.log*",
            "*.[0-9][0-9][0-9][0-9]",  # Files with 4 digits in name
            "*.[0-9][0-9][0-9][0-9][0-9]*"  # Files with 5+ digits in name
        ]
        
        count = 0
        for pattern in patterns:
            for file_path in glob.glob(str(directory / pattern)):
                try:
                    os.remove(file_path)
                    count += 1
                except:
                    pass
                    
        if count > 0:
            logger.info(f"Cleaned up {count} temporary files")
            
    except Exception as e:
        logger.warning(f"Error cleaning temporary files: {str(e)}")

def create_simplified_puppeteer_service(directory):
    """Create a simplified Puppeteer service with minimal dependencies"""
    logger.info("Creating simplified Puppeteer service...")
    
    # Create package.json
    with open(directory / "package.json", "w") as f:
        f.write('''{
  "name": "simple-puppeteer-service",
  "version": "1.0.0",
  "description": "Simple screenshot service",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "puppeteer": "^21.5.0"
  }
}''')
    
    # Create index.js
    with open(directory / "index.js", "w") as f:
        f.write('''const express = require('express');
const puppeteer = require('puppeteer');
const app = express();
const port = process.env.PORT || 8080;

app.use(express.json());

app.get('/status', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.post('/snapshot', async (req, res) => {
  try {
    const { url, symbol } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }
    
    console.log(`Taking screenshot of ${url}`);
    const browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 1024 });
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    
    const screenshot = await page.screenshot({ 
      encoding: 'base64',
      fullPage: true
    });
    
    await browser.close();
    
    res.json({ 
      url, 
      symbol: symbol || 'unknown',
      timestamp: new Date().toISOString(),
      image_base64: screenshot
    });
  } catch (error) {
    console.error(`Error: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`Simple Puppeteer service running on port ${port}`);
});''')
    
    logger.info("Simplified Puppeteer service created successfully")
    return True

def run_puppeteer_service(port=8080):
    """Run the Puppeteer service"""
    try:
        # Get the directory of this script
        current_dir = Path(__file__).parent.absolute()
        puppeteer_dir = current_dir / "puppeteer-service"
        
        if not puppeteer_dir.exists():
            logger.error(f"Puppeteer service directory not found: {puppeteer_dir}")
            return False
            
        logger.info(f"Starting Puppeteer service on port {port}...")
        
        # Set environment variables
        env = os.environ.copy()
        env["PORT"] = str(port)
        
        # Run npm start
        process = subprocess.Popen(
            ["node", "index.js"],  # Using node directly instead of npm start
            cwd=puppeteer_dir,
            env=env
        )
        
        logger.info(f"Puppeteer service started with PID {process.pid}")
        
        # Give it a moment to start
        time.sleep(1)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error("Failed to start Puppeteer service - process exited immediately")
            return False
        
        # Print the URL
        print(f"\n🚀 Puppeteer screenshot service running at http://localhost:{port}")
        print("Press Ctrl+C to stop the service\n")
        
        # Wait for the process to complete
        process.wait()
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
        return True
    except Exception as e:
        logger.exception(f"Error running Puppeteer service: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Setup and run Puppeteer screenshot service")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the service on")
    parser.add_argument("--setup-only", action="store_true", help="Only install dependencies, don't run the service")
    args = parser.parse_args()
    
    # Clean any temporary files in the current directory
    current_dir = Path(__file__).parent.absolute()
    puppeteer_dir = current_dir / "puppeteer-service"
    if puppeteer_dir.exists():
        clean_temp_files(puppeteer_dir)
    
    if args.setup_only:
        if setup_puppeteer_service():
            print("✅ Puppeteer service setup completed successfully")
            return 0
        else:
            print("❌ Puppeteer service setup failed")
            return 1
    else:
        if setup_puppeteer_service():
            if run_puppeteer_service(args.port):
                return 0
            else:
                print("❌ Failed to run Puppeteer service")
                return 1
        else:
            print("❌ Puppeteer service setup failed")
            return 1

if __name__ == "__main__":
    sys.exit(main()) 