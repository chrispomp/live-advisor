import os
import json
from alpha_vantage.timeseries import TimeSeries
from google.cloud import bigquery
from google.cloud import aiplatform_v1beta1 as aiplatform

# --- Configuration ---
# Assumes GOOGLE_CLOUD_PROJECT is set in the environment.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo") # Use 'demo' for testing, but expect a real key in prod
BIGQUERY_DATASET = "fsi-banking-agentspace.awm" # As per REQ-202
VERTEX_AI_SEARCH_DATASTORE_ID = "citi_perspectives_datastore" # A placeholder datastore ID

# Initialize clients
bq_client = bigquery.Client(project=PROJECT_ID)
vertex_ai_search_client = aiplatform.SearchServiceClient()

def get_user_portfolio_summary(client_id: str) -> str:
    """
    Retrieves the user's portfolio summary from the BigQuery holdings table.

    Args:
        client_id: The authenticated user's client ID.

    Returns:
        A JSON string with the total market value and top 3 holdings,
        or a message indicating that the portfolio could not be retrieved.
    """
    query = f\"\"\"
        SELECT
            h.ticker,
            h.security_name,
            h.market_value
        FROM
            `{PROJECT_ID}.{BIGQUERY_DATASET}.holdings` AS h
        WHERE
            h.client_id = @client_id
        ORDER BY
            h.market_value DESC
        LIMIT 3;
    \"\"\"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("client_id", "STRING", client_id),
        ]
    )
    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = query_job.result()

        holdings = list(results)
        if not holdings:
            return json.dumps({"message": "I could not retrieve your portfolio data at this time."})

        # Calculate total market value (this requires a separate query or assumption)
        # For this implementation, we'll assume the total value is a sum of all holdings,
        # which is not explicitly in the top 3 query. A real implementation would need a separate query.
        # Here we just sum the top 3 for demonstration.
        total_market_value = sum(h.market_value for h in holdings)

        response = {
            "total_market_value": total_market_value,
            "top_holdings": [
                {"ticker": h.ticker, "security_name": h.security_name, "market_value": h.market_value}
                for h in holdings
            ],
        }
        return json.dumps(response)
    except Exception as e:
        print(f"Error querying BigQuery: {e}")
        return json.dumps({"error": "An error occurred while retrieving portfolio data."})


def get_market_news_and_sentiment(topic: str) -> str:
    """
    Fetches the latest news articles and sentiment for a given topic or company ticker.

    Args:
        topic: The company ticker or topic to search for.

    Returns:
        A JSON string summarizing up to 5 news articles, including title, summary, and sentiment.
    """
    # Note: The alpha_vantage library doesn't directly provide a news/sentiment API in this form.
    # This function simulates the expected output based on a hypothetical API call.
    # A real implementation would use a news API like Alpha Vantage's or another provider.
    try:
        # This is a placeholder for a real API call.
        # The Alpha Vantage API for news is called "News & Sentiments".
        # from alpha_vantage.fundamentaldata import FundamentalData
        # fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY)
        # news_data, _ = fd.get_news_sentiment(tickers=topic)
        # For now, returning mock data.
        mock_news = {
            "articles": [
                {
                    "title": f"Positive Outlook for {topic}",
                    "summary": f"Analysts are bullish on {topic} following recent product announcements.",
                    "overall_sentiment": "Positive"
                },
                {
                    "title": f"Market Volatility Impacts {topic}",
                    "summary": f"Broader market trends are causing short-term volatility for {topic} stock.",
                    "overall_sentiment": "Neutral"
                }
            ]
        }
        return json.dumps(mock_news)
    except Exception as e:
        print(f"Error fetching market news: {e}")
        return json.dumps({"error": "An error occurred while fetching market news."})


def get_citi_perspective(question: str) -> str:
    """
    Queries the Citi internal knowledge base via Vertex AI Search to get the official Citi perspective.

    Args:
        question: The user's question about Citi's opinion or recommendations.

    Returns:
        A JSON string containing a summary of the official Citi perspective.
    """
    # This is a simplified example of a Vertex AI Search call.
    # The actual implementation may require more complex request construction.
    serving_config = vertex_ai_search_client.serving_config_path(
        project=PROJECT_ID,
        location="global", # Search datastores are global
        data_store=VERTEX_AI_SEARCH_DATASTORE_ID,
        serving_config="default_config",
    )

    request = aiplatform.SearchRequest(
        serving_config=serving_config,
        query=question,
        page_size=1, # Get the most relevant document
    )

    try:
        search_response = vertex_ai_search_client.search(request)
        if not search_response.results:
            return json.dumps({"summary": "I could not find an official Citi perspective on this topic."})

        # Extract the summary from the most relevant result
        top_result = search_response.results[0].document
        summary = top_result.derived_struct_data.get('summary', 'No summary available.')

        return json.dumps({"summary": summary})
    except Exception as e:
        print(f"Error querying Vertex AI Search: {e}")
        return json.dumps({"error": "An error occurred while retrieving the Citi perspective."})
