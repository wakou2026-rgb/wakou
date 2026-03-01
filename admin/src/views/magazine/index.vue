<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  getArticles,
  createArticle,
  updateArticle,
  deleteArticle,
  toggleArticlePublish,
  zhHant,
  type Article,
  type LocaleText
} from "@/api/magazine";
import { ElMessage } from "element-plus";

defineOptions({
  name: "MagazineIndex"
});

// ── Block types ────────────────────────────────────────────
type BlockType = "hero" | "text" | "image" | "quote" | "image_text";

interface LocaleField {
  zh_hant: string;
  ja: string;
  en: string;
}

interface HeroBlock       { type: "hero";       image_url: string; title: LocaleField; subtitle: LocaleField }
interface TextBlock       { type: "text";       content: LocaleField; align: "left" | "center" | "right" }
interface ImageBlock      { type: "image";      image_url: string; caption: LocaleField; size: "full" | "wide" | "medium" }
interface QuoteBlock      { type: "quote";      content: LocaleField; author: string }
interface ImageTextBlock  { type: "image_text"; image_url: string; content: LocaleField; layout: "image_left" | "image_right" }

type Block = HeroBlock | TextBlock | ImageBlock | QuoteBlock | ImageTextBlock;

const BLOCK_LABELS: Record<BlockType, string> = {
  hero: "🖼️ 全版大圖",
  text: "📝 文字段落",
  image: "📷 插圖",
  quote: "💬 引言",
  image_text: "🔲 圖文並排"
};

function emptyLocaleField(): LocaleField {
  return { zh_hant: "", ja: "", en: "" };
}

function createBlock(type: BlockType): Block {
  switch (type) {
    case "hero":       return { type, image_url: "", title: emptyLocaleField(), subtitle: emptyLocaleField() };
    case "text":       return { type, content: emptyLocaleField(), align: "left" };
    case "image":      return { type, image_url: "", caption: emptyLocaleField(), size: "wide" };
    case "quote":      return { type, content: emptyLocaleField(), author: "" };
    case "image_text": return { type, image_url: "", content: emptyLocaleField(), layout: "image_left" };
  }
}

// ── State ──────────────────────────────────────────────────
const loading = ref(true);
const articles = ref<Article[]>([]);

const drawerVisible = ref(false);
const drawerType = ref<"create" | "edit">("create");
const formLoading = ref(false);

const emptyLocale = (): LocaleText => ({ zh_hant: "", ja: "", en: "" });

const formData = ref<any>({
  slug: "",
  brand: "",
  title: emptyLocale(),
  description: emptyLocale(),
  image_url: "",
  gallery_urls: [] as string[],
  sort_order: 0,
  published: false,
  layout_blocks: [] as Block[]
});

const galleryInput = ref("");
const selectedBlockIndex = ref<number | null>(null);
const addBlockType = ref<BlockType>("text");

const selectedBlock = (): Block | null => {
  if (selectedBlockIndex.value === null) return null;
  return formData.value.layout_blocks[selectedBlockIndex.value] ?? null;
};

// ── Data loading ───────────────────────────────────────────
const loadData = async () => {
  try {
    loading.value = true;
    const res = await getArticles();
    const data = (res as any)?.data ?? res;
    articles.value = Array.isArray(data) ? data : (data?.items ?? []);
  } catch (error: any) {
    ElMessage.error(error?.message || "無法載入文章");
  } finally {
    loading.value = false;
  }
};

// ── Drawer open handlers ───────────────────────────────────
const resetFormData = () => ({
  slug: "",
  brand: "",
  title: emptyLocale(),
  description: emptyLocale(),
  image_url: "",
  gallery_urls: [],
  sort_order: 0,
  published: false,
  layout_blocks: [] as Block[]
});

const handleCreate = () => {
  drawerType.value = "create";
  formData.value = resetFormData();
  galleryInput.value = "";
  selectedBlockIndex.value = null;
  drawerVisible.value = true;
};

const normalizeLocale = (loc: any): { zh_hant: string; ja: string; en: string } => ({
  zh_hant: loc?.["zh-Hant"] ?? loc?.["zh_hant"] ?? "",
  ja: loc?.ja ?? "",
  en: loc?.en ?? ""
});

const handleEdit = (row: Article) => {
  drawerType.value = "edit";
  const blocks: Block[] = Array.isArray((row as any).layout_blocks) ? (row as any).layout_blocks : [];
  formData.value = {
    ...row,
    title: normalizeLocale(row.title),
    description: normalizeLocale(row.description),
    gallery_urls: [...(row.gallery_urls ?? [])],
    layout_blocks: blocks
  };
  galleryInput.value = (row.gallery_urls ?? []).join("\n");
  selectedBlockIndex.value = blocks.length > 0 ? 0 : null;
  drawerVisible.value = true;
};

// ── Delete / publish ───────────────────────────────────────
const handleDelete = async (row: Article) => {
  if (!row.article_id) return;
  try {
    await deleteArticle(row.article_id);
    ElMessage.success("刪除成功");
    loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "刪除失敗");
  }
};

const handleTogglePublish = async (row: Article) => {
  try {
    await toggleArticlePublish(row.article_id, !row.published);
    ElMessage.success("狀態切換成功");
    loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "狀態切換失敗");
  }
};

// ── Gallery sync ───────────────────────────────────────────
const syncGallery = () => {
  formData.value.gallery_urls = galleryInput.value
    .split("\n")
    .map((s: string) => s.trim())
    .filter(Boolean);
};

// ── Block editor actions ───────────────────────────────────
const addBlock = () => {
  const block = createBlock(addBlockType.value);
  formData.value.layout_blocks.push(block);
  selectedBlockIndex.value = formData.value.layout_blocks.length - 1;
};

const removeBlock = (index: number) => {
  formData.value.layout_blocks.splice(index, 1);
  if (selectedBlockIndex.value === index) {
    selectedBlockIndex.value = formData.value.layout_blocks.length > 0 ? Math.max(0, index - 1) : null;
  } else if (selectedBlockIndex.value !== null && selectedBlockIndex.value > index) {
    selectedBlockIndex.value--;
  }
};

const moveBlock = (index: number, direction: -1 | 1) => {
  const blocks: Block[] = formData.value.layout_blocks;
  const target = index + direction;
  if (target < 0 || target >= blocks.length) return;
  [blocks[index], blocks[target]] = [blocks[target], blocks[index]];
  selectedBlockIndex.value = target;
};

// ── Submit ─────────────────────────────────────────────────
const submitForm = async () => {
  if (!formData.value.slug || !formData.value.title.zh_hant) {
    ElMessage.warning("請填寫必要欄位（Slug 和繁中標題）");
    return;
  }

  syncGallery();

  try {
    formLoading.value = true;
    const payload = {
      slug: formData.value.slug,
      brand: formData.value.brand,
      title: formData.value.title,
      description: formData.value.description,
      image_url: formData.value.image_url,
      gallery_urls: formData.value.gallery_urls,
      sort_order: formData.value.sort_order,
      published: formData.value.published,
      layout_blocks: formData.value.layout_blocks
    };
    if (drawerType.value === "create") {
      await createArticle(payload);
      ElMessage.success("新增成功");
    } else {
      await updateArticle(formData.value.article_id, payload);
      ElMessage.success("更新成功");
    }
    drawerVisible.value = false;
    loadData();
  } catch (error: any) {
    ElMessage.error(error?.message || "儲存失敗");
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
          <span>雜誌文章管理</span>
          <el-button type="success" @click="handleCreate">新增文章</el-button>
        </div>
      </template>

      <el-table :data="articles" v-loading="loading" style="width: 100%" border>
        <el-table-column prop="slug" label="Slug" width="140" />
        <el-table-column prop="brand" label="品牌" width="120" />
        <el-table-column label="標題(繁中)">
          <template #default="{ row }">
            {{ zhHant(row.title) }}
          </template>
        </el-table-column>
        <el-table-column label="區塊數" width="80">
          <template #default="{ row }">
            {{ Array.isArray(row.layout_blocks) ? row.layout_blocks.length : 0 }}
          </template>
        </el-table-column>
        <el-table-column label="狀態" width="100">
          <template #default="{ row }">
            <el-tag :type="row.published ? 'success' : 'info'" size="small">
              {{ row.published ? "已發布" : "草稿" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="排序" prop="sort_order" width="70" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleTogglePublish(row)">
              {{ row.published ? "設為草稿" : "發布" }}
            </el-button>
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

    <!-- ── Drawer 編輯器 ───────────────────────────────────── -->
    <el-drawer
      v-model="drawerVisible"
      :title="drawerType === 'create' ? '新增文章' : '編輯文章'"
      direction="rtl"
      size="920px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="110px" size="default" class="drawer-form">

        <!-- ── 基本資訊 ─────────────────────────────────────── -->
        <div class="form-section">
          <div class="section-title">基本資訊</div>
          <el-form-item label="Slug" required>
            <el-input
              v-model="formData.slug"
              :disabled="drawerType === 'edit'"
              placeholder="e.g. rolex-submariner-2025"
            />
          </el-form-item>
          <el-form-item label="品牌 Brand">
            <el-input v-model="formData.brand" placeholder="e.g. Rolex" />
          </el-form-item>
          <el-form-item label="排序 Sort">
            <el-input-number v-model="formData.sort_order" :min="0" :step="10" />
          </el-form-item>
          <el-form-item label="狀態">
            <el-switch
              v-model="formData.published"
              active-text="已發布"
              inactive-text="草稿"
            />
          </el-form-item>
        </div>

        <!-- ── 標題與簡介 ───────────────────────────────────── -->
        <div class="form-section">
          <div class="section-title">標題與簡介</div>

          <div class="locale-group">
            <div class="locale-label">繁體中文</div>
            <el-form-item label="標題 (必填)" required>
              <el-input v-model="formData.title.zh_hant" placeholder="繁體中文標題" />
            </el-form-item>
            <el-form-item label="簡介">
              <el-input v-model="formData.description.zh_hant" type="textarea" :rows="2" placeholder="簡短描述" />
            </el-form-item>
          </div>

          <div class="locale-group">
            <div class="locale-label">日本語</div>
            <el-form-item label="タイトル">
              <el-input v-model="formData.title.ja" placeholder="日本語のタイトル" />
            </el-form-item>
            <el-form-item label="概要">
              <el-input v-model="formData.description.ja" type="textarea" :rows="2" placeholder="短い説明" />
            </el-form-item>
          </div>

          <div class="locale-group">
            <div class="locale-label">English</div>
            <el-form-item label="Title">
              <el-input v-model="formData.title.en" placeholder="English Title" />
            </el-form-item>
            <el-form-item label="Description">
              <el-input v-model="formData.description.en" type="textarea" :rows="2" placeholder="Short description" />
            </el-form-item>
          </div>
        </div>

        <!-- ── 主圖與相簿 ──────────────────────────────────── -->
        <div class="form-section">
          <div class="section-title">封面圖片</div>
          <el-form-item label="主圖 URL">
            <el-input v-model="formData.image_url" placeholder="https://..." />
          </el-form-item>
          <div v-if="formData.image_url" class="image-preview">
            <img :src="formData.image_url" alt="主圖預覽" />
          </div>
          <el-form-item label="相簿 Gallery">
            <el-input
              v-model="galleryInput"
              type="textarea"
              :rows="4"
              placeholder="每行一個 URL"
              @blur="syncGallery"
            />
            <div class="field-hint">每行輸入一個圖片 URL，失焦後自動同步</div>
          </el-form-item>
        </div>

        <!-- ── 版面區塊編輯器 ──────────────────────────────── -->
        <div class="form-section">
          <div class="section-title">版面區塊編輯器</div>

          <div class="block-editor">
            <!-- Left: block list -->
            <div class="block-list-panel">
              <div
                v-for="(block, idx) in formData.layout_blocks"
                :key="idx"
                class="block-item"
                :class="{ 'is-active': selectedBlockIndex === idx }"
                @click="selectedBlockIndex = idx"
              >
                <span class="block-label">{{ BLOCK_LABELS[block.type as BlockType] }}</span>
                <div class="block-actions">
                  <el-button
                    link
                    size="small"
                    :disabled="idx === 0"
                    @click.stop="moveBlock(idx, -1)"
                    title="上移"
                  >↑</el-button>
                  <el-button
                    link
                    size="small"
                    :disabled="idx === formData.layout_blocks.length - 1"
                    @click.stop="moveBlock(idx, 1)"
                    title="下移"
                  >↓</el-button>
                  <el-button
                    link
                    type="danger"
                    size="small"
                    @click.stop="removeBlock(idx)"
                    title="刪除"
                  >✕</el-button>
                </div>
              </div>

              <div v-if="formData.layout_blocks.length === 0" class="block-empty">
                尚無區塊，請新增
              </div>

              <div class="block-add-row">
                <el-select v-model="addBlockType" size="small" style="width: 140px">
                  <el-option v-for="(label, key) in BLOCK_LABELS" :key="key" :label="label" :value="key" />
                </el-select>
                <el-button type="primary" size="small" @click="addBlock">+ 新增</el-button>
              </div>
            </div>

            <!-- Right: property panel -->
            <div class="block-prop-panel">
              <div v-if="selectedBlockIndex === null || !selectedBlock()" class="prop-empty">
                點擊左側區塊以編輯屬性
              </div>

              <template v-else-if="selectedBlock()!.type === 'hero'">
                <div class="prop-panel-title">🖼️ 全版大圖</div>
                <el-form-item label="圖片 URL" label-width="90px">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).image_url" placeholder="https://..." size="small" />
                </el-form-item>
                <div class="locale-sub-label">標題 Title</div>
                <div class="locale-row">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).title.zh_hant" placeholder="繁中" size="small" />
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).title.ja" placeholder="日本語" size="small" />
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).title.en" placeholder="English" size="small" />
                </div>
                <div class="locale-sub-label">副標題 Subtitle</div>
                <div class="locale-row">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).subtitle.zh_hant" placeholder="繁中" size="small" />
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).subtitle.ja" placeholder="日本語" size="small" />
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as HeroBlock).subtitle.en" placeholder="English" size="small" />
                </div>
              </template>

              <template v-else-if="selectedBlock()!.type === 'text'">
                <div class="prop-panel-title">📝 文字段落</div>
                <el-form-item label="對齊" label-width="90px">
                  <el-select v-model="(formData.layout_blocks[selectedBlockIndex!] as TextBlock).align" size="small">
                    <el-option label="靠左 Left" value="left" />
                    <el-option label="置中 Center" value="center" />
                    <el-option label="靠右 Right" value="right" />
                  </el-select>
                </el-form-item>
                <div class="locale-sub-label">內容 Content</div>
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as TextBlock).content.zh_hant" type="textarea" :rows="4" placeholder="繁體中文內容" size="small" />
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as TextBlock).content.ja" type="textarea" :rows="4" placeholder="日本語コンテンツ" size="small" style="margin-top:6px" />
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as TextBlock).content.en" type="textarea" :rows="4" placeholder="English content" size="small" style="margin-top:6px" />
              </template>

              <template v-else-if="selectedBlock()!.type === 'image'">
                <div class="prop-panel-title">📷 插圖</div>
                <el-form-item label="圖片 URL" label-width="90px">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageBlock).image_url" placeholder="https://..." size="small" />
                </el-form-item>
                <el-form-item label="尺寸" label-width="90px">
                  <el-select v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageBlock).size" size="small">
                    <el-option label="全版 Full" value="full" />
                    <el-option label="寬幅 Wide" value="wide" />
                    <el-option label="中等 Medium" value="medium" />
                  </el-select>
                </el-form-item>
                <div class="locale-sub-label">說明文字 Caption</div>
                <div class="locale-row">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageBlock).caption.zh_hant" placeholder="繁中" size="small" />
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageBlock).caption.ja" placeholder="日本語" size="small" />
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageBlock).caption.en" placeholder="English" size="small" />
                </div>
              </template>

              <template v-else-if="selectedBlock()!.type === 'quote'">
                <div class="prop-panel-title">💬 引言</div>
                <el-form-item label="作者" label-width="90px">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as QuoteBlock).author" placeholder="Author / 作者" size="small" />
                </el-form-item>
                <div class="locale-sub-label">引言內容 Quote</div>
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as QuoteBlock).content.zh_hant" type="textarea" :rows="3" placeholder="繁體中文引言" size="small" />
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as QuoteBlock).content.ja" type="textarea" :rows="3" placeholder="日本語引用" size="small" style="margin-top:6px" />
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as QuoteBlock).content.en" type="textarea" :rows="3" placeholder="English quote" size="small" style="margin-top:6px" />
              </template>

              <template v-else-if="selectedBlock()!.type === 'image_text'">
                <div class="prop-panel-title">🔲 圖文並排</div>
                <el-form-item label="圖片 URL" label-width="90px">
                  <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageTextBlock).image_url" placeholder="https://..." size="small" />
                </el-form-item>
                <el-form-item label="排版方式" label-width="90px">
                  <el-select v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageTextBlock).layout" size="small">
                    <el-option label="圖左文右 Image Left" value="image_left" />
                    <el-option label="圖右文左 Image Right" value="image_right" />
                  </el-select>
                </el-form-item>
                <div class="locale-sub-label">內容 Content</div>
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageTextBlock).content.zh_hant" type="textarea" :rows="4" placeholder="繁體中文內容" size="small" />
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageTextBlock).content.ja" type="textarea" :rows="4" placeholder="日本語コンテンツ" size="small" style="margin-top:6px" />
                <el-input v-model="(formData.layout_blocks[selectedBlockIndex!] as ImageTextBlock).content.en" type="textarea" :rows="4" placeholder="English content" size="small" style="margin-top:6px" />
              </template>
            </div>
          </div>
        </div>

      </el-form>

      <template #footer>
        <div class="drawer-footer">
          <el-button @click="drawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="formLoading" @click="submitForm">
            確認儲存
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.drawer-form {
  padding: 0 4px 80px;
}

.form-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  padding: 8px 12px;
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  margin-bottom: 16px;
  border-radius: 0 4px 4px 0;
}

.locale-group {
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}

.locale-label {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.image-preview {
  margin: -8px 0 16px 110px;
  padding: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fafafa;
  display: inline-block;
}

.image-preview img {
  max-width: 280px;
  max-height: 180px;
  object-fit: contain;
  display: block;
}

.field-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* ── Block Editor ───────────────────────────────────── */
.block-editor {
  display: flex;
  gap: 12px;
  min-height: 320px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.block-list-panel {
  width: 200px;
  flex-shrink: 0;
  background: #f9fafb;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 4px;
}

.block-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s;
}

.block-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.block-item.is-active {
  background: #ecf5ff;
  border-color: #409eff;
}

.block-label {
  font-size: 12px;
  color: #303133;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.block-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.block-empty {
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
  padding: 16px 8px;
  flex: 1;
}

.block-add-row {
  display: flex;
  gap: 6px;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #e4e7ed;
  margin-top: auto;
}

.block-prop-panel {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.prop-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  font-size: 13px;
  color: #c0c4cc;
}

.prop-panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.locale-sub-label {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
  margin-top: 12px;
}

.locale-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
}
</style>
