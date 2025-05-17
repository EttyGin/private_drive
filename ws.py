@dataclass
class Workspace:
    name: str
    owner: str
    status: str
    created_at: datetime
    resources: dict
    pod_name: str  # קישור טכני למטה

class WorkspaceManager:
    def __init__(self, pod_controller: PodController):
        self.pod_controller = pod_controller

    def list_workspaces(self) -> List[Workspace]:
        pods = self.pod_controller.list_pods()
        workspaces = []
        for pod in pods:
            if self._is_workspace_pod(pod):  # פילטר על פודים שרלוונטיים
                workspaces.append(self._pod_to_workspace(pod))
        return workspaces

    def _is_workspace_pod(self, pod: PodSchema) -> bool:
        return pod.labels.get("type") == "workspace"

    def _pod_to_workspace(self, pod: PodSchema) -> Workspace:
        return Workspace(
            name=pod.labels.get("workspace-name", pod.name),
            owner=pod.labels.get("owner", "unknown"),
            status=pod.status,
            created_at=pod.created_at,
            resources=pod.resources,
            pod_name=pod.name
        )
