import { clearAuthToken, getAuthToken } from "./auth";

function normalizeApiBaseUrl(url: string) {
  return url.replace(/\/+$/, "");
}

function resolveApiBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configuredUrl) {
    return normalizeApiBaseUrl(configuredUrl);
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${window.location.hostname}:8000/api`;
  }

  return "http://127.0.0.1:8000/api";
}

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

type ApiRequestOptions = RequestInit & {
  auth?: boolean;
};

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {}
) {
  const { auth = true, headers, body, ...rest } = options;
  const apiBaseUrl = resolveApiBaseUrl();
  const requestUrl = `${apiBaseUrl}${path}`;
  const requestHeaders = new Headers(headers);

  if (!(body instanceof FormData) && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = getAuthToken();
    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  let response: Response;

  try {
    response = await fetch(requestUrl, {
      ...rest,
      body,
      headers: requestHeaders,
      cache: "no-store"
    });
  } catch (error) {
    const cause =
      error instanceof Error && error.message
        ? ` (${error.message})`
        : "";

    throw new ApiError(
      `Unable to reach the TrainUp API at ${apiBaseUrl}. Check that the backend is running and the API URL is correct${cause}.`,
      0,
      {
        detail: "API_UNREACHABLE",
        path,
        request_url: requestUrl
      }
    );
  }

  const responseText = await response.text();
  let payload: unknown = null;
  if (responseText) {
    try {
      payload = JSON.parse(responseText);
    } catch {
      payload = responseText;
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
    }

    const message =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "Request failed.";

    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}

export function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (
      typeof error.payload === "object" &&
      error.payload !== null &&
      "errors" in error.payload &&
      Array.isArray(error.payload.errors) &&
      error.payload.errors.length > 0
    ) {
      const firstError = error.payload.errors[0];
      if (
        typeof firstError === "object" &&
        firstError !== null &&
        "msg" in firstError &&
        typeof firstError.msg === "string"
      ) {
        return firstError.msg;
      }
    }

    if (Array.isArray(error.payload) && error.payload.length > 0) {
      const firstError = error.payload[0];
      if (
        typeof firstError === "object" &&
        firstError !== null &&
        "msg" in firstError &&
        typeof firstError.msg === "string"
      ) {
        return firstError.msg;
      }
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong. Please try again.";
}
