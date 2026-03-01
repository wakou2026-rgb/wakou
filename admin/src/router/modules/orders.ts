const Layout = () => import("@/layout/index.vue");

export default {
  path: "/orders",
  name: "Orders",
  component: Layout,
  redirect: "/orders/index",
  meta: {
    icon: "ep:list",
    title: "訂單管理",
    rank: 2
  },
  children: [
    {
      path: "/orders/index",
      name: "OrdersIndex",
      component: () => import("@/views/orders/index.vue"),
      meta: {
        title: "訂單管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
