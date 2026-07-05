# AI-Powered Earnings & Sentiment Analyzer

A Streamlit application that uses Claude 3.5 Sonnet to perform structured, quantitative sentiment analysis on corporate earnings call transcripts. Built as a portfolio project for a Quantitative Analyst role.

## What It Does

Paste the raw text of an earnings call transcript, and the app returns a structured analyst-style dashboard:

- **Overall Sentiment Score** (1-10 scale, bearish to bullish)
- **Forward Revenue Guidance** summary
- **Top 3 Risk Factors** extracted from the call, in a sortable table

Claude is prompted to act as an elite quantitative equity analyst and to return a strict, schema-locked JSON object, which the app parses and renders directly into the dashboard.

## Tech Stack

- Python 3.9+
- [Streamlit](https://streamlit.io/) — UI and response caching
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) — Claude 3.5 Sonnet API access
- [pandas](https://pandas.pydata.org/) — structuring the risk factor output

## Setup

1. Clone this repository and navigate into it.

2. (Recommended) Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:

   ```bash
   streamlit run app.py
   ```

5. In the sidebar, enter your Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com)). The key is used only in-session and is never stored or logged.

## Usage

1. Paste a full earnings call transcript into the text area.
2. Click **Analyze Transcript**.
3. Review the sentiment score, revenue guidance, and risk factor table.

## Design Notes

**Cost control via caching.** The Anthropic API call is wrapped in `@st.cache_data(show_spinner=False)`, keyed on the `(api_key, transcript)` pair. Streamlit reruns the entire script on every UI interaction, so without this decorator, unrelated widget clicks would re-trigger — and re-bill — the same API call. Only a genuinely new API key or transcript invalidates the cache.

**Strict JSON contract.** The system prompt locks Claude into returning a single raw JSON object matching an exact schema (no markdown fences, no prose). The app still defensively strips stray code fences and validates that all required keys are present before rendering, so a malformed or partial model response fails with a clear on-screen error instead of crashing.

**Error handling.** Missing API keys, empty transcripts, JSON parse failures, and Anthropic API errors (auth, rate limits, connectivity) are all caught and surfaced via `st.warning` / `st.error`, rather than raising unhandled exceptions.

## Disclaimer

This tool is a portfolio/demo project. Sentiment scores and risk factors are AI-generated interpretations of transcript text and should not be used as the sole basis for investment decisions.
