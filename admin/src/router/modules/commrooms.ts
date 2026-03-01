const Layout = () => import("@/layout/index.vue");

export default {
  path: "/commrooms",
  name: "CommRooms",
  component: Layout,
  redirect: "/commrooms/index",
  meta: {
    icon: "ep:chat-dot-round",
    title: "對話管理",
    rank: 6
  },
  children: [
    {
      path: "/commrooms/index",
      name: "CommRoomsIndex",
      component: () => import("@/views/commrooms/index.vue"),
      meta: {
        title: "對話管理"
      }
    }
  ]
} satisfies RouteConfigsTable;
