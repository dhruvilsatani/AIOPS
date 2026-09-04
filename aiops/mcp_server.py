from fastmcp import FastMCP
from kubernetes import client , config
from incident_detector import  (investigate_detected_incidents, run_incident_scan, create_incident_engine)

mcp = FastMCP("Aiops")

def get_kubernets_core():

    config.load_kube_config()
    return client.CoreV1Api()
      

@mcp.tool()
async def get_cluster_status() -> dict:
    """Scan the kubernetes cluster and return detected incidents"""
    core,_ = get_kubernets_core()
    return run_incident_scan(core)

@mcp.tool()
async def investigation_cluster_incidents() -> dict:
    """ Scan the kubernetes cluster and investigate detected incidents """
    core, _ = get_kubernets_core()
    scan_result = run_incident_scan(core)
    investigations = investigate_detected_incidents(
        core,scan_result
        )
    return {
        "scan" : scan_result,
        "investigation": investigations
    }





if __name__ == "__main__":
    mcp.run()


