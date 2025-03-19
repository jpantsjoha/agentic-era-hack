/**
 * Puppeteer Screenshot Module
 * Author: JP
 * Date: 2024-07-19
 */

const puppeteer = require('puppeteer');

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
    
    // Configure request interception to block unwanted resources
    await page.setRequestInterception(true);
    page.on('request', (request) => {
      // Block certain resource types to speed up the loading
      const resourceType = request.resourceType();
      if (['image', 'media', 'font'].includes(resourceType)) {
        request.abort();
      } else {
        request.continue();
      }
    });
    
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

module.exports = {
  takeScreenshot
}; 