const Layout = () => import("@/layout/index.vue");

export default {
  path: "/magazine",
  name: "Magazine",
  component: Layout,
  redirect: "/magazine/index",
  meta: {
    icon: "ep:document",
    title: "雜誌文章",
    rank: 4
  },
  children: [
    {
      path: "/magazine/index",
      name: "MagazineIndex",
      component: () => import("@/views/magazine/index.vue"),
      meta: {
        title: "雜誌文章"
      }
    }
  ]
} satisfies RouteConfigsTable;
