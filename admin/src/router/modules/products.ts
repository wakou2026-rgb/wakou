const Layout = () => import("@/layout/index.vue");

export default {
  path: "/products",
  name: "Products",
  component: Layout,
  redirect: "/products/index",
  meta: {
    icon: "ep:goods",
    title: "商品管理",
    rank: 3
  },
  children: [
    {
      path: "/products/index",
      name: "ProductsIndex",
      component: () => import("@/views/products/index.vue"),
      meta: {
        title: "商品管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
