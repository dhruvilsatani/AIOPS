# incident_engine.py

from kubernetes import client
from datetime import datetime, timezone


# ============================================================
# Helpers
# ============================================================

def safe_getattr(obj, attr, default=None):
    """Safely get an attribute from a Kubernetes API object."""
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


def iso_time(value):
    """Convert Kubernetes datetime to ISO string."""
    if value is None:
        return None

    try:
        return value.isoformat()
    except Exception:
        return str(value)


def owner_references(obj):
    """Return simplified Kubernetes owner references."""
    refs = safe_getattr(obj.metadata, "owner_references", []) or []

    return [
        {
            "kind": safe_getattr(ref, "kind"),
            "name": safe_getattr(ref, "name"),
            "uid": safe_getattr(ref, "uid"),
            "controller": safe_getattr(ref, "controller"),
        }
        for ref in refs
    ]



def labels(obj):
    return safe_getattr(obj.metadata, "labels", {}) or {}


def annotations(obj):
    return safe_getattr(obj.metadata, "annotations", {}) or {}


def container_resources(container):
    resources = safe_getattr(container, "resources")

    if not resources:
        return {
            "requests": {},
            "limits": {},
        }

    return {
        "requests": safe_getattr(
            resources,
            "requests",
            {}
        ) or {},
        "limits": safe_getattr(
            resources,
            "limits",
            {}
        ) or {},
    }


def probe_info(probe):
    if not probe:
        return None

    result = {
        "initial_delay_seconds": safe_getattr(
            probe,
            "initial_delay_seconds"
        ),
        "timeout_seconds": safe_getattr(
            probe,
            "timeout_seconds"
        ),
        "period_seconds": safe_getattr(
            probe,
            "period_seconds"
        ),
        "failure_threshold": safe_getattr(
            probe,
            "failure_threshold"
        ),
        "success_threshold": safe_getattr(
            probe,
            "success_threshold"
        ),
    }

    http_get = safe_getattr(probe, "http_get")
    tcp_socket = safe_getattr(probe, "tcp_socket")
    exec_action = safe_getattr(probe, "_exec")

    if http_get:
        result["http_get"] = {
            "path": safe_getattr(http_get, "path"),
            "port": safe_getattr(http_get, "port"),
            "host": safe_getattr(http_get, "host"),
            "scheme": safe_getattr(http_get, "scheme"),
        }

    if tcp_socket:
        result["tcp_socket"] = {
            "port": safe_getattr(tcp_socket, "port"),
            "host": safe_getattr(tcp_socket, "host"),
        }

    if exec_action:
        result["exec"] = {
            "command": safe_getattr(
                exec_action,
                "command",
                []
            ),
        }

    return result


# ============================================================
# INCIDENT ENGINE
# ============================================================

class KubernetesIncidentEngine:

    def __init__(
        self,
        core: client.CoreV1Api,
        apps: client.AppsV1Api,
    ):
        self.core = core
        self.apps = apps

        # Discovery API for EndpointSlices
        self.discovery = client.DiscoveryV1Api(
            api_client=core.api_client
        )

    # ========================================================
    # Public API
    # ========================================================

    def scan_cluster(self):
        """
        Scan the cluster and return all detected incidents.

        Returns:
            {
                "timestamp": ...,
                "incident_count": ...,
                "incidents": [...]
            }
        """

        incidents = []

        # ----------------------------------------------------
        # Pods
        # ----------------------------------------------------

        try:
            pods = self.core.list_pod_for_all_namespaces()

            for pod in pods.items:
                incidents.extend(
                    self.detect_pod_incidents(pod)
                )

        except Exception as e:
            incidents.append(
                self.engine_error(
                    "POD_SCAN_FAILED",
                    str(e),
                )
            )

        # ----------------------------------------------------
        # Services
        # ----------------------------------------------------

        try:
            services = (
                self.core.list_service_for_all_namespaces()
            )

            for service in services.items:
                incidents.extend(
                    self.detect_service_incidents(service)
                )

        except Exception as e:
            incidents.append(
                self.engine_error(
                    "SERVICE_SCAN_FAILED",
                    str(e),
                )
            )

        # ----------------------------------------------------
        # Deployments
        # ----------------------------------------------------

        try:
            deployments = (
                self.apps.list_deployment_for_all_namespaces()
            )

            for deployment in deployments.items:
                incidents.extend(
                    self.detect_deployment_incidents(
                        deployment
                    )
                )

        except Exception as e:
            incidents.append(
                self.engine_error(
                    "DEPLOYMENT_SCAN_FAILED",
                    str(e),
                )
            )

        # ----------------------------------------------------
        # Nodes
        # ----------------------------------------------------

        try:
            nodes = self.core.list_node()

            for node in nodes.items:
                incidents.extend(
                    self.detect_node_incidents(node)
                )

        except Exception as e:
            incidents.append(
                self.engine_error(
                    "NODE_SCAN_FAILED",
                    str(e),
                )
            )

        return {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "incident_count": len(incidents),
            "incidents": incidents,
        }

    # ========================================================
    # POD DETECTION
    # ========================================================

    def detect_pod_incidents(self, pod):

        incidents = []

        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace

        statuses = (
            pod.status.container_statuses or []
        )

        for container in statuses:

            name = container.name
            restart_count = (
                container.restart_count or 0
            )

            # ------------------------------------------------
            # CrashLoopBackOff
            # ------------------------------------------------

            waiting = safe_getattr(
                container.state,
                "waiting"
            )

            if waiting:

                reason = waiting.reason

                if reason == "CrashLoopBackOff":

                    incident = {
                        "type": "CRASH_LOOP",
                        "severity": "CRITICAL",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "restart_count": restart_count,
                    }

                    last = safe_getattr(
                        container.last_state,
                        "terminated",
                    )

                    if last:
                        incident.update({
                            "exit_code": last.exit_code,
                            "last_reason": last.reason,
                            "started_at": iso_time(
                                last.started_at
                            ),
                            "finished_at": iso_time(
                                last.finished_at
                            ),
                        })

                    incidents.append(incident)

                    # Don't also report high restart count
                    continue

                # ------------------------------------------------
                # Image pull failures
                # ------------------------------------------------

                if reason in (
                    "ImagePullBackOff",
                    "ErrImagePull",
                ):

                    incidents.append({
                        "type": "IMAGE_PULL_FAILURE",
                        "severity": "CRITICAL",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "restart_count": restart_count,
                        "message": waiting.message,
                    })

                    continue

                # ------------------------------------------------
                # Container creation failures
                # ------------------------------------------------

                if reason in (
                    "CreateContainerConfigError",
                    "CreateContainerError",
                    "InvalidImageName",
                    "ContainerCannotRun",
                ):

                    incidents.append({
                        "type": "CONTAINER_START_FAILURE",
                        "severity": "CRITICAL",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "restart_count": restart_count,
                        "message": waiting.message,
                    })

                    continue

            # ------------------------------------------------
            # Currently terminated
            # ------------------------------------------------

            terminated = safe_getattr(
                container.state,
                "terminated",
            )

            if terminated:

                reason = terminated.reason
                exit_code = terminated.exit_code

                if reason == "OOMKilled":

                    incidents.append({
                        "type": "OOM_KILLED",
                        "severity": "CRITICAL",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "exit_code": exit_code,
                        "restart_count": restart_count,
                    })

                    continue

                if exit_code and exit_code != 0:

                    incidents.append({
                        "type": "CONTAINER_FAILED",
                        "severity": "CRITICAL",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "exit_code": exit_code,
                        "restart_count": restart_count,
                    })

                    continue

            # ------------------------------------------------
            # Previous termination
            # ------------------------------------------------

            last = safe_getattr(
                container.last_state,
                "terminated",
            )

            if last:

                reason = last.reason
                exit_code = last.exit_code

                # Normal graceful shutdown
                if (
                    exit_code == 143
                    or reason == "Completed"
                ):
                    pass

                elif reason == "OOMKilled":

                    incidents.append({
                        "type": "OOM_KILLED",
                        "severity": "CRITICAL",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "exit_code": exit_code,
                        "restart_count": restart_count,
                    })

                    continue

                elif exit_code and exit_code != 0:

                    incidents.append({
                        "type": "PREVIOUS_CONTAINER_FAILED",
                        "severity": "WARNING",
                        "resource_type": "Pod",
                        "pod": pod_name,
                        "namespace": namespace,
                        "container": name,
                        "reason": reason,
                        "exit_code": exit_code,
                        "restart_count": restart_count,
                    })

                    continue

            # ------------------------------------------------
            # High restart count
            # ------------------------------------------------

                
            is_ready = bool(container.ready)

            is_running = bool(
                    container.state
                    and container.state.running
                )

            last = safe_getattr(
                    container.last_state,
                    "terminated",
                )

            last_exit_code = (
                    safe_getattr(last, "exit_code")
                    if last
                    else None
                )


            last_reason = (
                    safe_getattr(last, "reason")
                    if last
                    else None
                )

            graceful_last_exit = (
                    last_exit_code in (0, 143)
                    or last_reason == "Completed"
                )

            if restart_count > 5:

                    # If the container is currently healthy and
                    # the previous termination was graceful,
                    # don't report an active restart incident.
                    if is_running and is_ready and graceful_last_exit:
                        pass

                    else:
                        incidents.append({
                            "type": "HIGH_RESTART_COUNT",
                            "severity": (
                                "CRITICAL"
                                if not is_ready
                                else "WARNING"
                            ),
                            "resource_type": "Pod",
                            "pod": pod_name,
                            "namespace": namespace,
                            "container": name,
                            "restart_count": restart_count,
                            "ready": is_ready,
                            "last_exit_code": last_exit_code,
                            "last_reason": last_reason,
                        })

        # ====================================================
        # Pod-level status
        # ====================================================

        phase = pod.status.phase

        if phase == "Pending":

            incidents.append({
                "type": "POD_PENDING",
                "severity": "WARNING",
                "resource_type": "Pod",
                "pod": pod_name,
                "namespace": namespace,
                "phase": phase,
            })

        elif phase == "Failed":

            incidents.append({
                "type": "POD_FAILED",
                "severity": "CRITICAL",
                "resource_type": "Pod",
                "pod": pod_name,
                "namespace": namespace,
                "phase": phase,
            })

        return incidents

    # ========================================================
    # SERVICE DETECTION
    # ========================================================

    def detect_service_incidents(self, service):

        incidents = []

        name = service.metadata.name
        namespace = service.metadata.namespace

        try:

            # Use Kubernetes DiscoveryV1Api instead of
            # manually calling the REST API.
            endpoint_slices = (
                self.discovery.list_namespaced_endpoint_slice(
                    namespace=namespace
                )
            )

            matching_endpoints = []

            selector = service.spec.selector or {}

            for endpoint_slice in endpoint_slices.items:

                slice_labels = (
                    endpoint_slice.metadata.labels or {}
                )

                if (
                    slice_labels.get(
                        "kubernetes.io/service-name"
                    )
                    != name
                ):
                    continue

                for endpoint in endpoint_slice.endpoints:

                    conditions = endpoint.conditions

                    if (
                        conditions
                        and conditions.ready is True
                    ):
                        matching_endpoints.append(
                            endpoint
                        )

            # ------------------------------------------------
            # Service has no ready endpoints
            # ------------------------------------------------

            if selector and not matching_endpoints:

                incidents.append({
                    "type": "SERVICE_NO_ENDPOINTS",
                    "severity": "CRITICAL",
                    "resource_type": "Service",
                    "service": name,
                    "namespace": namespace,
                    "selector": selector,
                    "ready_endpoints": 0,
                })

        except Exception as e:

            incidents.append({
                "type": "SERVICE_ENDPOINT_CHECK_FAILED",
                "severity": "WARNING",
                "resource_type": "Service",
                "service": name,
                "namespace": namespace,
                "error": str(e),
            })

        return incidents

    # ========================================================
    # DEPLOYMENT DETECTION
    # ========================================================

    def detect_deployment_incidents(
        self,
        deployment
    ):

        incidents = []

        name = deployment.metadata.name
        namespace = deployment.metadata.namespace

        spec = deployment.spec
        status = deployment.status

        desired = spec.replicas or 0
        available = status.available_replicas or 0
        ready = status.ready_replicas or 0
        updated = status.updated_replicas or 0
        unavailable = status.unavailable_replicas or 0

        # ----------------------------------------------------
        # Replica shortage
        # ----------------------------------------------------

        if available < desired:

            incidents.append({
                "type": "DEPLOYMENT_UNAVAILABLE_REPLICAS",
                "severity": "CRITICAL",
                "resource_type": "Deployment",
                "deployment": name,
                "namespace": namespace,
                "desired_replicas": desired,
                "available_replicas": available,
                "ready_replicas": ready,
                "updated_replicas": updated,
                "unavailable_replicas": unavailable,
            })

        # ----------------------------------------------------
        # Rollout hasn't completed
        # ----------------------------------------------------

        if updated < desired:

            incidents.append({
                "type": "DEPLOYMENT_ROLLOUT_INCOMPLETE",
                "severity": "WARNING",
                "resource_type": "Deployment",
                "deployment": name,
                "namespace": namespace,
                "desired_replicas": desired,
                "updated_replicas": updated,
                "available_replicas": available,
            })

        # ----------------------------------------------------
        # Deployment conditions
        # ----------------------------------------------------

        conditions = status.conditions or []

        for condition in conditions:

            condition_type = condition.type
            condition_status = condition.status

            if (
                condition_type == "Progressing"
                and condition_status == "False"
            ):

                incidents.append({
                    "type": "DEPLOYMENT_PROGRESS_DEADLINE",
                    "severity": "CRITICAL",
                    "resource_type": "Deployment",
                    "deployment": name,
                    "namespace": namespace,
                    "reason": condition.reason,
                    "message": condition.message,
                })

            if (
                condition_type == "Available"
                and condition_status == "False"
            ):
                #incidents = {}
                # incidents.append({
                #     "type" : "Deployment_progress_deadline",
                #     "severity": "criticle"

                # })
                incidents.append({
                    "type": "DEPLOYMENT_NOT_AVAILABLE",
                    "severity": "CRITICAL",
                    "resource_type": "Deployment",
                    "deployment": name,
                    "namespace": namespace,
                    "reason": condition.reason,
                    "message": condition.message,
                })

        return incidents

    # ========================================================
    # NODE DETECTION
    # ========================================================

    def detect_node_incidents(self, node):

        incidents = []

        name = node.metadata.name

        conditions = node.status.conditions or []

        for condition in conditions:

            condition_type = condition.type
            status = condition.status

            # ------------------------------------------------
            # Node NotReady
            # ------------------------------------------------

            if (
                condition_type == "Ready"
                and status != "True"
            ):

                incidents.append({
                    "type": "NODE_NOT_READY",
                    "severity": "CRITICAL",
                    "resource_type": "Node",
                    "node": name,
                    "reason": condition.reason,
                    "message": condition.message,
                    "status": status,
                })

            # ------------------------------------------------
            # Memory pressure
            # ------------------------------------------------

            if (
                condition_type == "MemoryPressure"
                and status == "True"
            ):

                incidents.append({
                    "type": "NODE_MEMORY_PRESSURE",
                    "severity": "CRITICAL",
                    "resource_type": "Node",
                    "node": name,
                    "reason": condition.reason,
                    "message": condition.message,
                })

            # ------------------------------------------------
            # Disk pressure
            # ------------------------------------------------

            if (
                condition_type == "DiskPressure"
                and status == "True"
            ):

                incidents.append({
                    "type": "NODE_DISK_PRESSURE",
                    "severity": "CRITICAL",
                    "resource_type": "Node",
                    "node": name,
                    "reason": condition.reason,
                    "message": condition.message,
                })

            # ------------------------------------------------
            # PID pressure
            # ------------------------------------------------

            if (
                condition_type == "PIDPressure"
                and status == "True"
            ):

                incidents.append({
                    "type": "NODE_PID_PRESSURE",
                    "severity": "WARNING",
                    "resource_type": "Node",
                    "node": name,
                    "reason": condition.reason,
                    "message": condition.message,
                })

        return incidents

    # ========================================================
    # INVESTIGATION
    # ========================================================

    def investigate_incident(self, incident):

        resource_type = incident.get(
            "resource_type"
        )

        if resource_type == "Pod":

            return self.investigate_pod(
                incident["namespace"],
                incident["pod"],
            )

        if resource_type == "Service":

            return self.investigate_service(
                incident["namespace"],
                incident["service"],
            )

        if resource_type == "Deployment":

            return self.investigate_deployment(
                incident["namespace"],
                incident["deployment"],
            )

        if resource_type == "Node":

            return self.investigate_node(
                incident["node"],
            )

        return {
            "error": "Unknown resource type",
            "incident": incident,
        }

    # ========================================================
    # POD INVESTIGATION
    # ========================================================

    def investigate_pod(
        self,
        namespace,
        pod_name
    ):

        investigation = {
            "resource_type": "Pod",
            "pod": pod_name,
            "namespace": namespace,
            "metadata": {},
            "status": {},
            "containers": [],
            "events": [],
        }

        try:

            pod = self.core.read_namespaced_pod(
                name=pod_name,
                namespace=namespace,
            )

        except Exception as e:

            investigation["error"] = str(e)
            return investigation

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

        investigation["metadata"] = {
            "labels": labels(pod),
            "annotations": annotations(pod),
            "owner_references": owner_references(pod),
            "node": pod.spec.node_name,
            "service_account": (
                pod.spec.service_account_name
            ),
        }

        # ----------------------------------------------------
        # Pod status
        # ----------------------------------------------------

        investigation["status"] = {
            "phase": pod.status.phase,
            "reason": pod.status.reason,
            "message": pod.status.message,
            "pod_ip": pod.status.pod_ip,
            "host_ip": pod.status.host_ip,
            "start_time": iso_time(
                pod.status.start_time
            ),
        }

        # ----------------------------------------------------
        # Containers
        # ----------------------------------------------------

        statuses = (
            pod.status.container_statuses or []
        )

        specs = {
            c.name: c
            for c in pod.spec.containers
        }

        for status in statuses:

            spec = specs.get(status.name)

            container_info = {
                "name": status.name,
                "image": (
                    safe_getattr(
                        spec,
                        "image"
                    )
                    if spec
                    else None
                ),
                "restart_count": status.restart_count,
                "ready": status.ready,
                "started": status.started,
                "state": {},
                "last_state": {},
                "resources": (
                    container_resources(spec)
                    if spec
                    else {}
                ),
                "probes": {
                    "liveness": (
                        probe_info(
                            safe_getattr(
                                spec,
                                "liveness_probe"
                            )
                        )
                        if spec
                        else None
                    ),
                    "readiness": (
                        probe_info(
                            safe_getattr(
                                spec,
                                "readiness_probe"
                            )
                        )
                        if spec
                        else None
                    ),
                    "startup": (
                        probe_info(
                            safe_getattr(
                                spec,
                                "startup_probe"
                            )
                        )
                        if spec
                        else None
                    ),
                },
            }

            # ------------------------------------------------
            # Current state
            # ------------------------------------------------

            if status.state:

                if status.state.waiting:

                    container_info["state"] = {
                        "type": "Waiting",
                        "reason": (
                            status.state.waiting.reason
                        ),
                        "message": (
                            status.state.waiting.message
                        ),
                    }

                elif status.state.running:

                    container_info["state"] = {
                        "type": "Running",
                        "started_at": iso_time(
                            status.state.running.started_at
                        ),
                    }

                elif status.state.terminated:

                    container_info["state"] = {
                        "type": "Terminated",
                        "reason": (
                            status.state.terminated.reason
                        ),
                        "exit_code": (
                            status.state.terminated.exit_code
                        ),
                        "signal": (
                            status.state.terminated.signal
                        ),
                        "message": (
                            status.state.terminated.message
                        ),
                        "started_at": iso_time(
                            status.state.terminated.started_at
                        ),
                        "finished_at": iso_time(
                            status.state.terminated.finished_at
                        ),
                    }

            # ------------------------------------------------
            # Previous state
            # ------------------------------------------------

            if status.last_state:

                if status.last_state.terminated:

                    last = (
                        status.last_state.terminated
                    )

                    container_info["last_state"] = {
                        "type": "Terminated",
                        "reason": last.reason,
                        "exit_code": last.exit_code,
                        "signal": last.signal,
                        "message": last.message,
                        "started_at": iso_time(
                            last.started_at
                        ),
                        "finished_at": iso_time(
                            last.finished_at
                        ),
                    }

            # ------------------------------------------------
            # Logs
            # ------------------------------------------------

            try:

                container_info["logs"] = (
                    self.core.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=namespace,
                        container=status.name,
                        tail_lines=100,
                    )
                )

            except Exception as e:

                container_info["logs"] = (
                    f"Could not retrieve logs: {e}"
                )

            # ------------------------------------------------
            # Previous logs
            # ------------------------------------------------

            try:

                container_info["previous_logs"] = (
                    self.core.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=namespace,
                        container=status.name,
                        previous=True,
                        tail_lines=100,
                    )
                )

            except Exception as e:

                container_info["previous_logs"] = (
                    f"No previous logs: {e}"
                )

            investigation["containers"].append(
                container_info
            )

        # ----------------------------------------------------
        # Events
        # ----------------------------------------------------

        investigation["events"] = (
            self.get_pod_events(
                namespace,
                pod_name,
            )
        )

        return investigation

    # ========================================================
    # SERVICE INVESTIGATION
    # ========================================================

    def investigate_service(
        self,
        namespace,
        service_name
    ):

        investigation = {
            "resource_type": "Service",
            "service": service_name,
            "namespace": namespace,
            "service_info": {},
            "endpoint_slices": [],
            "matching_pods": [],
            "events": [],
        }

        try:

            service = (
                self.core.read_namespaced_service(
                    service_name,
                    namespace,
                )
            )

        except Exception as e:

            investigation["error"] = str(e)
            return investigation

        selector = service.spec.selector or {}

        investigation["service_info"] = {
            "type": service.spec.type,
            "cluster_ip": service.spec.cluster_ip,
            "ports": [
                {
                    "name": p.name,
                    "port": p.port,
                    "target_port": p.target_port,
                    "protocol": p.protocol,
                }
                for p in service.spec.ports
            ],
            "selector": selector,
        }

        # ----------------------------------------------------
        # Matching pods
        # ----------------------------------------------------

        try:

            pods = self.core.list_namespaced_pod(
                namespace
            )

            for pod in pods.items:

                pod_labels = labels(pod)

                matches = all(
                    pod_labels.get(k) == v
                    for k, v in selector.items()
                )

                if matches:

                    investigation[
                        "matching_pods"
                    ].append({
                        "name": pod.metadata.name,
                        "phase": pod.status.phase,
                        "pod_ip": pod.status.pod_ip,
                        "node": pod.spec.node_name,
                        "ready": self.pod_ready(pod),
                    })

        except Exception as e:

            investigation[
                "matching_pods_error"
            ] = str(e)

        # ----------------------------------------------------
        # EndpointSlices
        # ----------------------------------------------------

        try:

            endpoint_slices = (
                self.discovery.list_namespaced_endpoint_slice(
                    namespace=namespace
                )
            )

            for endpoint_slice in endpoint_slices.items:

                item_labels = (
                    endpoint_slice.metadata.labels or {}
                )

                if (
                    item_labels.get(
                        "kubernetes.io/service-name"
                    )
                    == service_name
                ):

                    investigation[
                        "endpoint_slices"
                    ].append(
                        endpoint_slice.to_dict()
                    )

        except Exception as e:

            investigation[
                "endpoint_slices_error"
            ] = str(e)

        # ----------------------------------------------------
        # Events
        # ----------------------------------------------------

        investigation["events"] = (
            self.get_service_events(
                namespace,
                service_name,
            )
        )

        return investigation

    # ========================================================
    # DEPLOYMENT INVESTIGATION
    # ========================================================

    def investigate_deployment(
        self,
        namespace,
        deployment_name,
    ):

        investigation = {
            "resource_type": "Deployment",
            "deployment": deployment_name,
            "namespace": namespace,
            "deployment_info": {},
            "pods": [],
            "events": [],
        }

        try:

            deployment = (
                self.apps.read_namespaced_deployment(
                    deployment_name,
                    namespace,
                )
            )

        except Exception as e:

            investigation["error"] = str(e)
            return investigation

        selector = (
            deployment.spec.selector.match_labels
            or {}
        )

        investigation["deployment_info"] = {
            "replicas": deployment.spec.replicas,
            "available": (
                deployment.status.available_replicas
                or 0
            ),
            "ready": (
                deployment.status.ready_replicas
                or 0
            ),
            "updated": (
                deployment.status.updated_replicas
                or 0
            ),
            "unavailable": (
                deployment.status.unavailable_replicas
                or 0
            ),
            "selector": selector,
            "strategy": deployment.spec.strategy.type,
            "conditions": [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason,
                    "message": c.message,
                    "last_update_time": iso_time(
                        c.last_update_time
                    ),
                }
                for c in (
                    deployment.status.conditions
                    or []
                )
            ],
        }

        # ----------------------------------------------------
        # Find deployment pods
        # ----------------------------------------------------

        try:

            pods = self.core.list_namespaced_pod(
                namespace
            )

            for pod in pods.items:

                pod_labels = labels(pod)

                matches = all(
                    pod_labels.get(k) == v
                    for k, v in selector.items()
                )

                if matches:

                    investigation["pods"].append({
                        "name": pod.metadata.name,
                        "phase": pod.status.phase,
                        "pod_ip": pod.status.pod_ip,
                        "node": pod.spec.node_name,
                        "ready": self.pod_ready(pod),
                        "containers": [
                            {
                                "name": c.name,
                                "restart_count": (
                                    c.restart_count
                                ),
                                "ready": c.ready,
                            }
                            for c in (
                                pod.status.container_statuses
                                or []
                            )
                        ],
                    })

        except Exception as e:

            investigation["pods_error"] = str(e)

        investigation["events"] = (
            self.get_deployment_events(
                namespace,
                deployment_name,
            )
        )

        return investigation

    # ========================================================
    # NODE INVESTIGATION
    # ========================================================

    def investigate_node(self, node_name):

        investigation = {
            "resource_type": "Node",
            "node": node_name,
            "node_info": {},
            "pods": [],
            "events": [],
        }

        try:

            node = self.core.read_node(
                node_name
            )

        except Exception as e:

            investigation["error"] = str(e)
            return investigation

        investigation["node_info"] = {
            "labels": labels(node),
            "annotations": annotations(node),
            "conditions": [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason,
                    "message": c.message,
                    "last_heartbeat": iso_time(
                        c.last_heartbeat_time
                    ),
                    "last_transition": iso_time(
                        c.last_transition_time
                    ),
                }
                for c in (
                    node.status.conditions or []
                )
            ],
            "capacity": node.status.capacity or {},
            "allocatable": node.status.allocatable or {},
            "addresses": [
                {
                    "type": a.type,
                    "address": a.address,
                }
                for a in (
                    node.status.addresses or []
                )
            ],
        }

        # ----------------------------------------------------
        # Pods running on node
        # ----------------------------------------------------

        try:

            pods = (
                self.core.list_pod_for_all_namespaces(
                    field_selector=(
                        f"spec.nodeName={node_name}"
                    )
                )
            )

            for pod in pods.items:

                investigation["pods"].append({
                    "namespace": pod.metadata.namespace,
                    "name": pod.metadata.name,
                    "phase": pod.status.phase,
                    "pod_ip": pod.status.pod_ip,
                    "ready": self.pod_ready(pod),
                })

        except Exception as e:

            investigation["pods_error"] = str(e)

        investigation["events"] = (
            self.get_node_events(
                node_name
            )
        )

        return investigation

    # ========================================================
    # EVENT HELPERS
    # ========================================================

    def get_pod_events(
        self,
        namespace,
        pod_name,
    ):

        return self.get_events(
            namespace,
            pod_name,
            "Pod",
        )

    def get_service_events(
        self,
        namespace,
        service_name,
    ):

        return self.get_events(
            namespace,
            service_name,
            "Service",
        )

    def get_deployment_events(
        self,
        namespace,
        deployment_name,
    ):

        return self.get_events(
            namespace,
            deployment_name,
            "Deployment",
        )

    def get_node_events(
        self,
        node_name,
    ):

        try:

            events = (
                self.core.list_event_for_all_namespaces()
            )

            result = []

            for event in events.items:

                ref = event.involved_object

                if (
                    ref.name == node_name
                    and ref.kind == "Node"
                ):

                    result.append({
                        "type": event.type,
                        "reason": event.reason,
                        "message": event.message,
                        "count": event.count,
                        "first_timestamp": iso_time(
                            event.first_timestamp
                        ),
                        "last_timestamp": iso_time(
                            event.last_timestamp
                        ),
                    })

            return result

        except Exception as e:

            return [{
                "error": str(e)
            }]

    def get_events(
        self,
        namespace,
        resource_name,
        resource_kind,
    ):

        try:

            events = (
                self.core.list_namespaced_event(
                    namespace
                )
            )

            result = []

            for event in events.items:

                ref = event.involved_object

                if (
                    ref.name == resource_name
                    and ref.kind == resource_kind
                ):

                    result.append({
                        "type": event.type,
                        "reason": event.reason,
                        "message": event.message,
                        "count": event.count,
                        "first_timestamp": iso_time(
                            event.first_timestamp
                        ),
                        "last_timestamp": iso_time(
                            event.last_timestamp
                        ),
                    })

            return result

        except Exception as e:

            return [{
                "error": str(e)
            }]

    # ========================================================
    # POD READY
    # ========================================================

    @staticmethod
    def pod_ready(pod):

        statuses = (
            pod.status.container_statuses or []
        )

        if not statuses:
            return False

        return all(
            c.ready
            for c in statuses
        )

    # ========================================================
    # ENGINE ERROR
    # ========================================================

    @staticmethod
    def engine_error(
        incident_type,
        message,
    ):

        return {
            "type": incident_type,
            "severity": "CRITICAL",
            "resource_type": "Cluster",
            "reason": message,
        }


# ============================================================
# Convenience functions
# ============================================================

def create_incident_engine(core):

    apps = client.AppsV1Api(
        api_client=core.api_client
    )

    return KubernetesIncidentEngine(
        core=core,
        apps=apps,
    )


def run_incident_scan(core):

    engine = create_incident_engine(core)

    return engine.scan_cluster()


def investigate_detected_incidents(
    core,
    scan_result,
):

    engine = create_incident_engine(core)

    results = []

    for incident in scan_result.get(
        "incidents",
        []
    ):

        investigation = (
            engine.investigate_incident(
                incident
            )
        )

        results.append({
            "incident": incident,
            "investigation": investigation,
        })

    return results




# # def detect_pod_incident(pod):
# #     incidents = []

# #     pod_name = pod.metadata.name
# #     namespace = pod.metadata.namespace

# #     # Check container statuses
# #     if pod.status.container_statuses:

# #         for container in pod.status.container_statuses:

# #             # --------------------------------------------------
# #             # 1. CrashLoopBackOff
# #             # --------------------------------------------------
# #             if container.state and container.state.waiting:

# #                 reason = container.state.waiting.reason

# #                 if reason == "CrashLoopBackOff":
# #                     incident = {
# #                         "type": "CRASH_LOOP",
# #                         "severity": "CRITICAL",
# #                         "pod": pod_name,
# #                         "namespace": namespace,
# #                         "container": container.name,
# #                         "reason": reason,
# #                         "restart_count": container.restart_count
# #                     }

# #                     # Get information about the previous termination
# #                     if container.last_state and container.last_state.terminated:
# #                         last = container.last_state.terminated

# #                         incident["exit_code"] = last.exit_code
# #                         incident["last_reason"] = last.reason

# #                     incidents.append(incident)
# #                     continue

# #             # --------------------------------------------------
# #             # 2. Currently terminated
# #             # --------------------------------------------------
# #             if container.state and container.state.terminated:

# #                 terminated = container.state.terminated

# #                 # OOMKilled
# #                 if terminated.reason == "OOMKilled":
# #                     incidents.append({
# #                         "type": "OOM_KILLED",
# #                         "severity": "CRITICAL",
# #                         "pod": pod_name,
# #                         "namespace": namespace,
# #                         "container": container.name,
# #                         "reason": terminated.reason,
# #                         "exit_code": terminated.exit_code,
# #                         "restart_count": container.restart_count
# #                     })
# #                     continue

# #                 # Genuine container failure
# #                 if terminated.exit_code != 0:
# #                     incidents.append({
# #                         "type": "CONTAINER_FAILED",
# #                         "severity": "CRITICAL",
# #                         "pod": pod_name,
# #                         "namespace": namespace,
# #                         "container": container.name,
# #                         "reason": terminated.reason,
# #                         "exit_code": terminated.exit_code,
# #                         "restart_count": container.restart_count
# #                     })
# #                     continue

# #             # --------------------------------------------------
# #             # 3. Previous container termination
# #             # --------------------------------------------------
# #             if container.last_state and container.last_state.terminated:

# #                 last = container.last_state.terminated

# #                 # OOMKilled
# #                 if last.reason == "OOMKilled":
# #                     incidents.append({
# #                         "type": "OOM_KILLED",
# #                         "severity": "CRITICAL",
# #                         "pod": pod_name,
# #                         "namespace": namespace,
# #                         "container": container.name,
# #                         "reason": last.reason,
# #                         "exit_code": last.exit_code,
# #                         "restart_count": container.restart_count
# #                     })
# #                     continue

# #                 # Graceful termination / SIGTERM
# #                 #
# #                 # Exit code 143 = 128 + SIGTERM(15)
# #                 # This usually means the process was asked to
# #                 # terminate gracefully.
# #                 if last.exit_code == 143 or last.reason == "Completed":
# #                     # Don't classify this as a failure.
# #                     continue

# #                 # Previous container genuinely failed
# #                 if last.exit_code != 0:
# #                     incidents.append({
# #                         "type": "PREVIOUS_CONTAINER_FAILED",
# #                         "severity": "WARNING",
# #                         "pod": pod_name,
# #                         "namespace": namespace,
# #                         "container": container.name,
# #                         "reason": last.reason,
# #                         "exit_code": last.exit_code,
# #                         "restart_count": container.restart_count
# #                     })
# #                     continue

# #             # --------------------------------------------------
# #             # 4. High restart count
# #             # --------------------------------------------------
# #             if container.restart_count > 5:
# #                 incidents.append({
# #                     "type": "HIGH_RESTART_COUNT",
# #                     "severity": "WARNING",
# #                     "pod": pod_name,
# #                     "namespace": namespace,
# #                     "container": container.name,
# #                     "restart_count": container.restart_count
# #                 })
# #                 continue

# #     return incidents