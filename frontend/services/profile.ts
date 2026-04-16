import { apiRequest } from "../lib/api";
import type {
  ProfileEnvelopeResponse,
  ProfileResponse,
  ProfileUpsertRequest
} from "../types/profile";

export function getProfile() {
  return apiRequest<ProfileEnvelopeResponse>("/profile");
}

export function upsertProfile(payload: ProfileUpsertRequest) {
  return apiRequest<ProfileResponse>("/profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}
