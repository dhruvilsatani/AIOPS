


from kubernetes import client, config
from incident_detector import run_incident_scan, investigate_detected_incidents


config.load_kube_config()


core = client.CoreV1Api()


scan_result= run_incident_scan(core)
print("incidents :")
print (scan_result)
investation = investigate_detected_incidents(core, scan_result)
print ()

print("INVESTIGATIONS:")
print(investation)



# pods = v1.list_pod_for_all_namespaces()
# for pod in pods.items:
#     namespace  = pod.metadata.namespace 
#     name = pod.metadata.name
#     status = pod.status.phase
#     print (f"{namespace:20}{name:50}{status}")




# apps = client.AppsV1Api()

# deployments = apps.list_deployment_for_all_namespaces()

# print(f"{'NAMESPACE':<20}{'DEPLOYMENT':<40}{'READY':<10}{'DESIRED':<10}")

# for deployment in deployments.items:
#     namespace = deployment.metadata.namespace
#     name = deployment.metadata.name

#     ready = deployment.status.ready_replicas or 0
#     desired = deployment.spec.replicas or 0

#     print(f"{namespace:<20}{name:<40}{ready:<10}{desired:<10}")


# core = client.CoreV1Api()
# services = core.list_service_for_all_namespaces()
# for service in services.items:
#     namespace = service.metadata.namespace
#     name= service.metadata.name
#     service_type= service.spec.type
#     cluster_ip= service.spec.cluster_ip

#     print(f"{namespace:<20}{name:<40}{service_type:<20}{cluster_ip:<20}")


# events= core.list_event_for_all_namespaces()
# for event in events.items:
#     namespace = event.metadata.namespace
#     event_type =event.type
#     reason= event.reason or ""
#     message = event.message or ""

#     print(
#         f"{namespace:<20}"
#         f"{event_type:<10}"
#         f"{reason:<25}"
#         f"{message:<80}"

#     )
# print ()

# print()
# print(" ==== 🚨 POD HEALTH ======")

# pods = core.list_pod_for_all_namespaces()

# for pod in pods.items:
#     namespace = pod.metadata.namespace
#     name = pod.metadata.name
#     phase = pod.status.phase
#     restart_count = 0
#     if pod.status.container_statuses:
#         for container in pod.status.container_statuses:
#             restart_count += container.restart_count

#     if restart_count >= 5:
#         print(
#             f"⚠️ {namespace}/{name} "
#             f"has restarted {restart_count}"
#         )        
#     if pod.status.container_statuses:
#         for container in pod.status.container_statuses:
#             container_name = container.name
#             if container.state.waiting:
#                 reason = container.state.waiting.reason
#                 print(
#                     f"⚠️ {namespace}/{name}"
#                     f"container={container_name}"
#                     f"state=WAITING reason ={reason}"
#                 )
#             elif container.state.terminated:
#                reason = container.state.terminated.reason
#                terminated= container.state.terminated
#                print(
#                 f"❌ {namespace}/{name}"
#                 f"container ={container_name}"
#                 f"state=TERMINATED "
#                 f"reason={terminated.reason}"
#                 f"exit_code={terminated.exit_code}"


#         )
#             elif container.state.running:
#                 print(
#                     f"✅ {namespace }/ {name}"
#                     f"container={container_name}"
#                     f"state=RUNNING"
#                 )
#                 if container.last_state.terminated:
#                     last= container.last_state.terminated
#                     print(
#                         f"  ↳ Last termination: "
#                         f"reason={last.reason}"
#                         f"exit_code={last.exit_code}"

#                     )
#             print(
#             f"{namespace:20}"
#             f"{name:55}"
#             f"status={phase:12}"
#             f"restarts={restart_count}"



#             )

# print ()
# print (" ====== SUSPICIOUS POD LOGS ====")


# for pod in pods.items:
#     namespace = pod.metadata.namespace 
#     pod_name= pod.metadata.name
#     if  not pod.status.container_statuses:
#         continue 
#     for container in pod.status.container_statuses:
#         restart_count = container.restart_count
#         if restart_count >=5:

#            print()
#            print(f"🚨 {namespace}/{pod_name} ")
#            print(f"Container: {container.name}")
#            print(f"Restarts: {restart_count}")
#            try:
#                 logs = core.read_namespaced_pod_log(
#                     name=pod_name,
#                     namespace=namespace,
#                     container=container.name,
#                     tail_lines=20
#                 )   
#                 print (" _______Last 20 logs lines _____")
#                 print (logs)
#            except Exception as e:
#                 print(f"could not get logs : {e}")



# print()
# print("===== 🚨 INCIDENT DETECTION =====")

# for pod in pods.items:

#     namespace = pod.metadata.namespace
#     pod_name = pod.metadata.name

#     if not pod.status.container_statuses:
#         continue

#     for container in pod.status.container_statuses:

#         restart_count = container.restart_count

#         if container.state.waiting:
#             reason = container.state.waiting.reason

#             if reason == "CrashLoopBackOff":
#                 print(
#                     f"🚨 INCIDENT: {namespace}/{pod_name} "
#                     f"container={container.name} "
#                     f"is in CrashLoopBackOff "
#                     f"with {restart_count} restarts"
#                 )

#         if container.last_state.terminated:
#             last = container.last_state.terminated

#             if last.exit_code != 0:
#                 print(
#                     f"⚠️ FAILURE: {namespace}/{pod_name} "
#                     f"container={container.name} "
#                     f"last exit code={last.exit_code} "
#                     f"reason={last.reason}"
#                 )                

# for pod in pods.items:
#     incidents = detect_pod_incident(pod)
#     if incidents:
#         investigation = investigate_pod(core,pod)
      
#         print("\n🔎 INVESTIGATION")
#         print(investigation)