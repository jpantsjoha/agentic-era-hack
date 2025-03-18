# getMacro Cloud Function

**Author**: JP + [2024-07-19]

> **Architecture Decision Record**: ADR-001-GetMacro

## Overview

The `getMacro` function is responsible for fetching, processing, and storing macroeconomic data for the Agent-Era-Hackathon. This function runs hourly to ensure up-to-date macroeconomic information is available.

## Implementation Notes

The function uses Puppeteer for screenshots of financial websites and Gemini Flash 2.0 for AI-powered data extraction. Data is processed and stored in a structured JSON format in Google Cloud Storage.

- Processes URLs listed in `DataSources.text`, one per line
- Uses DEBUG level logging with tabular output for local execution
- Writes consolidated results to `LatestMacroData.json` in the MacroData-Extracts bucket

## Data Requirements

The function extracts key economic indicators that are essential for macroeconomic regime classification:

| Indicator Category | Key Metrics | Importance |
|-------------------|-------------|------------|
| Interest Rates | Fed Funds Rate, 10Y Yield, 2Y Yield, Yield Spread | Core indicators for monetary policy stance |
| Inflation | CPI YoY, PCE, Inflation Composite | Critical for regime detection |
| Growth | GDP, PMI Manufacturing | Business cycle indicators |
| Employment | Unemployment Rate, Nonfarm Payrolls | Labor market health |
| Market | S&P 500, NASDAQ, Dow Jones, VIX | Market sentiment |
| Money Supply | M2, M2 YoY Change | Liquidity conditions |

These indicators are specifically chosen to enable accurate classification of the current macroeconomic regime (Expansion, Stagflation, Slowdown, Disinflationary Boom) based on the directional changes in growth and inflation metrics.

### Forward Guidance Indicators

Several indicators serve as forward-looking signals, providing early warnings of economic shifts:

- **Yield Spread (10Y-2Y)**: The yield curve inversion (negative spread) has historically preceded recessions by 12-18 months with remarkable accuracy. When short-term rates exceed long-term rates, it signals market expectations of economic contraction.

- **PMI Manufacturing**: Readings below 50 indicate contraction, and this metric often leads GDP changes by 3-6 months. The PMI is particularly valuable as a real-time indicator of business sentiment and future production plans.

- **M2 YoY Change**: Significant shifts in money supply growth often lead inflation and economic activity by 6-12 months. The rate of change in M2 serves as an early indicator of liquidity conditions that will affect markets and the broader economy.

- **Inflation Composite**: By combining CPI data with the yield spread, this composite indicator provides a more nuanced view of inflationary pressures and expectations. This helps detect regime shifts earlier than looking at CPI alone.

- **VIX (Volatility Index)**: Known as the "fear gauge," spikes in the VIX often precede market corrections and can signal changing economic conditions before they appear in traditional economic data.

By tracking directional changes in these indicators rather than absolute values, the getMacro function provides valuable forward guidance for anticipating transitions between economic regimes. This forward-looking perspective is essential for strategic investment decisions and policy analysis.

## Tabular Output Format

When running in local mode with DEBUG logging, the function outputs data in a structured tabular format:

```
+------------------+------------+------------+----------+
| Indicator        | Value      | Source     | Status   |
+==================+============+============+==========+
| GDP Growth       | 2.50%      | BEA        | OK       |
| PMI              | 48.70      | yfinance   | OK       |
| CPI YoY          | 3.20%      | FRED       | OK       |
| 10Y Yield        | 4.25%      | FRED       | OK       |
| 2Y Yield         | 4.85%      | FRED       | OK       |
| Yield Spread     | -0.60%     | CME        | OK       |
| Inflation Comp.  | 1.30%      | CME        | OK       |
| M2 Money Supply  | 20,952.1B  | FRED       | OK       |
| M2 YoY Change    | -1.80%     | CME        | OK       |
| Fed Funds Rate   | 5.33%      | FRED       | OK       |
| S&P 500          | 4,783.45   | yfinance   | OK       |
| Dow Jones        | 37,592.13  | yfinance   | OK       |
| NASDAQ           | 16,795.20  | yfinance   | OK       |
| VIX              | 13.25      | yfinance   | OK       |
+------------------+------------+------------+----------+

+------------------------+
| Computed Regime        |
+========================+
| Slowdown (Deflationary)|
+------------------------+
```

This format provides a comprehensive overview of current economic conditions and the computed macroeconomic regime, which is essential for economic analysis and decision-making.

## Environment Requirements

The function requires the following environment variables:

- `GEMINI_API_KEY`: API key for Google's Gemini Pro Vision model
- `PUPPETEER_SERVICE_URL`: URL of the Puppeteer screenshot service (defaults to http://localhost:8080)

When running locally, these can be set in your shell environment:

```bash
export GEMINI_API_KEY=your_api_key_here
export PUPPETEER_SERVICE_URL=http://localhost:8080
```

When deployed as a Cloud Function, these should be configured as environment variables or secret references.

## Puppeteer Service Setup

The getMacro function requires a running Puppeteer service for website screenshots. You have several options to set this up:

### Option 1: Automatic Startup (Recommended for Local Development)

The function will attempt to automatically start the Puppeteer service if it's not already running. This is handled by the `rate_forecast_puppeteer.py` module, which:

1. Checks if the service is running at the configured URL
2. If not, attempts to start it from the `puppeteer-service` directory
3. Verifies the service is working by testing it with a simple screenshot request

### Option 2: Manual Setup and Start

For more control, you can manually set up and start the service:

1. Set up the service once:
   ```bash
   python setup_and_run_puppeteer.py --setup-only
   ```

2. Start the service on demand:
   ```bash
   python start_puppeteer_service.py
   ```

3. Verify the service is running:
   ```bash
   python start_puppeteer_service.py --test-only
   ```

### Option 3: Direct NPM Commands

You can also manage the service directly using npm:

```bash
cd puppeteer-service
npm install                # One-time setup
npm start                  # Start the service
```

### Cloud Deployment

For production use, deploy the Puppeteer service to Cloud Run:

```bash
cd puppeteer-service

# Build the container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/puppeteer-service

# Deploy to Cloud Run
gcloud run deploy puppeteer-service \
  --image gcr.io/YOUR_PROJECT_ID/puppeteer-service \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi
```

Then set the `PUPPETEER_SERVICE_URL` environment variable to the deployed service URL when deploying the Cloud Function.

## DataSources Configuration

The function reads URLs from a `DataSources.text` file, which should be formatted as follows:

```
# Lines starting with # are comments
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
https://fred.stlouisfed.org/series/DFF
https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html
# Add more URLs as needed
```

Each URL will be processed in sequence: a screenshot is taken, then analyzed by Gemini Flash 2.0.

## HLD

```bash
                                   +-----------------------------+
                                   |  Financial/Economic         |
                                   |  Websites (Data Sources)    |
                                   +-------------+--------------+
                                                 |
                                                 | Web Scraping
                                                 ▼
+--------------------------------+  +-----------------------------+  +------------------------+
|                                |  |                             |  |                        |
|  DataSources.text              |  |  getMacro Cloud Function    |  |  Google Cloud Storage  |
|  (List of URLs to process)     +->|  - Puppeteer screenshots    |  |  MacroData-Extracts   |
|                                |  |  - Gemini Flash 2.0 analysis+->|  LatestMacroData.json |
+--------------------------------+  |  - Data compilation         |  |                        |
                                    +-------------+---------------+  +----------+-------------+
```

## Running the Function Locally

To run the function locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   export GEMINI_API_KEY=your_api_key_here
   ```

3. Create a DataSources.text file with URLs to process:
   ```bash
   echo "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm" > DataSources.text
   echo "https://fred.stlouisfed.org/series/DFF" >> DataSources.text
   ```

4. Run the function:
   ```bash
   python main.py --local
   ```

Optional flags:
- `--dry-run`: Don't store results to GCS
- `--verbose`: Print detailed output
- `--debug`: Enable DEBUG level logging with tabular output

## Deploying as a Cloud Function

To deploy the function to Google Cloud:

```bash
gcloud functions deploy getMacro \
  --runtime python311 \
  --trigger-http \
  --entry-point run \
  --memory 256MB \
  --timeout 540s \
  --set-env-vars GEMINI_API_KEY=your_api_key_here \
  --set-env-vars PUPPETEER_SERVICE_URL=https://your-puppeteer-service-url
```

For better security, use Secret Manager for API keys:

```bash
gcloud functions deploy getMacro \
  --runtime python311 \
  --trigger-http \
  --entry-point run \
  --memory 256MB \
  --timeout 540s \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

## Data Structure

The function outputs a JSON file to GCS with the following structure:

```json
{
  "metadata": {
    "date": "2024-07-20T15:30:00.000Z",
    "timestamp": "2024-07-20T15:30:00.000Z",
    "provider": "COMPOSITE",
    "sources": ["https://example.com/economics", "https://example.com/rates"],
    "validation": {
      "status": "OK",
      "missing_fields": [],
      "warnings": []
    }
  },
  "data": [
    {
      "source": "example.com",
      "url": "https://example.com/economics",
      "method": "puppeteer_gemini",
      "timestamp": "2024-07-20 15:30:00",
      "data": {
        "interest_rates": {
          "fed_funds_rate": "5.50%",
          "treasury_10y": "4.25%"
        },
        "inflation": {
          "cpi_yoy": "3.2%"
        }
      }
    }
  ]
}
```

## Macroeconomic Regimes

The function calculates the current macroeconomic regime based on the extracted data:

1. **Expansion (Reflation)**: Growth ↑, Inflation ↑
2. **Stagflation Risk**: Growth ↓, Inflation ↑ 
3. **Slowdown (Deflationary)**: Growth ↓, Inflation ↓
4. **Disinflationary Boom**: Growth ↑, Inflation ↓

This classification is critical for investment strategy and economic forecasting.

## Troubleshooting

Common issues:

1. **Puppeteer service not starting**:
   - Check if Node.js is installed and accessible in your PATH
   - Ensure there are no other services running on port 8080
   - Look for errors in the console when starting the service 
   - Try starting it manually with `cd puppeteer-service && npm start`

2. **Missing API key**: Verify that the GEMINI_API_KEY environment variable is set correctly.

3. **DataSources.text not found**: Ensure the file exists in the same directory as main.py or provide the full path when running.

4. **GCS bucket doesn't exist**: Create the MacroData-Extracts bucket in your GCP project or update the bucket name in the code.

5. **Timeout errors**: If processing certain URLs takes too long, you may need to increase the timeout values in the Puppeteer service configuration.

6. **Missing indicators**: If specific indicators are missing in the output, verify that the DataSources.text file includes URLs that contain that data, and that Gemini Flash 2.0 can correctly extract it from the screenshots.
