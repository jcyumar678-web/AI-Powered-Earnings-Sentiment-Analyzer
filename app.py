"""
AI-Powered Earnings & Sentiment Analyzer
------------------------------------------
A single-file Streamlit application that uses Claude 3.5 Sonnet to perform
structured sentiment analysis on corporate earnings call transcripts.

Portfolio project for a Quantitative Analyst application.
"""

import json

import pandas as pd
import streamlit as st
from anthropic import Anthropic

# ------------------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Earnings & Sentiment Analyzer",
    page_icon="📈",
    layout="wide",
)

# ------------------------------------------------------------------------------
# SYSTEM PROMPT
# ------------------------------------------------------------------------------
# This is the core "prompt engineering" of the app. We pin Claude into a narrow,
# well-defined role (elite quant equity analyst) and give it a rigid output
# contract. Constraining the persona AND the schema in the same prompt reduces
# variance in the response and makes downstream JSON parsing reliable.
SYSTEM_PROMPT = """You are an elite quantitative equity analyst at a top-tier institutional
wealth management firm. You specialize in extracting objective, decision-useful signal from
corporate earnings call transcripts for use in systematic trading and portfolio construction
models.

You will be given the raw text of an earnings call transcript. Analyze it with the rigor,
skepticism, and precision expected of a senior sell-side/buy-side analyst. Do not be swayed by
management's tone alone -- weigh hedging language, forward guidance changes, and risk
disclosures as heavily as headline numbers.

CRITICAL OUTPUT INSTRUCTIONS:
You must respond with ONLY a single raw JSON object. Do not include markdown code fences
(no ```json), do not include any prose, preamble, or explanation before or after the JSON.
Your entire response must be valid, directly parsable JSON matching this EXACT schema:

{
  "Company_Name": "<string: the company name identified in the transcript>",
  "Overall_Sentiment_Score": <integer 1-10, where 1 is extremely bearish and 10 is extremely bullish>,
  "Forward_Revenue_Guidance": "<string: a single-sentence summary of the forward revenue outlook>",
  "Top_3_Risk_Factors": ["<string>", "<string>", "<string>"]
}

Rules:
- "Overall_Sentiment_Score" must be an integer between 1 and 10 inclusive.
- "Top_3_Risk_Factors" must contain exactly 3 concise strings, ranked by materiality.
- Output nothing outside the JSON object. No trailing commentary.
"""


# ------------------------------------------------------------------------------
# CACHED API CALL
# ------------------------------------------------------------------------------
# COST-CONTROL MECHANISM:
# Streamlit reruns the ENTIRE script top-to-bottom on every widget interaction
# (e.g., clicking a different button, toggling a checkbox elsewhere on the page).
# Without caching, that rerun would re-fire the Anthropic API call every single
# time -- burning tokens/credits for no reason, even if the transcript and API
# key haven't changed.
#
# @st.cache_data(show_spinner=False) memoizes this function's return value,
# keyed on a hash of its input arguments (api_key, transcript). As long as the
# user passes the same api_key + transcript combination, Streamlit will serve
# the cached result instantly instead of hitting the network. Only a genuinely
# new API key or new transcript text will trigger a fresh (billable) API call.
# `show_spinner=False` is used here because we manage our own spinner UX in the
# calling code below.
@st.cache_data(show_spinner=False)
def get_ai_analysis(api_key: str, transcript: str) -> str:
    """
    Connects to the Anthropic API and requests structured sentiment analysis
    of an earnings call transcript.

    Args:
        api_key: The user's Anthropic API key (used as part of the cache key,
                  so switching keys correctly invalidates the cache).
        transcript: Raw earnings call transcript text.

    Returns:
        The raw text content of Claude's response (expected to be a JSON string).
    """
    client = Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        temperature=0,  # Deterministic output is preferred for structured/financial extraction tasks
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the earnings call transcript to analyze:\n\n{transcript}",
            }
        ],
    )

    # response.content is a list of content blocks; we expect a single text block
    # containing the raw JSON string per our system prompt instructions.
    return response.content[0].text


# ------------------------------------------------------------------------------
# SIDEBAR: API KEY INPUT
# ------------------------------------------------------------------------------
with st.sidebar:
    st.header("🔑 API Configuration")
    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Your key is used only for this session and is never stored or logged.",
    )
    st.caption(
        "Get a key at console.anthropic.com. Standard API usage charges apply per request."
    )

# ------------------------------------------------------------------------------
# MAIN BODY: TITLE + TRANSCRIPT INPUT
# ------------------------------------------------------------------------------
st.title("📈 AI-Powered Earnings & Sentiment Analyzer")
st.write(
    "Paste a raw earnings call transcript below. Claude will act as a quantitative "
    "equity analyst and extract a structured sentiment signal, forward guidance summary, "
    "and top risk factors."
)

transcript_input = st.text_area(
    "Earnings Call Transcript",
    height=300,
    placeholder="Paste the full transcript text here...",
)

analyze_clicked = st.button("Analyze Transcript", type="primary")

# ------------------------------------------------------------------------------
# WORKFLOW: VALIDATE -> CALL API -> PARSE -> RENDER DASHBOARD
# ------------------------------------------------------------------------------
if analyze_clicked:
    # --- Input validation / graceful error handling ---
    if not api_key_input:
        st.warning("⚠️ Please enter your Anthropic API key in the sidebar to proceed.")
    elif not transcript_input.strip():
        st.warning("⚠️ Please paste a transcript into the text area before analyzing.")
    else:
        try:
            with st.spinner("Analyzing transcript with Claude 3.5 Sonnet..."):
                raw_response = get_ai_analysis(api_key_input, transcript_input)

            # --------------------------------------------------------------------
            # JSON PARSING LOGIC
            # --------------------------------------------------------------------
            # Even with a strict system prompt, LLMs can occasionally wrap output
            # in markdown fences (```json ... ```) or add stray whitespace. We
            # defensively strip common fence patterns before handing the string
            # to json.loads(), which raises json.JSONDecodeError on malformed
            # input -- this is caught below and surfaced to the user cleanly
            # rather than crashing the app.
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```"):
                # Remove opening fence (``` or ```json) and closing fence
                cleaned_response = cleaned_response.strip("`")
                cleaned_response = cleaned_response.replace("json", "", 1).strip()

            data = json.loads(cleaned_response)

            # --------------------------------------------------------------------
            # SCHEMA VALIDATION
            # --------------------------------------------------------------------
            # Confirm all expected keys are present before rendering, so a
            # partial/malformed model response fails loudly and specifically
            # rather than raising an opaque KeyError deep in the UI code.
            required_keys = [
                "Company_Name",
                "Overall_Sentiment_Score",
                "Forward_Revenue_Guidance",
                "Top_3_Risk_Factors",
            ]
            missing_keys = [k for k in required_keys if k not in data]
            if missing_keys:
                st.error(
                    f"❌ AI response was missing expected fields: {missing_keys}. "
                    "Try re-running the analysis."
                )
                st.code(raw_response, language="text")
            else:
                # ----------------------------------------------------------------
                # DASHBOARD RENDERING
                # ----------------------------------------------------------------
                st.divider()
                st.subheader(f"Analysis Results: {data['Company_Name']}")

                # --- Top-line sentiment metric ---
                score = int(data["Overall_Sentiment_Score"])
                # Delta text gives quick visual context on the 1-10 scale without
                # needing a separate chart.
                if score >= 7:
                    sentiment_label = "Bullish"
                elif score >= 4:
                    sentiment_label = "Neutral"
                else:
                    sentiment_label = "Bearish"

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric(
                        label="Overall Sentiment Score (1-10)",
                        value=f"{score}/10",
                        delta=sentiment_label,
                    )

                # --- Forward revenue guidance ---
                with col2:
                    st.info(f"**Forward Revenue Guidance:** {data['Forward_Revenue_Guidance']}")

                # --- Top 3 risk factors as a DataFrame ---
                st.subheader("Top 3 Risk Factors")
                risks = data["Top_3_Risk_Factors"]
                risk_df = pd.DataFrame(
                    {
                        "Rank": range(1, len(risks) + 1),
                        "Risk Factor": risks,
                    }
                )
                st.dataframe(risk_df, use_container_width=True, hide_index=True)

                # --- Raw JSON for transparency / debugging ---
                with st.expander("View Raw JSON Response"):
                    st.json(data)

        except json.JSONDecodeError:
            # Thrown by json.loads() when Claude's output isn't valid JSON
            # (e.g., it added commentary despite instructions). Surface the raw
            # text so the user can see exactly what came back.
            st.error("❌ Failed to parse the AI's response as JSON. Raw response below:")
            st.code(raw_response, language="text")

        except Exception as e:
            # Catches API-level errors: invalid API key, rate limits, network
            # issues, etc. Anthropic's SDK raises typed exceptions (e.g.
            # AuthenticationError, APIConnectionError) that all inherit from
            # Exception, so this broad catch keeps the app from crashing while
            # still surfacing the underlying error message to the user.
            st.error(f"❌ An error occurred while contacting the Anthropic API: {e}")
