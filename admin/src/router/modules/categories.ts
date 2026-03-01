const Layout = () => import("@/layout/index.vue");

export default {
  path: "/categories",
  name: "Categories",
  component: Layout,
  redirect: "/categories/index",
  meta: {
    icon: "ep:grid",
    title: "分類管理",
    rank: 2
  },
  children: [
    {
      path: "/categories/index",
      name: "CategoriesIndex",
      component: () => import("@/views/categories/index.vue"),
      meta: {
        title: "分類管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
