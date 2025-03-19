#!/bin/bash

# Puppeteer Service Setup Script
# Author: JP
# Date: 2024-07-19

echo "Setting up Puppeteer screenshot service..."

# Install dependencies
npm install

# Install Puppeteer browser if it doesn't exist
node -e "
const puppeteer = require('puppeteer');
(async () => {
  try {
    console.log('Checking Puppeteer browser installation...');
    const browser = await puppeteer.launch();
    await browser.close();
    console.log('Puppeteer browser is already installed.');
  } catch (error) {
    console.log('Installing Puppeteer browser...');
    await puppeteer.install();
    console.log('Puppeteer browser installation complete.');
  }
})();
"

echo "Setup complete! Run 'npm start' to start the service." 