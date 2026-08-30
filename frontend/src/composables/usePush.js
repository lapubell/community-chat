import { reactive } from "vue";
import { api, getToken } from "@/api";

// Shared reactive state so the Settings toggle and any other view stay in sync.
const state = reactive({
  supported: "serviceWorker" in navigator && "PushManager" in window && "Notification" in window,
  permission: typeof Notification !== "undefined" ? Notification.permission : "denied",
  subscribed: false,
  busy: false,
  error: null,
});

function setPermission(p) {
  state.permission = p;
}

// Decode a base64url string to an ArrayBuffer (the VAPID public key format the
// browser's pushManager.subscribe expects).
function base64UrlToArrayBuffer(base64Url) {
  const padding = base64Url.length % 4 === 0 ? "" : "=".repeat(4 - (base64Url.length % 4));
  const base64 = (base64Url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const latin1 = atob(base64);
  const bytes = new Uint8Array(latin1.length);
  for (let i = 0; i < latin1.length; i++) bytes[i] = latin1.charCodeAt(i);
  return bytes.buffer;
}

async function getRegistration() {
  // `.ready` resolves once the currently-active controller is ready; fall back
  // to the registration itself if that's not available yet.
  return (
    (await navigator.serviceWorker.getRegistration()) ||
    (await navigator.serviceWorker.ready)
  );
}

export async function pushStatus() {
  // Reflect the current browser permission.
  if (typeof Notification !== "undefined") {
    setPermission(Notification.permission);
  }
  // Are we already subscribed? Check the registration's subscription.
  if (state.supported) {
    try {
      const reg = await getRegistration();
      const sub = await reg.pushManager.getSubscription();
      state.subscribed = Boolean(sub);
    } catch {
      state.subscribed = false;
    }
  }
}

export async function subscribePush() {
  if (!state.supported) {
    state.error = "Push notifications are not supported in this browser.";
    return false;
  }
  if (state.busy) return false;
  state.busy = true;
  state.error = null;
  try {
    // 1. Permission.
    let perm = Notification.permission;
    if (perm === "default") perm = await Notification.requestPermission();
    setPermission(perm);
    if (perm !== "granted") {
      state.error = "Notification permission was not granted.";
      return false;
    }

    // 2. VAPID public key from the server.
    const { public_key } = await api.get("/api/push/key");
    const reg = await getRegistration();
    const existing = await reg.pushManager.getSubscription();
    if (existing) {
      await existing.unsubscribe();
    }

    // 3. Subscribe (or create a new subscription).
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64UrlToArrayBuffer(public_key),
    });

    // 4. Store the subscription on the server.
    const json = sub.toJSON();
    await api.post("/api/push/subscribe", {
      endpoint: json.endpoint,
      keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
    });

    state.subscribed = true;
    return true;
  } catch (err) {
    state.error = err?.message || "Could not enable notifications.";
    state.subscribed = false;
    return false;
  } finally {
    state.busy = false;
  }
}

export async function unsubscribePush() {
  if (!state.supported) return false;
  state.busy = true;
  try {
    const reg = await getRegistration();
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await api.del(`/api/push/subscribe?endpoint=${encodeURIComponent(sub.endpoint)}`).catch(() => {});
      await sub.unsubscribe();
    }
    state.subscribed = false;
    return true;
  } finally {
    state.busy = false;
  }
}

export function usePush() {
  return state;
}
