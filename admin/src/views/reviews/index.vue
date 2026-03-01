<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getReviews, toggleReviewHidden, type Review } from "@/api/reviews";
import { ElMessage } from "element-plus";

defineOptions({
  name: "ReviewsIndex"
});

const loading = ref(true);
const reviews = ref<Review[]>([]);

const loadData = async () => {
  try {
    loading.value = true;
    const res = await getReviews();
    reviews.value = Array.isArray(res) ? res : ((res as any).data || []);
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入評價");
  } finally {
    loading.value = false;
  }
};

const handleToggleHidden = async (row: Review) => {
  try {
    await toggleReviewHidden(row.id);
    ElMessage.success("狀態切換成功");
    row.hidden = !row.hidden;
  } catch (error: any) {
    ElMessage.error(error?.message || "狀態切換失敗");
    await loadData();
  }
};

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>評價管理</span>
        </div>
      </template>

      <el-table :data="reviews" v-loading="loading" style="width: 100%" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="buyer_email" label="買家" width="200" />
        <el-table-column prop="product_id" label="商品 ID" width="100" />
        <el-table-column prop="rating" label="評分" width="120">
          <template #default="{ row }">
            <el-rate :model-value="row.rating" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="評論" />
        <el-table-column label="狀態" width="100">
          <template #default="{ row }">
            <el-tag :type="row.hidden ? 'info' : 'success'" size="small">
              {{ row.hidden ? '已隱藏' : '公開' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link :type="row.hidden ? 'success' : 'warning'" @click="handleToggleHidden(row)">
              {{ row.hidden ? '顯示' : '隱藏' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
