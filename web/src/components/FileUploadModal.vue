<template>
  <a-modal
    v-model:open="visible"
    title="添加文件"
    width="800px"
    @cancel="handleCancel"
  >
    <template #footer>
      <a-button key="back" @click="handleCancel">取消</a-button>
      <a-button
        key="submit"
        type="primary"
        @click="chunkData"
        :loading="chunkLoading"
        :disabled="isSubmitDisabled"
      >
        添加到知识库
      </a-button>
    </template>

    <div class="add-files-content">
      <div class="upload-header">
        <div class="source-selector">
          <div class="upload-mode-selector" @click="uploadMode = 'file'" :class="{ active: uploadMode === 'file' }">
            <FileOutlined /> 上传文件
          </div>
          <div class="upload-mode-selector" @click="uploadMode = 'url'" :class="{ active: uploadMode === 'url' }">
            <LinkOutlined /> 输入网址
          </div>
        </div>
        <div class="config-controls">
          <a-button type="dashed" @click="showChunkConfigModal" v-if="!isGraphBased && processingStrategy === 'text'">
            <SettingOutlined /> 分块参数 ({{ chunkParams.chunk_size }}/{{ chunkParams.chunk_overlap }})
          </a-button>
        </div>
      </div>

      <div class="processing-strategy" v-if="uploadMode === 'file'">
        <a-form layout="horizontal">
          <a-form-item label="处理策略" name="processing_strategy">
            <a-radio-group v-model:value="processingStrategy" button-style="solid">
              <a-radio-button value="text">文本嵌入</a-radio-button>
              <a-radio-button value="multimodal">多模态嵌入</a-radio-button>
            </a-radio-group>
            <div class="param-description">
              <span v-if="processingStrategy === 'text'">将文件解析为文本后进行嵌入（支持文档、图片OCR识别、PDF等格式）{{ textSupportedTypesHint }}</span>
              <span v-else>支持图片、视频、音频等多模态内容的嵌入处理</span>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <div class="ocr-config" v-if="processingStrategy === 'text'">
        <a-form layout="horizontal">
          <a-form-item label="使用OCR" name="enable_ocr">
            <div class="ocr-controls">
              <a-select
                v-model:value="chunkParams.enable_ocr"
                :options="enableOcrOptions"
                style="width: 220px; margin-right: 12px;"
                :disabled="ocrHealthChecking"
              />
              <a-button
                size="small"
                type="dashed"
                @click="checkOcrHealth"
                :loading="ocrHealthChecking"
                :icon="h(CheckCircleOutlined)"
              >
                检查OCR服务
              </a-button>
            </div>
            <div class="param-description">
              <div v-if="chunkParams.enable_ocr !== 'disable' && selectedOcrStatus && selectedOcrStatus !== 'healthy'" class="ocr-warning">
                ⚠️ {{ selectedOcrMessage }}
              </div>
              <div v-else-if="chunkParams.enable_ocr !== 'disable' && selectedOcrStatus === 'healthy'" class="ocr-healthy">
                ✅ {{ selectedOcrMessage }}
              </div>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <div class="qa-split-config" v-if="isQaSplitSupported && processingStrategy === 'text'">
        <a-form layout="horizontal">
          <a-form-item label="QA分割模式" name="use_qa_split">
            <div class="toggle-controls">
              <a-switch
                v-model:checked="chunkParams.use_qa_split"
                style="margin-right: 12px;"
              />
              <span class="param-description">
                {{ chunkParams.use_qa_split ? '启用QA分割（忽略chunk大小设置）' : '使用普通分割模式' }}
              </span>
            </div>
          </a-form-item>
          <a-form-item
            v-if="chunkParams.use_qa_split"
            label="QA分隔符"
            name="qa_separator"
          >
            <a-input
              v-model:value="chunkParams.qa_separator"
              placeholder="输入QA分隔符"
              style="width: 200px; margin-right: 12px;"
            />
            <span class="param-description">
              用于分割不同QA对的分隔符，默认为3个换行符
            </span>
          </a-form-item>
        </a-form>
      </div>

      <div class="multimodal-mode-config" v-if="processingStrategy === 'multimodal' && uploadMode === 'file'">
        <a-form layout="horizontal">
          <a-form-item label="处理模式" name="multimodal_mode">
            <a-radio-group v-model:value="multimodalMode" button-style="solid">
              <a-radio-button value="single">单个文件</a-radio-button>
              <a-radio-button value="batch">批量JSON</a-radio-button>
            </a-radio-group>
            <div class="param-description">
              <span v-if="multimodalMode === 'single'">上传单个图片、视频或音频文件进行处理</span>
              <span v-else>通过JSON文件批量处理多个多模态文件</span>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <div class="upload" v-if="uploadMode === 'file'">
        <a-upload-dragger
          class="upload-dragger"
          v-model:fileList="fileList"
          name="file"
          :multiple="processingStrategy === 'text' || multimodalMode === 'single'"
          :disabled="chunkLoading"
          :accept="currentAcceptedFileTypes"
          :before-upload="beforeUpload"
          :action="uploadAction"
          :headers="getAuthHeaders()"
          @change="handleFileUpload"
          @drop="handleDrop"
        >
          <p class="ant-upload-text">点击或者把文件拖拽到这里上传</p>
          <p class="ant-upload-hint">
            支持的文件类型：{{ currentUploadHint }}
          </p>
          <p class="ant-upload-hint size-limit-hint">
            {{ currentSizeLimitHint }}
          </p>
        </a-upload-dragger>
      </div>

      <div class="url-input" v-else>
        <a-form layout="vertical">
          <a-form-item label="网页链接 (每行一个URL)">
            <a-textarea
              v-model:value="urlList"
              placeholder="请输入网页链接，每行一个"
              :rows="6"
              :disabled="chunkLoading"
            />
          </a-form-item>
        </a-form>
        <p class="url-hint">
          支持添加网页内容，系统会自动抓取网页文本并进行分块。请确保URL格式正确且可以公开访问。
        </p>
      </div>
      
      <div class="upload-errors" v-if="uploadErrors.length > 0">
        <a-alert
          v-for="(error, index) in uploadErrors"
          :key="index"
          :type="error.type"
          :message="error.message"
          show-icon
          closable
          @close="removeError(index)"
          style="margin-bottom: 8px;"
        />
      </div>
    </div>
  </a-modal>

  <a-modal v-model:open="chunkConfigModalVisible" title="分块参数配置" width="500px">
    <template #footer>
      <a-button key="back" @click="chunkConfigModalVisible = false">取消</a-button>
      <a-button key="submit" type="primary" @click="handleChunkConfigSubmit">确定</a-button>
    </template>
    <div class="chunk-config-content">
      <div class="params-info">
        <p>调整分块参数可以控制文本的切分方式，影响检索质量和文档加载效率。</p>
      </div>
      <a-form
        :model="tempChunkParams"
        name="chunkConfig"
        autocomplete="off"
        layout="vertical"
      >
        <a-form-item label="Chunk Size" name="chunk_size">
          <a-input-number v-model:value="tempChunkParams.chunk_size" :min="100" :max="10000" style="width: 100%;" />
          <p class="param-description">每个文本片段的最大字符数</p>
        </a-form-item>
        <a-form-item label="Chunk Overlap" name="chunk_overlap">
          <a-input-number v-model:value="tempChunkParams.chunk_overlap" :min="0" :max="1000" style="width: 100%;" />
          <p class="param-description">相邻文本片段间的重叠字符数</p>
        </a-form-item>
        <a-form-item v-if="isQaSplitSupported" label="QA分割模式" name="use_qa_split">
          <a-switch v-model:checked="tempChunkParams.use_qa_split" />
          <p class="param-description">启用后将按QA对分割，忽略上述chunk大小设置</p>
        </a-form-item>
        <a-form-item v-if="tempChunkParams.use_qa_split && isQaSplitSupported" label="QA分隔符" name="qa_separator">
          <a-input v-model:value="tempChunkParams.qa_separator" placeholder="输入QA分隔符" style="width: 100%;" />
          <p class="param-description">用于分割不同QA对的分隔符</p>
        </a-form-item>
      </a-form>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { message, Upload } from 'ant-design-vue';
import { useUserStore } from '@/stores/user';
import { useDatabaseStore } from '@/stores/database';
import { ocrApi } from '@/apis/system_api';
import { fileApi, multimodalApi } from '@/apis/knowledge_api';
import {
  FileOutlined,
  LinkOutlined,
  SettingOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons-vue';
import { h } from 'vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
});

const emit = defineEmits(['update:visible']);

const store = useDatabaseStore();

const TEXT_EMBED_SUPPORTED_TYPES = [
  '.txt', '.md', '.doc', '.docx', '.pdf', '.html', '.htm', '.json', '.csv', '.xls', '.xlsx',
  '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'
];

const MULTIMODAL_SUPPORTED_TYPES = {
  image: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.svg'],
  video: ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
  audio: ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a']
};

const DEFAULT_SUPPORTED_TYPES = TEXT_EMBED_SUPPORTED_TYPES;

const normalizeExtensions = (extensions) => {
  if (!Array.isArray(extensions)) {
    return [];
  }
  const normalized = extensions
    .map((ext) => (typeof ext === 'string' ? ext.trim().toLowerCase() : ''))
    .filter((ext) => ext.length > 0)
    .map((ext) => (ext.startsWith('.') ? ext : `.${ext}`));
  return Array.from(new Set(normalized)).sort();
};

const supportedFileTypes = ref(normalizeExtensions(DEFAULT_SUPPORTED_TYPES));
const fileCategories = ref({});

const applySupportedFileTypes = (data) => {
  if (data?.file_types) {
    supportedFileTypes.value = normalizeExtensions(data.file_types);
  }
  if (data?.categories) {
    fileCategories.value = data.categories;
  }
};

const loadSupportedFileTypes = async () => {
  try {
    const data = await fileApi.getSupportedFileTypes();
    applySupportedFileTypes(data);
  } catch (error) {
    console.error('获取支持的文件类型失败:', error);
    message.warning('获取支持的文件类型失败，已使用默认配置');
    applySupportedFileTypes({ file_types: DEFAULT_SUPPORTED_TYPES });
  }
};

onMounted(() => {
  loadSupportedFileTypes();
});

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const databaseId = computed(() => store.databaseId);
const kbType = computed(() => store.database.kb_type);
const chunkLoading = computed(() => store.state.chunkLoading);

const uploadMode = ref('file');
const processingStrategy = ref('text');
const multimodalMode = ref('single');
const uploadErrors = ref([]);

const fileList = ref([]);
const urlList = ref('');

const ocrHealthStatus = ref({
  rapid_ocr: { status: 'unknown', message: '' },
  mineru_ocr: { status: 'unknown', message: '' },
  paddlex_ocr: { status: 'unknown', message: '' }
});

const ocrHealthChecking = ref(false);

const chunkParams = ref({
  chunk_size: 1000,
  chunk_overlap: 200,
  enable_ocr: 'disable',
  use_qa_split: false,
  qa_separator: '\n\n\n',
});

const chunkConfigModalVisible = ref(false);

const tempChunkParams = ref({
  chunk_size: 1000,
  chunk_overlap: 200,
  use_qa_split: false,
  qa_separator: '\n\n\n',
});

const isQaSplitSupported = computed(() => {
  const type = kbType.value?.toLowerCase();
  return type === 'chroma' || type === 'milvus';
});

const isGraphBased = computed(() => {
  const type = kbType.value?.toLowerCase();
  return type === 'lightrag';
});

const uploadAction = computed(() => {
  return `/api/knowledge/files/upload?db_id=${databaseId.value}&validate=true`;
});

const currentAcceptedFileTypes = computed(() => {
  if (processingStrategy.value === 'text') {
    return TEXT_EMBED_SUPPORTED_TYPES.join(',');
  } else if (processingStrategy.value === 'multimodal') {
    if (multimodalMode.value === 'single') {
      const allTypes = [
        ...MULTIMODAL_SUPPORTED_TYPES.image,
        ...MULTIMODAL_SUPPORTED_TYPES.video,
        ...MULTIMODAL_SUPPORTED_TYPES.audio
      ];
      return allTypes.join(',');
    } else {
      return '.json';
    }
  }
  return supportedFileTypes.value.join(',');
});

const currentUploadHint = computed(() => {
  if (processingStrategy.value === 'text') {
    return TEXT_EMBED_SUPPORTED_TYPES.join(', ');
  } else if (processingStrategy.value === 'multimodal') {
    if (multimodalMode.value === 'single') {
      return '图片: ' + MULTIMODAL_SUPPORTED_TYPES.image.join(', ') + 
             '; 视频: ' + MULTIMODAL_SUPPORTED_TYPES.video.slice(0, 3).join(', ') + '...' +
             '; 音频: ' + MULTIMODAL_SUPPORTED_TYPES.audio.slice(0, 3).join(', ') + '...';
    } else {
      return 'JSON文件（格式: [{"url": "文件URL", "description": "描述信息"}, ...]）';
    }
  }
  return supportedFileTypes.value.join(', ');
});

const currentSizeLimitHint = computed(() => {
  if (processingStrategy.value === 'text') {
    return '文件大小限制：文本/图片 100MB';
  } else if (processingStrategy.value === 'multimodal') {
    return '文件大小限制：图片 50MB / 视频 500MB / 音频 100MB';
  }
  return '文件大小限制：100MB';
});

const textSupportedTypesHint = computed(() => {
  return '支持: ' + TEXT_EMBED_SUPPORTED_TYPES.slice(0, 8).join(', ') + '... 等格式';
});

const enableOcrOptions = computed(() => [
  {
    value: 'disable',
    label: '不启用',
    title: '不启用'
  },
  {
    value: 'onnx_rapid_ocr',
    label: getRapidOcrLabel(),
    title: 'ONNX with RapidOCR',
    disabled: ocrHealthStatus.value.rapid_ocr.status === 'unavailable' || ocrHealthStatus.value.rapid_ocr.status === 'error'
  },
  {
    value: 'mineru_ocr',
    label: getMinerULabel(),
    title: 'MinerU OCR',
    disabled: ocrHealthStatus.value.mineru_ocr.status === 'unavailable' || ocrHealthStatus.value.mineru_ocr.status === 'error'
  },
  {
    value: 'paddlex_ocr',
    label: getPaddleXLabel(),
    title: 'PaddleX OCR',
    disabled: ocrHealthStatus.value.paddlex_ocr.status === 'unavailable' || ocrHealthStatus.value.paddlex_ocr.status === 'error'
  },
]);

const selectedOcrStatus = computed(() => {
  switch (chunkParams.value.enable_ocr) {
    case 'onnx_rapid_ocr':
      return ocrHealthStatus.value.rapid_ocr.status;
    case 'mineru_ocr':
      return ocrHealthStatus.value.mineru_ocr.status;
    case 'paddlex_ocr':
      return ocrHealthStatus.value.paddlex_ocr.status;
    default:
      return null;
  }
});

const selectedOcrMessage = computed(() => {
  switch (chunkParams.value.enable_ocr) {
    case 'onnx_rapid_ocr':
      return ocrHealthStatus.value.rapid_ocr.message;
    case 'mineru_ocr':
      return ocrHealthStatus.value.mineru_ocr.message;
    case 'paddlex_ocr':
      return ocrHealthStatus.value.paddlex_ocr.message;
    default:
      return '';
  }
});

const getRapidOcrLabel = () => {
  const status = ocrHealthStatus.value.rapid_ocr.status;
  const statusIcons = {
    'healthy': '✅',
    'unavailable': '❌',
    'error': '⚠️',
    'unknown': '❓'
  };
  return `${statusIcons[status] || '❓'} RapidOCR (ONNX)`;
};

const getMinerULabel = () => {
  const status = ocrHealthStatus.value.mineru_ocr.status;
  const statusIcons = {
    'healthy': '✅',
    'unavailable': '❌',
    'unhealthy': '⚠️',
    'timeout': '⏰',
    'error': '⚠️',
    'unknown': '❓'
  };
  return `${statusIcons[status] || '❓'} MinerU OCR`;
};

const getPaddleXLabel = () => {
  const status = ocrHealthStatus.value.paddlex_ocr.status;
  const statusIcons = {
    'healthy': '✅',
    'unavailable': '❌',
    'unhealthy': '⚠️',
    'timeout': '⏰',
    'error': '⚠️',
    'unknown': '❓'
  };
  return `${statusIcons[status] || '❓'} PaddleX OCR`;
};

const validateOcrService = () => {
  if (chunkParams.value.enable_ocr === 'disable') {
    return true;
  }

  const status = selectedOcrStatus.value;
  if (status === 'unavailable' || status === 'error') {
    const ocrMessage = selectedOcrMessage.value;
    message.error(`OCR服务不可用: ${ocrMessage}`);
    return false;
  }

  return true;
};

const handleCancel = () => {
  emit('update:visible', false);
};

const addError = (type, errorMessage) => {
  uploadErrors.value.push({ type, message: errorMessage });
};

const removeError = (index) => {
  uploadErrors.value.splice(index, 1);
};

const validateMultimodalJsonFormat = (jsonData) => {
  if (!Array.isArray(jsonData)) {
    return { valid: false, error: 'JSON格式错误：根元素必须是数组' };
  }
  
  for (let i = 0; i < jsonData.length; i++) {
    const item = jsonData[i];
    if (typeof item !== 'object' || item === null) {
      return { valid: false, error: `第 ${i + 1} 项不是有效的对象` };
    }
    if (!item.url || typeof item.url !== 'string') {
      return { valid: false, error: `第 ${i + 1} 项缺少有效的 "url" 字段` };
    }
    if (!item.description || typeof item.description !== 'string') {
      return { valid: false, error: `第 ${i + 1} 项缺少有效的 "description" 字段` };
    }
    if (!item.url.startsWith('http://') && !item.url.startsWith('https://')) {
      return { valid: false, error: `第 ${i + 1} 项的 "url" 必须以 http:// 或 https:// 开头` };
    }
  }
  
  return { valid: true };
};

const beforeUpload = (file) => {
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  
  if (processingStrategy.value === 'text') {
    if (!TEXT_EMBED_SUPPORTED_TYPES.includes(ext)) {
      const errorMsg = `文本嵌入不支持该文件类型: ${file.name}。支持的类型: ${TEXT_EMBED_SUPPORTED_TYPES.slice(0, 5).join(', ')}...`;
      message.error(errorMsg);
      addError('error', errorMsg);
      return Upload.LIST_IGNORE;
    }
  } else if (processingStrategy.value === 'multimodal') {
    if (multimodalMode.value === 'single') {
      const allMultimodalTypes = [
        ...MULTIMODAL_SUPPORTED_TYPES.image,
        ...MULTIMODAL_SUPPORTED_TYPES.video,
        ...MULTIMODAL_SUPPORTED_TYPES.audio
      ];
      if (!allMultimodalTypes.includes(ext)) {
        const errorMsg = `多模态嵌入不支持该文件类型: ${file.name}`;
        message.error(errorMsg);
        addError('error', errorMsg);
        return Upload.LIST_IGNORE;
      }
    } else {
      if (ext !== '.json') {
        const errorMsg = `批量模式仅支持JSON文件，当前文件: ${file.name}`;
        message.error(errorMsg);
        addError('error', errorMsg);
        return Upload.LIST_IGNORE;
      }
    }
  }
  
  const sizeLimits = {
    text: 100 * 1024 * 1024,
    image: 50 * 1024 * 1024,
    video: 500 * 1024 * 1024,
    audio: 100 * 1024 * 1024,
    default: 100 * 1024 * 1024,
  };
  
  let maxSize = sizeLimits.default;
  if (processingStrategy.value === 'text') {
    maxSize = sizeLimits.text;
  } else if (processingStrategy.value === 'multimodal') {
    if (multimodalMode.value === 'single') {
      const allMultimodalTypes = [
        ...MULTIMODAL_SUPPORTED_TYPES.image,
        ...MULTIMODAL_SUPPORTED_TYPES.video,
        ...MULTIMODAL_SUPPORTED_TYPES.audio
      ];
      if (MULTIMODAL_SUPPORTED_TYPES.image.includes(ext)) {
        maxSize = sizeLimits.image;
      } else if (MULTIMODAL_SUPPORTED_TYPES.video.includes(ext)) {
        maxSize = sizeLimits.video;
      } else if (MULTIMODAL_SUPPORTED_TYPES.audio.includes(ext)) {
        maxSize = sizeLimits.audio;
      }
    } else {
      maxSize = 10 * 1024 * 1024;
    }
  }
  
  if (file.size > maxSize) {
    const errorMsg = `文件过大: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)，最大限制 ${(maxSize / 1024 / 1024).toFixed(0)} MB`;
    message.error(errorMsg);
    addError('error', errorMsg);
    return Upload.LIST_IGNORE;
  }
  
  return true;
};

const handleFileUpload = (info) => {
  if (info?.file?.status === 'error') {
    const response = info.file?.response;
    let errorMessage = `文件上传失败: ${info.file.name}`;
    
    if (response?.detail) {
      if (typeof response.detail === 'object') {
        errorMessage = response.detail.message || errorMessage;
        
        if (response.detail.error_code === 'FILE_TOO_LARGE') {
          errorMessage = `文件过大: 当前 ${(response.detail.file_size / 1024 / 1024).toFixed(2)} MB，最大限制 ${(response.detail.max_size / 1024 / 1024).toFixed(0)} MB`;
        } else if (response.detail.error_code === 'UNSUPPORTED_FILE_TYPE') {
          errorMessage = `不支持的文件类型: ${response.detail.file_ext}。支持的类型: ${response.detail.supported_types?.slice(0, 10).join(', ')}...`;
        } else if (response.detail.error_code === 'FILE_CORRUPTED') {
          errorMessage = `文件损坏或不完整: ${info.file.name}`;
        } else if (response.detail.error_code === 'FILE_SECURITY_RISK') {
          errorMessage = `检测到安全风险: ${info.file.name}`;
        }
      } else {
        errorMessage = response.detail;
      }
    }
    
    message.error(errorMessage);
    addError('error', errorMessage);
  }
  fileList.value = info?.fileList ?? [];
};

const handleDrop = () => {};

const showChunkConfigModal = () => {
  tempChunkParams.value = {
    chunk_size: chunkParams.value.chunk_size,
    chunk_overlap: chunkParams.value.chunk_overlap,
    use_qa_split: isQaSplitSupported.value ? chunkParams.value.use_qa_split : false,
    qa_separator: chunkParams.value.qa_separator,
  };
  chunkConfigModalVisible.value = true;
};

const handleChunkConfigSubmit = () => {
  chunkParams.value.chunk_size = tempChunkParams.value.chunk_size;
  chunkParams.value.chunk_overlap = tempChunkParams.value.chunk_overlap;
  if (isQaSplitSupported.value) {
    chunkParams.value.use_qa_split = tempChunkParams.value.use_qa_split;
    chunkParams.value.qa_separator = tempChunkParams.value.qa_separator;
  } else {
    chunkParams.value.use_qa_split = false;
  }
  chunkConfigModalVisible.value = false;
  message.success('分块参数配置已更新');
};

const checkOcrHealth = async () => {
  if (ocrHealthChecking.value) return;

  ocrHealthChecking.value = true;
  try {
    const healthData = await ocrApi.getHealth();
    ocrHealthStatus.value = healthData.services;
  } catch (error) {
    console.error('OCR健康检查失败:', error);
    message.error('OCR服务健康检查失败');
  } finally {
    ocrHealthChecking.value = false;
  }
};

const getAuthHeaders = () => {
  const userStore = useUserStore();
  return userStore.getAuthHeaders();
};

const isSubmitDisabled = computed(() => {
  if (uploadMode.value === 'url') {
    return !urlList.value.trim();
  }
  if (fileList.value.length === 0) {
    return true;
  }
  const hasValidFiles = fileList.value.some(file => file.status === 'done');
  return !hasValidFiles;
});

watch(processingStrategy, () => {
  fileList.value = [];
  uploadErrors.value = [];
});

watch(multimodalMode, () => {
  fileList.value = [];
  uploadErrors.value = [];
});

const chunkData = async () => {
  if (processingStrategy.value === 'text' && !validateOcrService()) {
    return;
  }

  uploadErrors.value = [];

  let success = false;
  if (uploadMode.value === 'file') {
    const files = fileList.value.filter(file => file.status === 'done').map(file => file.response?.file_path);
    const validFiles = files.filter(file => file);
    if (validFiles.length === 0) {
      const errorMsg = '请先上传文件';
      message.error(errorMsg);
      addError('error', errorMsg);
      return;
    }
    
    if (processingStrategy.value === 'text') {
      success = await store.addFiles({ 
        items: validFiles, 
        contentType: 'file', 
        params: chunkParams.value 
      });
    } else if (processingStrategy.value === 'multimodal') {
      if (multimodalMode.value === 'single') {
        try {
          const multimodalParams = {
            ...chunkParams.value,
            mode: 'single',
          };
          await multimodalApi.addMultimodalContent(databaseId.value, validFiles, multimodalParams);
          success = true;
        } catch (error) {
          console.error('多模态文件处理失败:', error);
          addError('error', `多模态文件处理失败: ${error.message || '未知错误'}`);
          return;
        }
      } else {
        try {
          const jsonFile = validFiles[0];
          const jsonContent = await fetch(jsonFile).then(r => r.text());
          const jsonData = JSON.parse(jsonContent);
          
          const validation = validateMultimodalJsonFormat(jsonData);
          if (!validation.valid) {
            message.error(validation.error);
            addError('error', validation.error);
            return;
          }
          
          const multimodalParams = {
            ...chunkParams.value,
            mode: 'batch',
            items: jsonData,
          };
          await multimodalApi.addMultimodalContent(databaseId.value, [], multimodalParams);
          success = true;
        } catch (error) {
          console.error('批量多模态处理失败:', error);
          addError('error', `批量处理失败: ${error.message || '未知错误'}`);
          return;
        }
      }
    }
    
  } else if (uploadMode.value === 'url') {
    const urls = urlList.value.split('\n')
      .map(url => url.trim())
      .filter(url => url.length > 0 && (url.startsWith('http://') || url.startsWith('https://')));

    if (urls.length === 0) {
      const errorMsg = '请输入有效的网页链接（必须以http://或https://开头）';
      message.error(errorMsg);
      addError('error', errorMsg);
      return;
    }

    success = await store.addFiles({ items: urls, contentType: 'url', params: chunkParams.value });
  }

  if (success) {
    emit('update:visible', false);
    fileList.value = [];
    urlList.value = '';
    uploadErrors.value = [];
  }
};

</script>

<style lang="less" scoped>
.add-files-content {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  height: 100%;

  .ant-form-item {
    margin: 0;
  }
}

.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.source-selector {
  display: flex;
  gap: 12px;
}

.upload-mode-selector {
  padding: 8px 16px;
  border: 1px solid var(--gray-300);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-mode-selector:hover {
  border-color: var(--main-color);
}

.upload-mode-selector.active {
  border-color: var(--main-color);
  background-color: var(--main-30);
  color: var(--main-color);
}

.config-controls {
  display: flex;
  align-items: center;
}

.processing-strategy,
.ocr-config,
.qa-split-config,
.multimodal-mode-config {
  margin-bottom: 20px;
  padding: 16px;
  background-color: var(--gray-50);
  border-radius: 6px;
}

.toggle-controls {
  display: flex;
  align-items: center;
}

.param-description {
  font-size: 12px;
  color: var(--gray-600);
  margin-top: 4px;
}

.ocr-warning {
  color: #faad14;
}

.ocr-healthy {
  color: #52c41a;
}

.upload-dragger {
  margin-bottom: 16px;
}

.size-limit-hint {
  color: var(--gray-500);
  font-size: 12px;
}

.url-hint {
  font-size: 12px;
  color: var(--gray-600);
  margin-top: 8px;
}

.upload-errors {
  margin-top: 16px;
}

.chunk-config-content .params-info {
  margin-bottom: 16px;
}
</style>
