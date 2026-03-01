const Layout = () => import("@/layout/index.vue");

export default {
  path: "/reviews",
  name: "Reviews",
  component: Layout,
  redirect: "/reviews/index",
  meta: {
    icon: "ep:chat-line-square",
    title: "評價管理",
    rank: 7
  },
  children: [
    {
      path: "/reviews/index",
      name: "ReviewsIndex",
      component: () => import("@/views/reviews/index.vue"),
      meta: {
        title: "評價管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
