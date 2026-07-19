// Tiny fetch wrapper used by all pages. Errors from the API are returned as
// { code, message, details } - we surface them as Error subclasses so callers
// can switch on `err.code` if they want to render stage-specific UI.

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiRequestError extends Error {
  code: string;
  details: Record<string, unknown>;
  constructor(payload: ApiError) {
    super(payload.message);
    this.code = payload.code;
    this.details = payload.details || {};
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    if (body instanceof FormData) {
      init.body = body;
    } else {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
  }
  const res = await fetch(`/api${path}`, init);
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok && data && typeof data === "object") {
    throw new ApiRequestError(data as ApiError);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
};
