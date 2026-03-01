const Layout = () => import("@/layout/index.vue");

export default {
  path: "/shipping",
  name: "Shipping",
  component: Layout,
  redirect: "/shipping/index",
  meta: {
    icon: "ep:van",
    title: "出貨管理",
    rank: 7
  },
  children: [
    {
      path: "/shipping/index",
      name: "ShippingIndex",
      component: () => import("@/views/shipping/index.vue"),
      meta: {
        title: "出貨管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
