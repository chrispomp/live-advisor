import os
import json
from alpha_vantage.timeseries import TimeSeries
from google.cloud import bigquery
from google.cloud import discoveryengine

# --- Configuration ---
# Assumes GOOGLE_CLOUD_PROJECT is set in the environment.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo") # Use 'demo' for testing, but expect a real key in prod
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "fsi-banking-agentspace.awm")
VERTEX_AI_SEARCH_DATASTORE_ID = os.getenv("VERTEX_AI_SEARCH_DATASTORE_ID", "citi_perspectives_datastore")

# Initialize clients
try:
    bq_client = bigquery.Client(project=PROJECT_ID)
    vertex_ai_search_client = discoveryengine.SearchServiceClient()
except Exception as e:
    print(f"Warning: Could not initialize Google Cloud clients: {e}")
    bq_client = None
    vertex_ai_search_client = None

def get_user_portfolio_summary(client_id: str) -> str:
    """
    Retrieves the user's portfolio summary from the BigQuery holdings table.

    Args:
        client_id: The authenticated user's client ID.

    Returns:
        A JSON string with the total market value and top 3 holdings,
        or a message indicating that the portfolio could not be retrieved.
    """
    if not bq_client:
        return json.dumps({"error": "The BigQuery client is not available. Please check your Google Cloud credentials."})

    query = f"""
        WITH ClientHoldings AS (
            SELECT
                ticker,
                security_name,
                market_value
            FROM
                `{PROJECT_ID}.{BIGQUERY_DATASET}.holdings`
            WHERE
                client_id = @client_id
        ),
        TotalValue AS (
            SELECT
                SUM(market_value) AS total_market_value
            FROM
                ClientHoldings
        )
        SELECT
            h.ticker,
            h.security_name,
            h.market_value,
            tv.total_market_value
        FROM
            ClientHoldings h,
            TotalValue tv
        ORDER BY
            h.market_value DESC
        LIMIT 3;
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("client_id", "STRING", client_id),
        ]
    )
    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = list(query_job.result())

        if not results:
            return json.dumps({"message": "I could not retrieve your portfolio data at this time."})

        total_market_value = results[0].total_market_value if results else 0

        response = {
            "total_market_value": total_market_value,
            "top_holdings": [
                {
                    "ticker": row.ticker,
                    "security_name": row.security_name,
                    "market_value": row.market_value,
                }
                for row in results
            ],
        }
        return json.dumps(response)
    except Exception as e:
        print(f"Error querying BigQuery: {e}")
        return json.dumps({"error": "An error occurred while retrieving portfolio data."})


from alpha_vantage.fundamentaldata import FundamentalData

def get_market_news_and_sentiment(topic: str) -> str:
    """
    Fetches the latest news articles and sentiment for a given topic or company ticker.

    Args:
        topic: The company ticker or topic to search for.

    Returns:
        A JSON string summarizing up to 5 news articles, including title, summary, and sentiment.
    """
    if not ALPHA_VANTAGE_API_KEY or ALPHA_VANTAGE_API_KEY == "demo":
        return json.dumps({
            "error": "Missing or invalid Alpha Vantage API key. Please set the ALPHA_VANTAGE_API_KEY environment variable."
        })

    try:
        fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format='json')
        news_data, _ = fd.get_news_sentiment(tickers=topic, limit=5) # Limit to 5 articles

        if not news_data or 'feed' not in news_data or not news_data['feed']:
             return json.dumps({"articles": [], "message": f"No news found for {topic}."})

        articles = []
        for item in news_data['feed']:
            # Find the most relevant ticker sentiment
            ticker_sentiment = next((s for s in item.get('ticker_sentiment', []) if s.get('ticker') == topic.upper()), None)

            articles.append({
                "title": item.get('title'),
                "summary": item.get('summary'),
                "url": item.get('url'),
                "overall_sentiment": ticker_sentiment.get('ticker_sentiment_label', 'N/A') if ticker_sentiment else 'N/A'
            })

        return json.dumps({"articles": articles})
    except Exception as e:
        print(f"Error fetching market news from Alpha Vantage: {e}")
        # This could be due to an invalid API key, network issues, or an invalid ticker.
        # Provide a more specific error message if possible.
        error_message = "An error occurred while fetching market news. The ticker symbol may be invalid or the API key may have expired."
        return json.dumps({"error": error_message})


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
