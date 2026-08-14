import { createRouter, createWebHistory } from "vue-router";
import { supabase } from "../lib/supabase";

const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/login",
    name: "login",
    component: () => import("../views/Login.vue"),
  },
  {
    path: "/forgot-password",
    name: "forgot",
    component: () => import("../views/ForgotPassword.vue"),
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: () => import("../views/Dashboard.vue"),
    meta: { auth: true },
  },
  {
    path: "/analytics",
    name: "analytics",
    component: () => import("../views/Analytics.vue"),
    meta: { auth: true },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("../views/Profile.vue"),
    meta: { auth: true },
  },
  { path: "/profile", redirect: { name: "settings" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const { data } = await supabase.auth.getSession();
  if (to.meta.auth && !data.session) return { name: "login" };
  if ((to.name === "login" || to.name === "forgot") && data.session)
    return { name: "dashboard" };
});

export default router;
