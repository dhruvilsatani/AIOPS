# AIOps MCP Agent

An [MCP](https://modelcontextprotocol.io) server that exposes live Kubernetes cluster health as callable tools for an LLM — so you can ask a chat model things like *"what's wrong with my cluster right now?"* and get an answer grounded in real pod, deployment, and service state, instead of a guess.

## What this actually is (and isn't)

This is **not** a trained failure-prediction model. It's a two-layer system:

1. **A rule-based incident-detection engine** (`aiops_agent/incident_detector.py`) that talks to the Kubernetes API directly and flags concrete, well-understood failure signatures: `CrashLoopBackOff`, `OOMKilled`, non-zero exit codes, high restart counts, and unhealthy deployments/services/nodes.
2. **An MCP server** (`aiops_agent/mcp_server.py`) that exposes that engine as two tools — `get_cluster_status` and `investigation_cluster_incidents` — over the Model Context Protocol.

Any MCP-compatible client can then connect to this server and let an LLM call those tools mid-conversation. In practice this project is used with an LLM client configured against **DeepSeek via OpenRouter**, so the "prediction" you get is really: *rule-based detection produces structured incident data → the LLM reads that data and reasons/explains/suggests next steps in plain language.* That distinction matters — it's what makes the tool's output trustworthy (it's reporting real cluster state, not hallucinating one).

Deployment of the agent itself is automated with **ArgoCD** (GitOps) — see [`k8s/`](./k8s).

## Tools exposed

| Tool | Description |
|---|---|
| `get_cluster_status` | Scans the cluster and returns all currently detected incidents (pods, deployments, services, nodes). |
| `investigation_cluster_incidents` | Runs the same scan, then investigates each detected incident for more detail (recent events, container state history, etc.). |

## Project layout

```
aiops_agent/
  incident_detector.py   # KubernetesIncidentEngine — the detection/investigation logic
  mcp_server.py           # MCP server wiring the engine up as tools
  test_kubernetes.py      # manual smoke-test script (not pytest) against a live/kubeconfig cluster
k8s/
  serviceaccount.yaml               # dedicated `aiops-agent` ServiceAccount
  aiops-role.yaml / aiops-rolebinding.yaml               # namespaced (default) read access
  aiops-monitoring-role.yaml / aiops-monitoring-rolebinding.yaml   # namespaced (monitoring) read access
  aiops-clusterrole.yaml / aiops-clusterrolebinding.yaml # cluster-wide read access (deployments/replicasets across namespaces)
```

## Permissions

The agent runs under a dedicated `aiops-agent` ServiceAccount with **read-only** access (`get`/`list`/`watch` only — no `create`/`update`/`delete`) to pods, pod logs, events, namespaces, deployments, replicasets, and services. It cannot modify anything in the cluster. Apply the manifests in [`k8s/`](./k8s) with:

```bash
kubectl apply -f k8s/
```

## Running locally

```bash
pip install -r requirements.txt

# uses your local ~/.kube/config
python -m aiops_agent.mcp_server
```

Point any MCP-compatible client (configured with your LLM of choice, e.g. DeepSeek via OpenRouter) at this server to start prompting it about your cluster.

## Status / known limitations

- `test_kubernetes.py` is a manual smoke-test script, not an automated test suite — a real pytest suite (with a fake/mocked Kubernetes client) is a natural next step.
- Requires a working `~/.kube/config` with access to the target cluster; no in-cluster ServiceAccount auto-detection yet.
- Originally developed alongside a separate FastAPI social-media backend project; extracted into its own repository since it shares no code or dependencies with that project.

## License

MIT (or your choice — update this section).
