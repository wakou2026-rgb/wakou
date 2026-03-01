const Layout = () => import("@/layout/index.vue");

export default {
  path: "/finance",
  name: "Finance",
  component: Layout,
  redirect: "/finance/index",
  meta: {
    icon: "ep:money",
    title: "財務報表",
    rank: 6,
    roles: ["admin", "super_admin"]
  },
  children: [
    {
      path: "/finance/index",
      name: "FinanceIndex",
      component: () => import("@/views/finance/index.vue"),
      meta: {
        title: "財務報表"
      }
    }
  ]
} satisfies RouteConfigsTable;
