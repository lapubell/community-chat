const BASE = "";

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData) && typeof options.body !== "string") {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(BASE + path, { ...options, headers });
  // 401 = not authenticated, 403 = authenticated but not allowed, 405 =
  // method not allowed (a symptom of a stale/broken response, e.g. an old
  // cached SPA hitting the API). All three mean the current session is
  // invalid or the request can't proceed — drop it and let the SPA redirect
  // to login via the router (a full-page reload would fight the router).
  if (res.status === 401 || res.status === 403 || res.status === 405) {
    setToken(null);
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    throw new Error(res.status === 401 ? "Unauthorized" : "Session expired");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d) => d.msg).join(", ");
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
  upload: (path, formData) => request(path, { method: "POST", body: formData }),
};

export function wsUrl() {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws?token=${encodeURIComponent(getToken() || "")}`;
}
