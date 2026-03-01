<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory
} from "@/api/categories";
import type { Category } from "@/api/categories";
import { ElMessage } from "element-plus";

defineOptions({
  name: "CategoriesIndex"
});

const loading = ref(true);
const categories = ref<Category[]>([]);

const dialogVisible = ref(false);
const dialogType = ref<"create" | "edit">("create");
const formLoading = ref(false);

const formData = ref<Partial<Category>>({
  id: "",
  title: { "zh-Hant": "", ja: "", en: "" },
  image: "",
  sort_order: 0,
  is_active: true
});

const loadData = async () => {
  try {
    loading.value = true;
    const res: unknown = await getCategories();
    if (Array.isArray(res)) {
      categories.value = res;
    } else if (
      res &&
      typeof res === "object" &&
      "items" in res &&
      Array.isArray((res as { items: Category[] }).items)
    ) {
      categories.value = (res as { items: Category[] }).items;
    } else {
      categories.value = [];
    }
  } catch (error: unknown) {
    const msg =
      error instanceof Error ? error.message : "無法載入分類";
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
};

const handleCreate = () => {
  dialogType.value = "create";
  formData.value = {
    id: "",
    title: { "zh-Hant": "", ja: "", en: "" },
    image: "",
    sort_order: 0,
    is_active: true
  };
  dialogVisible.value = true;
};

const handleEdit = (row: Category) => {
  dialogType.value = "edit";
  formData.value = {
    ...row,
    title: { ...row.title }
  };
  dialogVisible.value = true;
};

const handleDelete = async (row: Category) => {
  if (!row.id) return;
  try {
    await deleteCategory(row.id);
    ElMessage.success("刪除成功");
    loadData();
  } catch (error: unknown) {
    const msg =
      error instanceof Error ? error.message : "刪除失敗";
    ElMessage.error(msg);
  }
};

const submitForm = async () => {
  if (
    !formData.value.title?.["zh-Hant"] ||
    !formData.value.title?.ja ||
    !formData.value.title?.en
  ) {
    ElMessage.warning("請填寫所有名稱欄位");
    return;
  }
  if (dialogType.value === "create" && !formData.value.id) {
    ElMessage.warning("請填寫分類 ID");
    return;
  }

  try {
    formLoading.value = true;
    if (dialogType.value === "create") {
      await createCategory(formData.value);
      ElMessage.success("新增成功");
    } else {
      await updateCategory(formData.value.id!, formData.value);
      ElMessage.success("更新成功");
    }
    dialogVisible.value = false;
    loadData();
  } catch (error: unknown) {
    const msg =
      error instanceof Error ? error.message : "儲存失敗";
    ElMessage.error(msg);
  } finally {
    formLoading.value = false;
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
          <span class="text-lg font-bold">分類管理</span>
          <el-button type="success" @click="handleCreate"
            >新增分類</el-button
          >
        </div>
      </template>

      <el-table
        :data="categories"
        v-loading="loading"
        style="width: 100%"
        border
      >
        <el-table-column prop="id" label="ID" width="120" />
        <el-table-column label="圖片" width="80">
          <template #default="{ row }">
            <el-image
              v-if="row.image"
              :src="row.image"
              style="width: 50px; height: 50px"
              fit="cover"
            />
            <span v-else class="text-gray-400">無圖</span>
          </template>
        </el-table-column>
        <el-table-column label="中文名稱" min-width="140">
          <template #default="{ row }">
            {{ row.title?.["zh-Hant"] }}
          </template>
        </el-table-column>
        <el-table-column label="日文名稱" min-width="140">
          <template #default="{ row }">
            {{ row.title?.ja }}
          </template>
        </el-table-column>
        <el-table-column label="英文名稱" min-width="140">
          <template #default="{ row }">
            {{ row.title?.en }}
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="啟用狀態" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.is_active ? 'success' : 'danger'"
              size="small"
            >
              {{ row.is_active ? "啟用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)"
              >編輯</el-button
            >
            <el-popconfirm
              title="確定要刪除嗎？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger">刪除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新增分類' : '編輯分類'"
      width="600px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="分類 ID" required>
          <el-input
            v-model="formData.id"
            placeholder="例如: watch"
            :disabled="dialogType === 'edit'"
          />
        </el-form-item>
        <el-form-item label="中文名稱" required>
          <el-input
            v-model="formData.title!['zh-Hant']"
            placeholder="例如: 經典腕錶"
          />
        </el-form-item>
        <el-form-item label="日文名稱" required>
          <el-input
            v-model="formData.title!.ja"
            placeholder="例如: クラシックウォッチ"
          />
        </el-form-item>
        <el-form-item label="英文名稱" required>
          <el-input
            v-model="formData.title!.en"
            placeholder="例如: Classic Watches"
          />
        </el-form-item>
        <el-form-item label="圖片路徑">
          <el-input
            v-model="formData.image"
            placeholder="例如: /Watches.png"
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="排序順序">
              <el-input-number
                v-model="formData.sort_order"
                :min="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="啟用">
              <el-switch v-model="formData.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="submitForm"
          >確認</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>
