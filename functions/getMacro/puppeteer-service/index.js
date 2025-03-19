/**
 * Puppeteer Screenshot Microservice
 * Author: JP
 * Date: 2024-07-19
 */

const express = require('express');
const bodyParser = require('body-parser');
const puppeteer = require('puppeteer');

// Create Express app
const app = express();
const port = process.env.PORT || 8080;

// Parse JSON request bodies
app.use(bodyParser.json({ limit: '50mb' }));

// Status endpoint
app.get('/status', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'puppeteer-screenshot',
    timestamp: new Date().toISOString()
  });
});

// Screenshot endpoint
app.post('/snapshot', async (req, res) => {
  try {
    console.log(`Received snapshot request:`, req.body);
    
    // Extract parameters
    const { url, symbol } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'Missing required parameter: url' });
    }
    
    // Take screenshot
    console.log(`Taking screenshot of ${url}`);
    const screenshot = await takeScreenshot(url);
    
    // Return the screenshot as base64
    res.json({ 
      url: url,
      symbol: symbol || 'unknown',
      timestamp: new Date().toISOString(),
      image_base64: screenshot
    });
  } catch (error) {
    console.error('Error taking screenshot:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * Take a screenshot of the given URL
 * 
 * @param {string} url - The URL to take a screenshot of
 * @returns {Promise<string>} - Base64 encoded screenshot
 */
async function takeScreenshot(url) {
  let browser = null;
  
  try {
    console.log(`Launching browser...`);
    
    // Launch browser with appropriate options
    browser = await puppeteer.launch({
      headless: 'new',  // Use new headless mode
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ],
    });
    
    // Create a new page
    const page = await browser.newPage();
    
    // Set viewport size
    await page.setViewport({
      width: 1280,
      height: 1024,
      deviceScaleFactor: 1,
    });
    
    // Set default navigation timeout (1 minute)
    page.setDefaultNavigationTimeout(60000);
    
    // Navigate to URL
    console.log(`Navigating to ${url}`);
    await page.goto(url, {
      waitUntil: 'networkidle2',  // Wait until network is mostly idle
    });
    
    // Wait a bit for any remaining dynamic content
    await page.waitForTimeout(2000);
    
    // Take screenshot
    console.log(`Taking screenshot...`);
    const screenshot = await page.screenshot({
      type: 'png',
      fullPage: true,
      encoding: 'base64'
    });
    
    return screenshot;
  } catch (error) {
    console.error(`Error taking screenshot of ${url}:`, error);
    throw error;
  } finally {
    // Ensure browser is closed
    if (browser) {
      console.log(`Closing browser...`);
      await browser.close();
    }
  }
}

// Start the server
app.listen(port, () => {
  console.log(`Puppeteer screenshot service running on port ${port}`);
});

// Handle graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received: closing HTTP server');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received: closing HTTP server');
  process.exit(0);
}); 