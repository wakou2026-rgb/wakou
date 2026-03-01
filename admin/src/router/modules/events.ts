const Layout = () => import("@/layout/index.vue");

export default {
  path: "/events",
  name: "Events",
  component: Layout,
  redirect: "/events/index",
  meta: {
    icon: "ep:clock",
    title: "系統日誌",
    rank: 8
  },
  children: [
    {
      path: "/events/index",
      name: "EventsIndex",
      component: () => import("@/views/events/index.vue"),
      meta: {
        title: "系統日誌"
      }
    }
  ]
} satisfies RouteConfigsTable;
