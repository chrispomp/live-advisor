# Agent Development Guide

This document provides instructions and guidelines for developers and AI agents working on this multimodal audio agent project.

## Project Overview

This project is a bidirectional audio agent that uses Google's Gemini Flash 1.5 model and the Google Agent Development Kit (ADK). It features a web-based interface for real-time voice conversations with the AI.

The core components are:
- **`ui/server/server.py`**: The Python WebSocket server that handles the agent logic using the ADK.
- **`ui/client/index.html`**: The main web interface for the user.
- **`ui/client/audio-client.js`**: The client-side JavaScript that manages audio input/output and WebSocket communication.
- **`ui/server/tools.py`**: Defines the tools that the agent can use to interact with external services.

## Development Setup

### 1. Install Dependencies

Install the required Python packages using pip:
```bash
pip install -r ui/server/requirements.txt
```

### 2. Authenticate with Google Cloud

For local development, you need to authenticate with Google Cloud to use services like BigQuery and Vertex AI Search. Run the following command and follow the instructions:

```bash
gcloud auth application-default login

gcloud auth application-default set-quota-project fsi-banking-agentspace
```

### 3. Configure Environment Variables

The application requires the following environment variables to be set:

- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID.
- `ALPHA_VANTAGE_API_KEY`: Your API key for Alpha Vantage, used for the market news tool. You can obtain a free API key from the [Alpha Vantage website](https://www.alphavantage.co/support/#api-key).
- `BIGQUERY_DATASET`: The BigQuery dataset where the user portfolio data is stored (e.g., `fsi-banking-agentspace.awm`).
- `VERTEX_AI_SEARCH_DATASTORE_ID`: The ID of the Vertex AI Search datastore to use for the `get_citi_perspective` tool.
- `ADK_MODEL`: The name of the Gemini model to use (e.g., `gemini-2.0-flash-live-preview-04-09`).

You can set them in your shell like this:
```bash
export GOOGLE_CLOUD_PROJECT="fsi-banking-agentspace"
export ALPHA_VANTAGE_API_KEY="6QRF1QS1W28T036V"
export GOOGLE_CLOUD_LOCATION="us-central1"
export BIGQUERY_DATASET="fsi-banking-agentspace.awm"
export VERTEX_AI_SEARCH_DATASTORE_ID="your-datastore-id"
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export PORT=8080
```

**Note on Deployment:** When deploying to Cloud Run, the `ALPHA_VANTAGE_API_KEY` should be stored in [Google Secret Manager](https://cloud.google.com/secret-manager) as a secret named `ALPHA_VANTAGE_API_KEY`. The `cloudbuild.yaml` file is configured to mount this secret as an environment variable in the Cloud Run service.

## Running the Application Locally

1.  **Start the Python server:**
    ```bash
    python ui/server/server.py
    ```
    The server will start on `localhost:8080`.

2.  **Start a simple web server for the client:**
    ```bash
    python -m http.server 8000
    ```

3.  **Open the web interface:**
    Navigate to `http://localhost:8000/ui/client/index.html` in your web browser.

## Testing

There are currently no automated tests for this project. To test your changes, you should run the application locally and perform the following manual checks:

1.  Verify that the application loads correctly in the browser.
2.  Test the microphone input and audio output.
3.  Have a conversation with the agent and ensure it responds appropriately.
4.  Test the available tools by asking questions that would trigger them (e.g., "What's my portfolio summary?", "What's the latest news on Google?").
5.  Check the browser console and server logs for any errors.

## Working with Tools

The agent's tools are defined in `ui/server/tools.py`. Each tool is a Python function that takes one or more arguments and returns a JSON string.

To add a new tool:
1.  Create a new function in `ui/server/tools.py` that follows the existing pattern.
2.  Add the new function to the `tools` list in the `Agent` constructor in `ui/server/server.py`.
3.  Update the system prompt in `ui/server/system_prompt.txt` to inform the agent about the new tool and its capabilities.
