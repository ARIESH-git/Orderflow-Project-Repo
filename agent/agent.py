import os
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

app = FastAPI()

LOKI_URL = os.getenv("LOKI_URL", "http://loki.monitoring.svc.cluster.local:3100")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

PAST_INCIDENTS = [
    "Consumer crash-loop caused by missing item field in Kafka message. Fix: add dead-letter-queue handling.",
    "API 500 errors caused by DynamoDB throttling during load spike. Fix: add exponential backoff retry.",
    "Kafka consumer lag spike caused by consumer group rebalancing after pod restart. Fix: increase session.timeout.ms.",
    "Redis connection refused errors caused by Redis pod OOMKilled. Fix: increase Redis memory limit in Helm values.",
]

@tool
def query_loki_errors(namespace: str = "default") -> str:
    """Query Loki for recent error logs from the given namespace."""
    end = datetime.utcnow()
    start = end - timedelta(minutes=15)
    params = {
        "query": '{namespace="' + namespace + '"} |= "error"',
        "start": str(int(start.timestamp() * 1e9)),
        "end": str(int(end.timestamp() * 1e9)),
        "limit": "20",
    }
    try:
        resp = requests.get(f"{LOKI_URL}/loki/api/v1/query_range", params=params, timeout=10)
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if not results:
            return "No error logs found in the last 15 minutes."
        lines = []
        for stream in results:
            for _, line in stream.get("values", []):
                lines.append(line)
        return "\n".join(lines[:20]) if lines else "No error lines found."
    except Exception as e:
        return f"Failed to query Loki: {str(e)}"

@tool
def lookup_past_incidents(error_description: str) -> str:
    """Search past incidents knowledge base for similar issues and fixes."""
    keywords = error_description.lower().split()
    matches = []
    for incident in PAST_INCIDENTS:
        if any(kw in incident.lower() for kw in keywords):
            matches.append(incident)
    if not matches:
        return "No similar past incidents found."
    return "Similar past incidents:\n" + "\n".join(f"- {m}" for m in matches[:2])

@tool
def post_to_slack(message: str) -> str:
    """Post a diagnosis and suggested fix to the Slack alerts channel."""
    if not SLACK_WEBHOOK:
        return "SLACK_WEBHOOK_URL not set - message not sent."
    try:
        payload = {"text": f":rotating_light: *OrderFlow AI Ops Copilot*\n{message}"}
        resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        if resp.status_code == 200:
            return "Message posted to Slack successfully."
        return f"Slack returned status {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Failed to post to Slack: {str(e)}"

llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY)
tools = [query_loki_errors, lookup_past_incidents, post_to_slack]

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI ops copilot for OrderFlow, a Kubernetes-based order processing platform.
When triggered by an alert:
1. Query Loki for recent error logs
2. Look up similar past incidents in the knowledge base
3. Post a clear diagnosis and suggested fix to Slack
Be concise and actionable. Always complete all 3 steps."""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

@app.post("/alert")
async def handle_alert(request: Request):
    body = await request.json()
    alerts = body.get("alerts", [{}])
    alert_name = alerts[0].get("labels", {}).get("alertname", "Unknown alert")
    summary = alerts[0].get("annotations", {}).get("summary", "No summary provided")
    trigger_message = f"Alert fired: {alert_name}. Summary: {summary}. Investigate and post findings to Slack."
    result = agent_executor.invoke({"input": trigger_message})
    return {"status": "processed", "output": result.get("output")}

@app.get("/health")
def health():
    return {"status": "ok"}
