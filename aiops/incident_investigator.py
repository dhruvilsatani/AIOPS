# def investigate_pod(core, pod):

#     pod_name = pod.metadata.name
#     namespace = pod.metadata.namespace

#     investigation = {
#         "pod": pod_name,
#         "namespace": namespace,
#         "containers": [],
#         "events": []
#     }

#     # Get container information
#     if pod.status.container_statuses:

#         for container in pod.status.container_statuses:

#             container_info = {
#                 "name": container.name,
#                 "restart_count": container.restart_count
#             }

#             # Check current container state
#             if container.state:

#                 if container.state.waiting:
#                     container_info["state"] = "Waiting"
#                     container_info["reason"] = container.state.waiting.reason

#                 elif container.state.running:
#                     container_info["state"] = "Running"

#                 elif container.state.terminated:
#                     container_info["state"] = "Terminated"
#                     container_info["reason"] = container.state.terminated.reason

#             # Get current container logs
#             try:
#                 logs = core.read_namespaced_pod_log(
#                     name=pod_name,
#                     namespace=namespace,
#                     container=container.name,
#                     tail_lines=50
#                 )

#                 container_info["logs"] = logs

#             except Exception as e:
#                 container_info["logs"] = f"Could not get logs: {e}"

#             # Get logs from previous container instance
#             try:
#                 previous_logs = core.read_namespaced_pod_log(
#                     name=pod_name,
#                     namespace=namespace,
#                     container=container.name,
#                     previous=True,
#                     tail_lines=50
#                 )

#                 container_info["previous_logs"] = previous_logs

#             except Exception as e:
#                 container_info["previous_logs"] = f"No previous logs: {e}"

#             # Add container information to investigation
#             investigation["containers"].append(container_info)

#     # Get Pod events
#     events = core.list_namespaced_event(namespace)

#     for event in events.items:

#         if event.involved_object.name == pod_name:

#             investigation["events"].append({
#                 "reason": event.reason,
#                 "message": event.message,
#                 "type": event.type
#             })

#     return investigation