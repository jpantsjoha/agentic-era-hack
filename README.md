
# About



## market-conditions-agent

A agent implementing a base ReAct agent using LangGraph
Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack)

## HLD

```
               +-----------------------------+
               | Research Reports, Macro    |
               | Data, Market Charts        |
               +-------------+--------------+
                             |
                (1) Upload or Update into GCS
                             |
                             v
                  +---------------------------+
                  |   Google Cloud Storage   |
                  |           (GCS)          |
                  +-----------+---------------+
                              |
                      (2) Hourly Batch Trigger
                              |
                              v
                  +---------------------------+
                  | Orchestrator / Core      |
                  | Engine                   |
                  +------------+-------------+
                               |
     +-------------------------+-------------------------+
     |                       |                          |
     v                       v                          v
 +-----------+         +-----------+              +-----------+
 |  Macro    |         | Sentiment |              | Market    |
 | Analysis  |         | Analysis  |              | Performance
 |  Agent    |         |  Agent    |              |  Agent    |
 +-----------+         +-----------+              +-----------+
                               |
                     (3) Write evaluation/JSON to GCS
                               |
                               v
                   +----------------------------+
                   | Consolidated Output in GCS|
                   +-------------+--------------+
                                 |
                       +------------------------+
                       |   Streamlit UI        |
                       |  - Reads final data   |
                       |  - Chat-like queries  |
                       +----------+------------+
                                  |
                               (4) Display
                                  |
                                  v
                           +-------------+
                           |    User     |
                           +-------------+


```

# MarketConditionsAgent

A proof-of-concept AI-driven application providing *forward guidance* on macroeconomic and market conditions. This project is part of an Agentic-Era Hackathon demo: it ingests research data, analyses market sentiment, evaluates stock performance, and generates an outlook (with probabilities) for bullish, neutral, or bearish scenarios.

## About the Project

**MarketConditionsAgent** is designed as a go-to analyst for queries on macroeconomic conditions and the business cycle. By leveraging multiple data sources (research reports, macro metrics, and market performance), it can produce:

- **Short feedback reports** – Quick insights into the market environment.
- **Heatmap or chart-based performance** – Snapshot views of major indexes (e.g., SPX) or industry sectors.
- **Forward Guidance** – A probability-weighted outlook (bullish, neutral, or bearish), informed by Federal Reserve rates, inflation, labour market data, and forward-looking indicators (such as PMIs).

Users primarily interact through a **Streamlit** UI with a chatbot-like interface, posing questions such as:
- *Is the SPX near its bottom?*
- *How will upcoming rate decisions affect the tech sector?*

The system retrieves data from Google Cloud Storage (GCS) where raw and processed data is stored, combining **macro analysis**, **sentiment analysis**, and **market chart evaluation** into a concise answer.

## Solution Value Proposition

1. **Rapid Market Assessment**  
   By automating the gathering and processing of research reports, macro statistics, and market data, MarketConditionsAgent enables near real-time evaluations of the overall economic climate.

2. **Transparent Scenario Outlook**  
   Each recommendation includes a breakdown into bullish, mean, or bearish probabilities, along with key drivers (e.g., interest rates, inflation, labour market status).

3. **Centralised Knowledge Base**  
   Relevant data is consolidated in a single repository (GCS), facilitating versioning, comparisons of past vs. present conditions, and consistent analysis.

4. **Flexible User Experience**  
   The solution offers:
   - A *Streamlit* chat-style interface for ad-hoc queries.
   - Visual dashboards or heatmaps for quick glimpses of market movements.
   - Automated summaries for deeper investigation.

5. **Scalable and Modular Architecture**  
   - **Agents**: Specialised modules for macro data, sentiment, and market performance can be updated or replaced independently.
   - **Orchestrator**: Schedules and coordinates agent outputs, storing results in a common data layer.

## Table of Contents
1. [Use Cases](#use-cases)
2. [Setup & Installation](#setup--installation)
3. [How to Run](#how-to-run)
4. [Future Enhancements](#future-enhancements)

## Use Cases

1. *Is this the SPX bottom?*  
   - The user prompts the system in Streamlit.
   - Agents evaluate rate trends, inflation data, sentiment polarity, and SPX charts.
   - Responds with probability-weighted scenarios plus short or extended commentary.

2. *Forward Guidance*  
   - The user can query possible impacts of rate hikes on specific sectors.
   - The system summarises relevant macro data, labour market dynamics, and historical performance patterns.

## Setup & Installation

1. **Clone the Repository**  
   `git clone git@github.com:<your-org>/agentic-era-gcp.git`  
   `cd MarketConditionsAgent`

2. **Install Requirements**  
   `pip install -r requirements.txt`

3. **Configure GCS Access**  
   - Use service account credentials or environment variables for Cloud Storage.
   - Update `.env` or `config.yaml` with bucket names and credentials.

4. **Streamlit Configuration**  
   - Modify `streamlit_app.py` to set environment variables for local or production usage.

## How to Run

1. **Local Test**  
   `python orchestrator.py`  
   Manually triggers a single run of data ingestion and agent evaluation.

2. **Streamlit UI**  
   `streamlit run streamlit_app.py`  
   Launches the local web UI at http://localhost:8501

3. **Production Schedule**  
   - Use a cron job, Cloud Scheduler, or a CI pipeline to run `orchestrator.py` every hour.
   - Validate logs and final outputs in GCS.

## Future Enhancements

- **Sector-Specific Analysis**  
  Tag or categorise sentiment by industry for finer-grained insights.

- **Advanced Forecasting Models**  
  Add ARIMA, LSTM, or Transformer-based approaches to enhance predictive accuracy.

- **Real-Time Dashboards**  
  Implement near-real-time data pipelines with streaming frameworks.

- **User Overrides**  
  Let users modify assumptions (e.g., upcoming interest rate changes) and observe updated scenario probabilities.

*Enjoy exploring the future of market guidance! For any questions, please open an issue or submit a pull request.*


## Project Structure

This project is organized as follows:

```
market-conditions-agent/
├── app/                 # Core application code
│   ├── agent.py         # Main agent logic
│   ├── server.py        # FastAPI Backend server
│   └── utils/           # Utility functions and helpers
├── deployment/          # Infrastructure and deployment scripts
├── notebooks/           # Jupyter notebooks for prototyping and evaluation
├── tests/               # Unit, integration, and load tests
├── Makefile             # Makefile for common commands
└── pyproject.toml       # Project dependencies and configuration
```

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager - [Install](https://docs.astral.sh/uv/getting-started/installation/)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)


### Installation

Install required packages using uv:

```bash
make install
```

### Setup

If not done during the initialization, set your default Google Cloud project and Location:

```bash
export PROJECT_ID="YOUR_PROJECT_ID"
export LOCATION="us-central1"
gcloud config set project $PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project $PROJECT_ID
```

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make install`       | Install all required dependencies using uv                                                  |
| `make playground`    | Launch local development environment with backend and frontend |
| `make backend`       | Start backend server only |
| `make ui`            | Launch Streamlit frontend without local backend |
| `make test`          | Run unit and integration tests                                                              |
| `make lint`          | Run code quality checks (codespell, ruff, mypy)                                             |
| `uv run jupyter lab` | Launch Jupyter notebook                                                                     |

For full command options and usage, refer to the [Makefile](Makefile).


## Usage

1. **Prototype:** Build your Generative AI Agent using the intro notebooks in `notebooks/` for guidance. Use Vertex AI Evaluation to assess performance.
2. **Integrate:** Import your chain into the app by editing `app/agent.py`.
3. **Test:** Explore your chain's functionality using the Streamlit playground with `make playground`. The playground offers features like chat history, user feedback, and various input types, and automatically reloads your agent on code changes.
4. **Deploy:** Configure and trigger the CI/CD pipelines, editing tests if needed. See the [deployment section](#deployment) for details.
5. **Monitor:** Track performance and gather insights using Cloud Logging, Tracing, and the Looker Studio dashboard to iterate on your application.


## Deployment

### Dev Environment

The repository includes a Terraform configuration for the setup of the Dev Google Cloud project.
See [deployment/README.md](deployment/README.md) for instructions.

### Production Deployment

The repository includes a Terraform configuration for the setup of a production Google Cloud project. Refer to [deployment/README.md](deployment/README.md) for detailed instructions on how to deploy the infrastructure and application.

## Monitoring and Observability

>> You can use [this Looker Studio dashboard](https://lookerstudio.google.com/c/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f/page/tEnnC) template for visualizing events being logged in BigQuery. See the "Setup Instructions" tab to getting started.

The application uses OpenTelemetry for comprehensive observability with all events being sent to Google Cloud Trace and Logging for monitoring and to BigQuery for long term storage. 
