# AIOps Core Engine

The heart of automated Kubernetes incident detection and investigation. This module contains the detection engine, investigation logic, and root cause analysis.

## What This Is

A Python module that:
1. **Detects** incidents in your Kubernetes cluster (crashes, memory issues, missing endpoints, etc.)
2. **Investigates** by collecting comprehensive evidence (logs, events, container state, resources)
3. **Analyzes** to determine root cause and recommend fixes

Think of it as a detective that never sleeps - continuously monitoring your cluster and creating detailed incident reports.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify kubeconfig works
kubectl cluster-info
```

### Run Detection

```bash
# Scan your cluster once
python incident_detector.py

# You'll see output like:
# [DETECT] Scanning cluster...
# [DETECT] Found 3 incidents
# [DETECT] Pod: payment-service-xyz (OOMKilled)
# [DETECT] Service: api-gateway (No ready endpoints)
# [DETECT] Node: worker-1 (Memory pressure)
```

### Use as a Module

```python
from incident_detector import IncidentDetector

detector = IncidentDetector()

# Scan the cluster
incidents = detector.scan()

for incident in incidents:
    print(f"Incident: {incident['pod']}")
    print(f"Severity: {incident['severity']}")
    print(f"Issue: {incident['description']}")
```

## Project Structure

```
├── incident_detector.py     # Main detection engine
├── incident_investigator.py # Evidence collection
├── mcp_server.py           # MCP protocol interface
├── test_kubernetes.py      # Integration tests
└── requirements.txt        # Dependencies
```

## How It Works

### 1. Incident Detector (`incident_detector.py`)

Continuously scans your Kubernetes cluster for problems:

```python
class IncidentDetector:
    def scan(self):
        # Checks:
        # - All pods (status, restart count, exit codes)
        # - All deployments (replica mismatch, failed updates)
        # - All services (endpoint availability)
        # - All nodes (readiness, resource pressure)
        # - Events (what happened recently?)
        
        return [
            {
                "pod": "myapp-xyz",
                "status": "Failed",
                "restart_count": 5,
                "exit_code": 137,  # OOMKilled
                "severity": "CRITICAL"
            },
            # ... more incidents
        ]
```

**What it detects:**

| Issue | Severity | What to Look For |
|-------|----------|------------------|
| **OOMKilled** | CRITICAL | Exit code 137, memory used > limit |
| **CrashLoopBackOff** | CRITICAL | Restart count > 3, exit code 1 |
| **ImagePullBackOff** | WARNING | Can't pull container image |
| **Pending Pod** | WARNING | Pod unschedulable for > 5 minutes |
| **No Endpoints** | CRITICAL | Service has no ready pods |
| **Node NotReady** | CRITICAL | Node status unhealthy |
| **Memory Pressure** | WARNING | Node memory < 5% free |
| **Disk Pressure** | WARNING | Node disk full |

### 2. Incident Investigator (`incident_investigator.py`)

When an incident is found, investigate it for root cause:

```python
class IncidentInvestigator:
    def investigate_pod(self, namespace, pod_name):
        # Collects:
        return {
            "metadata": {
                "name": pod_name,
                "labels": {},
                "annotations": {},
                "created_at": "2026-09-04T10:00:00Z"
            },
            "current_state": {
                "phase": "Failed",
                "container_status": {
                    "ready": False,
                    "restart_count": 5,
                    "state": "Terminated",
                    "exit_code": 137
                }
            },
            "resources": {
                "memory_limit": "256Mi",
                "memory_used": "512Mi",
                "cpu_limit": "500m",
                "cpu_used": "450m"
            },
            "logs": {
                "current": ["Starting...", "Loading data...", "OOM"],
                "previous": ["Crashed..."]
            },
            "events": [
                "Pod created",
                "Container started",
                "Memory pressure",
                "Killed by kernel"
            ]
        }
```

### 3. Root Cause Analysis

The data is structured so an AI model (or human) can reason about it:

```
Evidence collected:
- Exit code 137 = SIGKILL (memory kill)
- Memory used: 512Mi
- Memory limit: 256Mi (VIOLATED!)
- Logs: Application was loading data

Root cause:
  ↓
Application needs more memory than allocated

Recommendation:
  ↓
Increase memory limit from 256Mi to 512Mi
Edit: helm upgrade myapp --set resources.limits.memory=512Mi
```

## Real Examples

### Example 1: Pod OOMKilled

**Detection:**
```
Pod: payment-processor-abc123
Status: Failed
Restart count: 7
Exit code: 137
Severity: CRITICAL
```

**Investigation:**
```json
{
  "memory_limit": "256Mi",
  "memory_used": "512Mi",
  "logs": [
    "Starting payment processor...",
    "Loading transaction cache (300Mi)...",
    "(kernel killed process)"
  ]
}
```

**AI Analysis:**
"Pod is out of memory. Application tried to allocate 300Mi cache but only has 256Mi limit. Recommend: increase to 512Mi."

### Example 2: Service with No Endpoints

**Detection:**
```
Service: api-gateway
Endpoint count: 0
Severity: CRITICAL
```

**Investigation:**
```json
{
  "selector": {"app": "api-gateway"},
  "matching_pods": 3,
  "pod_status": [
    {"name": "api-gateway-1", "ready": false, "reason": "CrashLoopBackOff"},
    {"name": "api-gateway-2", "ready": false, "reason": "ImagePullBackOff"},
    {"name": "api-gateway-3", "ready": false, "reason": "Pending"}
  ]
}
```

**AI Analysis:**
"Service exists but pods aren't ready. Pod 1: crashing (check logs). Pod 2: can't pull image (check registry access). Pod 3: pending (waiting for resources)."

### Example 3: High Restart Count

**Detection:**
```
Pod: analytics-worker-xyz
Restart count: 12 (very high!)
Severity: WARNING
```

**Investigation:**
```json
{
  "current_state": "Running",
  "restart_count": 12,
  "exit_code": 1,  # Application error, not infrastructure
  "logs": [
    "Connected to database",
    "Processing batch 1...",
    "Error: timeout on query",
    "Restarting..."
  ]
}
```

**AI Analysis:**
"Pod keeps crashing due to application errors (exit code 1), not infrastructure. Database queries timing out. Check if database is slow or overloaded."

## Integration Points

### MCP Server

The `mcp_server.py` exposes these tools to AI models:

```python
@mcp.tool()
async def get_cluster_status():
    """Returns overall health: healthy pods, failed pods, nodes, etc."""

@mcp.tool()
async def get_cluster_incidents():
    """Lists all detected incidents"""

@mcp.tool()
async def investigation_cluster_incidents():
    """Returns full investigation for each incident"""
```

### Direct Module Usage

```python
from incident_detector import IncidentDetector

detector = IncidentDetector()
incidents = detector.scan()

# Process however you want
for incident in incidents:
    if incident['severity'] == 'CRITICAL':
        send_alert(incident)
        investigate(incident)
```

## Configuration

### Environment Variables

```bash
# Kubernetes
KUBECONFIG=~/.kube/config

# Which namespaces to monitor
NAMESPACES=default,production,monitoring

# Detection sensitivity
RESTART_COUNT_THRESHOLD=5
PENDING_TIMEOUT_SECONDS=300

# Logging
LOG_LEVEL=INFO  # or DEBUG for verbose output
```

### Cluster Access

The module requires read-only access to Kubernetes resources:

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
```

## API Reference

### IncidentDetector

```python
detector = IncidentDetector(namespace=None, kubeconfig='~/.kube/config')

# Scan for incidents
incidents = detector.scan()

# Returns:
[
    {
        "incident_id": "incident-123",
        "pod": "myapp-xyz",
        "namespace": "production",
        "severity": "CRITICAL",  # CRITICAL, WARNING, INFO
        "type": "OOMKilled",
        "description": "Pod killed due to memory limit exceeded",
        "detection_time": "2026-09-04T14:30:00Z"
    }
]
```

### IncidentInvestigator

```python
investigator = IncidentInvestigator()

# Investigate a pod
investigation = investigator.investigate_pod("production", "myapp-xyz")

# Returns:
{
    "pod": "myapp-xyz",
    "namespace": "production",
    "metadata": {...},
    "current_state": {...},
    "container_state": {...},
    "resources": {...},
    "logs": {
        "current": [...],
        "previous": [...]
    },
    "events": [...]
}
```

## Testing

### Manual Testing

```bash
# Test against your cluster
python test_kubernetes.py

# This will:
# 1. Try to connect to cluster
# 2. Scan for incidents
# 3. Investigate each incident
# 4. Print results
```

### Unit Testing (Future)

```bash
# Once implemented:
pytest test_*.py -v
```

## Performance

| Operation | Typical Time |
|-----------|--------------|
| Cluster scan (detection) | 2-3 seconds |
| Investigate single pod | 500ms |
| Full scan + investigation | 5-10 seconds |

**Optimization tips:**
- Only watch specific namespaces if cluster is large
- Adjust check frequency based on your needs
- Consider caching results if called frequently

## Common Issues

### "Connection refused" to Kubernetes API

```bash
# Check kubeconfig
kubectl cluster-info

# Set kubeconfig explicitly
export KUBECONFIG=~/.kube/config

# Try connecting
python -c "from incident_detector import IncidentDetector; IncidentDetector().scan()"
```

### "Permission denied" errors

```bash
# Verify RBAC is applied
kubectl get clusterrole aiops-reader
kubectl get clusterrolebinding aiops-reader

# Check your service account permissions
kubectl auth can-i get pods --as=system:serviceaccount:default:aiops-agent
```

### Detection is slow

```bash
# Check kubectl performance
time kubectl get pods -A

# If slow, check API server load
kubectl top nodes

# Consider reducing scope:
export NAMESPACES="production"  # Only watch production
```

## What Gets Detected vs What Doesn't

### ✅ Detected

- Pod crashes and restarts
- Memory/CPU limits exceeded
- Services with no ready endpoints
- Pending pods (unschedulable)
- Node resource pressure
- High restart counts
- Container exit codes

### ❌ Not Detected (Yet)

- Performance degradation (would need baselines)
- Incorrect configuration (needs validation)
- Network connectivity issues
- Persistent volume issues (beyond availability)
- Custom resource problems (CRDs)

## Contributing

Have an idea for a new incident type? Found a bug?

1. Check `test_kubernetes.py` for examples
2. Add detection logic to `incident_detector.py`
3. Add investigation to `incident_investigator.py`
4. Test against real cluster
5. Submit PR!

## Design Patterns Used

### Observer Pattern
- Continuously monitors cluster state
- Notifies via structured incident objects

### Strategy Pattern
- Different detection strategies for different resource types
- Pluggable investigation strategies

### Factory Pattern
- Creates appropriate incident objects based on detected issues

## References

- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Deployment Status](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#deployment-status)

## License

MIT

---

**What this module does best:** Turn raw Kubernetes state into actionable insights.

**Built by:** Dhruvil Satani  
**Email:** dhruvilsatani98@gmail.com  
**Last Updated:** 2026-09-04

**Every incident tells a story. This module reads the story and tells it to your AI.**
