# AI-Powered Kubernetes Operations & Incident Investigation

Complete end-to-end system for automated Kubernetes incident detection, investigation, and AI-powered diagnosis. Three separate components that work together: detect what's wrong, investigate why, let AI analyze and fix.

## 🏗️ Project Overview

This project contains **three main components**:

```
┌──────────────────────────────────────────────────────────┐
│              AI-Powered Kubernetes Operations             │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │         Your Kubernetes Cluster                     │ │
│  │  (Deployments, Services, Pods, Nodes, Events)      │ │
│  └────────────────┬────────────────────────────────────┘ │
│                   │                                       │
│    ┌──────────────┼──────────────┬──────────────┐        │
│    │              │              │              │        │
│    ▼              ▼              ▼              ▼        │
│ ┌────────┐  ┌──────────┐  ┌────────────┐  ┌────────┐  │
│ │aiops   │  │aiops-mcp-│  │deepseek-   │  │AI Models
│ │        │  │agent     │  │harness     │  │(Claude,│  │
│ │Detect  │  │          │  │            │  │DeepSeek)  │
│ │Investig│  │MCP       │  │Chat with   │  └────────┘  │
│ │Analyze │  │Server    │  │AI about    │              │
│ └────────┘  └──────────┘  └────────────┘              │
│                                                           │
│   📊 Output: Structured Incident Data                   │
│   💬 Output: AI-Powered Diagnosis                       │
│   🔧 Output: Fix Recommendations                        │
└──────────────────────────────────────────────────────────┘
```

| Component | Purpose | Tech |
|-----------|---------|------|
| **aiops** | Detection & Investigation Engine | Python |
| **aiops-mcp-agent** | MCP Server (AI Interface) | Python + Kubernetes |
| **deepseek-harness** | DeepSeek DSH Chat | Node.js + npm |

## The Problem We're Solving

When a Kubernetes pod dies at 3 AM:
- Alert fires ✓
- You wake up ✗
- You SSH in and dig through logs ✗
- 30 minutes later you figure out it's OOMKilled ✗

**With this agent:**
- Alert fires ✓
- Agent automatically investigates ✓
- AI model reads the investigation ✓
- You get a report: "Pod used 512Mi, limit is 256Mi. Increase memory." ✓
- Back to sleep in 2 minutes ✓

## What This Does

```
Your Kubernetes Cluster
        ↓
   [Agent Watches]
        ↓
   [Pod Crashes]
        ↓
   [Agent Detects]
        ↓
   [Investigates Automatically]
   ├─ Collects logs
   ├─ Checks container state
   ├─ Reads events
   └─ Analyzes resources
        ↓
   [MCP Protocol]
   (Exposes to AI)
        ↓
   [AI Models]
   ├─ Claude
   ├─ DeepSeek DSH
   └─ Custom Agents
        ↓
   [Intelligent Analysis]
   "Root cause: OOMKilled"
```

## Quick Start

### Prerequisites
```bash
# You need:
# - Kubernetes cluster
# - kubectl configured
# - Docker (to build/run)
# - Python 3.10+
```

### Deploy to Kubernetes

```bash
# 1. Build Docker image
docker build -t aiops-agent:latest .

# 2. Push to your registry
docker tag aiops-agent:latest your-registry/aiops-agent:latest
docker push your-registry/aiops-agent:latest

# 3. Deploy to cluster
kubectl apply -f k8s/

# 4. Verify it's running
kubectl get pods -n default | grep aiops
kubectl logs -f deployment/aiops-agent -n default
```

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Setup kubeconfig
export KUBECONFIG=~/.kube/config

# Run the agent
python -m aiops_agent.mcp_server

# The MCP server will start listening for connections
```

## Project Structure

```
aiops_agent/
├── incident_detector.py    # "What's broken?"
├── mcp_server.py           # "Talk to AI models"
└── test_kubernetes.py      # Tests

k8s/
├── aiops-clusterrole.yaml      # Read-only permissions
├── aiops-clusterrolebinding.yaml
├── aiops-role.yaml
├── aiops-rolebinding.yaml
├── aiops-monitoring-role.yaml
├── aiops-monitoring-rolebinding.yaml
└── serviceaccount.yaml

Dockerfile                  # Container definition
requirements.txt            # Python dependencies
```

## How It Works

### Part 1: Detection

The agent continuously scans your cluster:

```python
# What it checks for:
- Pods in CrashLoopBackOff
- Pods with high restart count
- Pods with OOMKilled status
- Container exit codes (1, 137, etc.)
- Services with no ready endpoints
- Nodes that aren't ready
- Deployment replica mismatches
```

**Example detection:**
```
[DETECT] Pod: payment-service-xyz
[DETECT] Status: Failed
[DETECT] Restart count: 5 (anomaly!)
[DETECT] Last exit code: 137 (SIGKILL = memory issue)
[DETECT] Severity: WARNING
```

### Part 2: Investigation

When something's wrong, it automatically collects evidence:

```python
# Investigation collects:
- Pod logs (current + previous)
- Container state details
- Exit codes and termination reasons
- Resource usage (vs limits)
- Kubernetes events
- Pod configuration
- Service account permissions
```

**Investigation example:**
```json
{
  "pod": "payment-service-xyz",
  "status": "Failed",
  "memory_limit": "256Mi",
  "memory_used": "512Mi",
  "exit_code": 137,
  "logs": [
    "Starting application...",
    "Loading database...",
    "Allocating 300Mi buffer...",
    "(killed by kernel)"
  ],
  "event": "Container killed due to memory"
}
```

### Part 3: MCP Interface

Exposes findings to AI models via MCP protocol:

```python
# Tools available to AI models:

@mcp.tool()
async def get_cluster_status():
    """What's the overall cluster health?"""
    return {healthy_nodes, healthy_pods, failed_pods}

@mcp.tool()
async def get_cluster_incidents():
    """What incidents are happening?"""
    return [incident, incident, ...]

@mcp.tool()
async def investigation_cluster_incidents():
    """Give me full investigations with evidence"""
    return [{investigation_with_evidence}, ...]
```

## Integration Examples

### With Claude API

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-1",
    max_tokens=2048,
    tools=[
        {
            "type": "mcp",
            "server": {
                "type": "stdio",
                "command": "python",
                "args": ["-m", "aiops_agent.mcp_server"]
            }
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "What's wrong with my cluster?"
        }
    ]
)

print(response.content)
```

### With DeepSeek DSH

```bash
# Terminal 1: Start agent
python -m aiops_agent.mcp_server

# Terminal 2: Start DSH with MCP
npm exec dsh -- \
  --mcp-server localhost:9001 \
  --profile web
```

Then ask DSH: "Investigate my Kubernetes cluster"

## Real-World Example: Pod OOMKilled at 2 AM

**Timeline:**

```
2:34 AM - Alert: payment-service-xyz down

WITHOUT AGENT (the nightmare):
  2:34 - Phone buzzes
  2:35 - Groggy wake-up
  2:36 - SSH to cluster
  2:37 - kubectl get pods
  2:38 - kubectl logs (scroll...scroll...)
  2:40 - "OOMKilled"
  2:41 - kubectl top pod
  2:42 - See: 512Mi used vs 256Mi limit
  2:43 - Edit values, redeploy
  2:50 - Back to sleep
  Total: 16 minutes awake, frustrated

WITH AGENT (the dream):
  2:34 - Alert fires
  2:34 - Agent investigates automatically
  2:35 - Get report:
         "Pod OOMKilled. Used 512Mi, limit 256Mi.
          Fix: helm upgrade --set resources.limits.memory=512Mi"
  2:36 - Deploy fix
  2:37 - Back to sleep
  Total: 3 minutes awake, satisfied
```

## Permissions (What This Agent Can Do)

The agent has **read-only** access:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: aiops-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services", "events", "nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "daemonsets", "statefulsets"]
  verbs: ["get", "list"]
- apiGroups: ["discovery.k8s.io"]
  resources: ["endpointslices"]
  verbs: ["list"]
```

**It CANNOT:**
- Delete anything
- Modify anything
- Access secrets (without explicit permission)
- Write to cluster

This is intentional. Investigation should never make things worse.

## Configuration

### Environment Variables

```bash
# Kubernetes
KUBECONFIG=/path/to/kubeconfig
WATCH_INTERVAL=30  # seconds between scans

# Logging
LOG_LEVEL=INFO  # or DEBUG

# MCP Server
MCP_PORT=9001
MCP_HOST=localhost
```

## Troubleshooting

### "Cannot get kubeconfig"

```bash
# Make sure kubeconfig is accessible
kubectl cluster-info
ls $KUBECONFIG

# Set it explicitly
export KUBECONFIG=~/.kube/config
```

### "Permission denied" errors

```bash
# Check RBAC is applied
kubectl get clusterrole aiops-reader
kubectl get clusterrolebinding aiops-reader

# Verify service account has role
kubectl get rolebinding -A | grep aiops
```

### "MCP server won't start"

```bash
# Check port is available
lsof -i :9001

# Check dependencies
python -c "import mcp; print('MCP OK')"

# Run with verbose logging
LOG_LEVEL=DEBUG python -m aiops_agent.mcp_server
```

## Performance

| Operation | Time |
|-----------|------|
| Scan cluster (detection) | 2-3s |
| Investigate single pod | 500ms |
| Full incident report | 1-2s |

## What the AI Model Sees

When Claude or DeepSeek investigates via MCP, they get:

```json
{
  "incident_id": "incident-2026-09-04-001",
  "severity": "CRITICAL",
  "pod": "payment-service-xyz",
  "namespace": "production",
  "status": "Failed",
  "restart_count": 5,
  "exit_code": 137,
  "exit_reason": "OOMKilled",
  "memory_requested": "256Mi",
  "memory_limit": "256Mi",
  "memory_used": "512Mi",
  "logs": [
    "Starting payment processor...",
    "Loading transaction cache...",
    "Cache: 300Mi allocated...",
    "(killed by kernel)"
  ],
  "events": [
    "Container started",
    "Container exited with code 137",
    "Container being restarted"
  ],
  "recommendation": "Increase memory limit to 512Mi"
}
```

The AI then analyzes this and tells you exactly what to fix.

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest aiops_agent/test_kubernetes.py -v

# Run with coverage
pytest --cov=aiops_agent aiops_agent/
```

### Local Development

```bash
# Use minikube for local testing
minikube start

# Point to minikube
eval $(minikube docker-env)
docker build -t aiops-agent:local .

# Deploy locally
kubectl apply -f k8s/
```

## Design Decisions

### Why Read-Only Access?

Investigation should **never break things further**. By limiting to read-only:
- Safe to run continuously
- Can't accidentally delete resources
- Easier to get cluster approval

### Why MCP Protocol?

MCP lets AI models:
- Call investigation tools directly
- Build context from multiple queries
- Reason over complete evidence
- Provide actionable recommendations

### Why Not Just Webhooks?

Webhooks are reactive. This is proactive:
- Continuous monitoring (not just on events)
- Can detect patterns (e.g., "restarted 5 times")
- Investigates before human intervention
- Better for intermittent issues

## Known Limitations

1. **Log retention** - Only last 100 lines (Kubernetes default)
2. **Custom resources** - Only standard K8s resources supported
3. **Node-level issues** - Limited to what Kubernetes API exposes
4. **Historical analysis** - Doesn't remember incidents after restart

## Roadmap

- [ ] Predictive alerts (ML on patterns)
- [ ] Automatic remediation (run fix scripts)
- [ ] Slack/Teams integration
- [ ] Multi-cluster support
- [ ] Custom incident rules (YAML DSL)
- [ ] Web dashboard for incidents

## Contributing

Found a bug? Have ideas? PRs welcome!

Before submitting:
1. Test against real cluster
2. Document any new incident types
3. Update this README if adding features

## Security

**What's NOT included in investigation:**
- Secrets or sensitive environment variables
- Private container registry credentials
- Internal network details

**What IS included:**
- Pod metadata and configuration
- Logs (application output only)
- Container state and exit codes
- Kubernetes events

This is by design - the agent never needs access to secrets.

## License

MIT

---

**Built because:** Debugging at 3 AM should not be a manual process  
**Built by:** Dhruvil Satani  
**Email:** dhruvilsatani98@gmail.com  
**Last Updated:** 2026-09-04

**The real magic happens when AI investigates your cluster automatically.**
