import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  { path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
  {
    path: "/profile",
    name: "profile",
    component: () => import("@/views/ProfileView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/",
    name: "chat",
    component: () => import("@/views/ChatView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/members",
    name: "members",
    component: () => import("@/views/MembersView.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/families",
    name: "families",
    component: () => import("@/views/FamiliesView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/dm/:userId",
    name: "dm",
    component: () => import("@/views/DmView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/gallery",
    name: "gallery",
    component: () => import("@/views/GalleryView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("@/views/SettingsView.vue"),
    meta: { requiresAuth: true },
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: "login" };
  }
  if (to.meta.requiresAdmin && !auth.user?.is_admin) {
    return { name: "chat" };
  }
  if (to.name === "login" && auth.isAuthenticated) {
    return auth.user ? { name: "chat" } : { name: "profile" };
  }
});

export default router;
