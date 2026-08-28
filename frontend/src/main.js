import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import "./style.css";
import "./sw-register.js";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);

// When an API call comes back 401 (stale/revoked token), drop the in-memory
// session and route to the login screen via the SPA (no full-page reload).
window.addEventListener("auth:unauthorized", () => {
  const auth = useAuthStore(pinia);
  // api.js already cleared the localStorage token; clear the in-memory
  // session too so the router guard treats us as logged out.
  auth.closeWs();
  auth.token = null;
  auth.user = null;
  auth.users = [];
  if (router.currentRoute.value.name !== "login") {
    router.push({ name: "login" });
  }
});

app.mount("#app");
