import { apiRequest } from "../lib/api";
import type { SportOption } from "../types/sports";

export function getSports() {
  return apiRequest<SportOption[]>("/sports");
}
