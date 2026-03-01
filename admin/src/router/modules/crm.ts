const Layout = () => import("@/layout/index.vue");

export default {
  path: "/crm",
  name: "CRM",
  component: Layout,
  redirect: "/crm/index",
  meta: {
    icon: "ep:user",
    title: "會員管理",
    rank: 5
  },
  children: [
    {
      path: "/crm/index",
      name: "CRMIndex",
      component: () => import("@/views/crm/index.vue"),
      meta: {
        title: "會員管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
