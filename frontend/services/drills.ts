import { apiRequest } from "../lib/api";
import type { DrillDetail, DrillListItem } from "../types/drills";

export function getDrillsBySport(sportId: string) {
  return apiRequest<DrillListItem[]>(`/sports/${sportId}/drills`);
}

export function getDrillById(drillId: string) {
  return apiRequest<DrillDetail>(`/drills/${drillId}`);
}
