<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getProducts, createProduct, updateProduct, deleteProduct, type Product } from "@/api/products";
import { getCategories, type Category } from "@/api/categories";
import { ElMessage } from "element-plus";
import type { UploadFile } from "element-plus";

defineOptions({
  name: "ProductsIndex"
});


const loading = ref(true);
const products = ref<Product[]>([]);
const searchQuery = ref("");

const dialogVisible = ref(false);
const dialogType = ref<"create" | "edit">("create");
const formLoading = ref(false);
const uploadLoading = ref(false);

const formData = ref<Partial<Product>>({
  sku: "",
  name: "",
  category: "",
  price_twd: 0,
  grade: "A",
  availability: "available",
  brand: "",
  size: "",
  description: "",
  description_zh: "",
  description_ja: "",
  description_en: "",
  stock_qty: 0,
  cost_twd: 0,
  image_urls: []
});

const fileList = ref<UploadFile[]>([]);

const categories = ref<Category[]>([]);

const gradeOptions = [
  { value: "S", label: "S - 全新/近乎全新" },
  { value: "A", label: "A - 輕微使用痕跡" },
  { value: "B", label: "B - 一般使用痕跡" },
  { value: "C", label: "C - 明显使用痕迹" }
];

const availabilityOptions = [
  { value: "available", label: "上架" },
  { value: "negotiating", label: "議價中" },
  { value: "sold", label: "已售出" }
];

const loadData = async () => {
  try {
    loading.value = true;
    const params = searchQuery.value ? { q: searchQuery.value } : undefined;
    const res: any = await getProducts(params);
    if (res?.items) {
      products.value = res.items;
    } else if (Array.isArray(res)) {
      products.value = res;
    } else {
      products.value = [];
    }
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入商品");
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  loadData();
};

const handleCreate = () => {
  dialogType.value = "create";
  formData.value = {
    sku: "",
    name: "",
    category: "",
    price_twd: 0,
    grade: "A",
    availability: "available",
    brand: "",
    size: "",
    description: "",
    description_zh: "",
    description_ja: "",
    description_en: "",
    stock_qty: 0,
    cost_twd: 0,
    image_urls: []
  };
  fileList.value = [];
  dialogVisible.value = true;
};

const handleEdit = (row: Product) => {
  dialogType.value = "edit";
  formData.value = { ...row };
  
  // Convert image URLs to file list for display
  fileList.value = (row.image_urls || []).map((url, index) => ({
    name: `image_${index}`,
    url: url,
    status: 'success' as const
  }));
  
  dialogVisible.value = true;
};

const handleDelete = async (row: Product) => {
  if (!row.id) return;
  try {
    await deleteProduct(row.id);
    ElMessage.success("刪除成功");
    loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "刪除失敗");
  }
};

// Image upload handlers
const handleImageChange = (uploadFile: UploadFile) => {
  // In a real implementation, you would upload to a server
  // For now, we'll use local URL preview
  if (uploadFile.url) {
    const currentImages = formData.value.image_urls || [];
    if (!currentImages.includes(uploadFile.url)) {
      formData.value.image_urls = [...currentImages, uploadFile.url];
    }
  }
};

const handleImageRemove = (file: UploadFile) => {
  const url = file.url;
  if (url) {
    formData.value.image_urls = (formData.value.image_urls || []).filter(img => img !== url);
  }
};

const handleExceed = () => {
  ElMessage.warning("最多只能上傳 5 張圖片");
};

// Simple image URL input
const imageUrlInput = ref("");

const addImageUrl = () => {
  if (!imageUrlInput.value) return;
  
  const url = imageUrlInput.value.trim();
  const currentImages = formData.value.image_urls || [];
  
  if (!currentImages.includes(url)) {
    formData.value.image_urls = [...currentImages, url];
    fileList.value.push({
      name: `image_${currentImages.length}`,
      url: url,
      status: 'success'
    });
  }
  
  imageUrlInput.value = "";
};

const removeImage = (url: string) => {
  formData.value.image_urls = (formData.value.image_urls || []).filter(img => img !== url);
  fileList.value = fileList.value.filter(f => f.url !== url);
};

const submitForm = async () => {
  if (!formData.value.sku || !formData.value.category || !formData.value.price_twd || !formData.value.name) {
    ElMessage.warning("請填寫必要欄位（SKU、商品名、分類、價格）");
    return;
  }
  
  try {
    formLoading.value = true;
    
    // Ensure image_urls is an array
    const zhName =
      typeof formData.value.name === "string"
        ? formData.value.name.trim()
        : formData.value.name?.["zh-Hant"] || "";
    const jaName =
      typeof formData.value.name === "object" && formData.value.name !== null
        ? formData.value.name.ja || zhName
        : zhName;
    const enName =
      typeof formData.value.name === "object" && formData.value.name !== null
        ? formData.value.name.en || zhName
        : zhName;

    const submitData = {
      ...formData.value,
      category: formData.value.category || "watch",
      name: {
        "zh-Hant": zhName,
        ja: jaName,
        en: enName
      },
      description: {
        "zh-Hant": formData.value.description_zh || formData.value.description || "",
        ja: formData.value.description_ja || formData.value.description || "",
        en: formData.value.description_en || formData.value.description || ""
      },
      image_urls: formData.value.image_urls || []
    };
    
    if (dialogType.value === "create") {
      await createProduct(submitData);
      ElMessage.success("新增成功");
    } else {
      await updateProduct(formData.value.id!, submitData);
      ElMessage.success("更新成功");
    }
    dialogVisible.value = false;
    loadData();
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (Array.isArray(detail)) {
      const firstMsg = detail[0]?.msg;
      ElMessage.error(firstMsg || "儲存失敗");
    } else if (typeof detail === "string") {
      ElMessage.error(detail);
    } else {
      ElMessage.error(error?.message || "儲存失敗");
    }
  } finally {
    formLoading.value = false;
  }
};

const getCategoryLabel = (category: string) => {
  const found = categories.value.find(c => c.id === category);
  return found ? found.title["zh-Hant"] : category;
};

const getGradeLabel = (grade: string) => {
  return gradeOptions.find(g => g.value === grade)?.label || grade;
};

const getAvailabilityLabel = (availability: string) => {
  return availabilityOptions.find(a => a.value === availability)?.label || availability;
};

onMounted(async () => {
  try {
    const res: any = await getCategories();
    if (Array.isArray(res)) {
      categories.value = res;
    } else if (Array.isArray(res?.items)) {
      categories.value = res.items;
    } else if (Array.isArray(res?.data?.items)) {
      categories.value = res.data.items;
    } else if (res?.data && Array.isArray(res.data)) {
      categories.value = res.data;
    }
  } catch {
    // categories load failure is non-fatal
  }
  loadData();
});
</script>

<template>
  <div class="p-4">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <div class="flex gap-2">
            <el-input
              v-model="searchQuery"
              placeholder="搜尋商品（名稱，品牌）"
              style="width: 250px"
              clearable
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            />
            <el-button type="primary" @click="handleSearch">搜尋</el-button>
          </div>
          <el-button type="success" @click="handleCreate">新增商品</el-button>
        </div>
      </template>

      <el-table :data="products" v-loading="loading" style="width: 100%" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="圖片" width="80">
          <template #default="{ row }">
            <el-image 
              v-if="row.image_urls && row.image_urls.length > 0"
              :src="row.image_urls[0]" 
              style="width: 50px; height: 50px"
              fit="cover"
            />
            <span v-else class="text-gray-400">無圖</span>
          </template>
        </el-table-column>
        <el-table-column prop="sku" label="SKU" width="120" />
        <el-table-column prop="name" label="商品名稱" min-width="180" />
        <el-table-column prop="category" label="分類" width="100">
          <template #default="{ row }">
            {{ getCategoryLabel(row.category) }}
          </template>
        </el-table-column>
        <el-table-column prop="brand" label="品牌" width="120" />
        <el-table-column prop="price_twd" label="價格 (TWD)" width="120">
          <template #default="{ row }">
            ${{ row.price_twd?.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="grade" label="成色" width="80">
          <template #default="{ row }">
            {{ row.grade }}
          </template>
        </el-table-column>
        <el-table-column prop="availability" label="狀態" width="100">
          <template #default="{ row }">
            <el-tag :type="row.availability === 'available' ? 'success' : row.availability === 'sold' ? 'danger' : 'warning'" size="small">
              {{ getAvailabilityLabel(row.availability) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">編輯</el-button>
            <el-popconfirm title="確定要刪除嗎？" @confirm="handleDelete(row)">
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
      :title="dialogType === 'create' ? '新增商品' : '編輯商品'"
      width="700px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="SKU" required>
          <el-input v-model="formData.sku" placeholder="例如: WK-WATCH-001" />
        </el-form-item>
        <el-form-item label="商品名稱" required>
          <el-input v-model="formData.name" placeholder="商品名稱" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分類">
              <el-select v-model="formData.category" placeholder="選擇分類" style="width: 100%">
                <el-option
                  v-for="item in categories"
                  :key="item.id"
                  :label="item.title['zh-Hant']"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-input v-model="formData.brand" placeholder="品牌名稱" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="價格 (TWD)" required>
              <el-input-number v-model="formData.price_twd" :min="0" :step="1000" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="成色">
              <el-select v-model="formData.grade" placeholder="選擇成色" style="width: 100%">
                <el-option
                  v-for="item in gradeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="尺寸">
              <el-input v-model="formData.size" placeholder="例如: 38mm" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="狀態">
              <el-select v-model="formData.availability" placeholder="選擇狀態" style="width: 100%">
                <el-option
                  v-for="item in availabilityOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- Image Upload Section -->
        <el-form-item label="商品圖片">
          <div class="image-upload-section">
            <!-- Image URL Input -->
            <div class="flex gap-2 mb-2">
              <el-input 
                v-model="imageUrlInput" 
                placeholder="輸入圖片網址" 
                @keyup.enter="addImageUrl"
              />
              <el-button @click="addImageUrl" type="primary">新增</el-button>
            </div>
            
            <!-- Image Preview Grid -->
            <div v-if="formData.image_urls && formData.image_urls.length > 0" class="image-preview-grid">
              <div 
                v-for="(url, index) in formData.image_urls" 
                :key="index" 
                class="image-preview-item"
              >
                <el-image 
                  :src="url" 
                  :preview-src-list="formData.image_urls"
                  :initial-index="index"
                  fit="cover"
                  style="width: 100%; height: 100%"
                />
                <div class="image-remove-btn">
                  <el-button 
                    type="danger" 
                    size="small" 
                    circle 
                    @click="removeImage(url)"
                  >
                    ×
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty v-else description="尚無圖片，請輸入圖片網址" :image-size="60" />
          </div>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="商品描述" />
        </el-form-item>

        <!-- Multilingual descriptions -->
        <el-form-item label="中文描述">
          <el-input v-model="formData.description_zh" type="textarea" :rows="2" placeholder="中文描述" />
        </el-form-item>
        <el-form-item label="日文描述">
          <el-input v-model="formData.description_ja" type="textarea" :rows="2" placeholder="日本語説明" />
        </el-form-item>
        <el-form-item label="英文描述">
          <el-input v-model="formData.description_en" type="textarea" :rows="2" placeholder="English description" />
        </el-form-item>

        <!-- Stock and cost in a row -->
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="庫存數量">
              <el-input-number v-model="formData.stock_qty" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="採購成本 (TWD)">
              <el-input-number v-model="formData.cost_twd" :min="0" :step="1000" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="submitForm">確認</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.image-upload-section {
  width: 100%;
}
.image-preview-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-top: 10px;
}
.image-preview-item {
  position: relative;
  width: 100%;
  padding-top: 100%; /* 1:1 aspect ratio */
  border: 1px solid #eee;
  border-radius: 4px;
  overflow: hidden;
}
.image-preview-item .el-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
.image-remove-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  z-index: 10;
}
.mb-2 {
  margin-bottom: 8px;
}
</style>
