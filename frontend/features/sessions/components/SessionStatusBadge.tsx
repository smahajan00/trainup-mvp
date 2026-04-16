import { Badge } from "../../../components/ui/badge";
import type { SessionStatus } from "../../../types/sessions";

export function SessionStatusBadge({ status }: { status: SessionStatus }) {
  if (status === "COMPLETED") {
    return <Badge variant="success">Completed</Badge>;
  }

  if (status === "ABORTED") {
    return <Badge variant="danger">Aborted</Badge>;
  }

  return <Badge variant="accent">Active</Badge>;
}
