FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aiops_agent/ ./aiops_agent/

# Expects a mounted kubeconfig or in-cluster ServiceAccount token
CMD ["python", "-m", "aiops_agent.mcp_server"]
