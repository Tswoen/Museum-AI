<template>
  <div class="input-box" :class="[customClasses, { 'single-line': isSingleLine }]" @click="focusInput">
    <div class="expand-options" v-if="hasOptionsLeft">
      <a-popover
        v-model:open="optionsExpanded"
        placement="bottomLeft"
        trigger="click"
      >
        <template #content>
          <div class="popover-options">
            <slot name="options-left">
              <div class="no-options">没有配置 options</div>
            </slot>
          </div>
        </template>
        <a-button
          type="text"
          size="small"
          class="expand-btn"
        >
          <template #icon>
            <PlusOutlined :class="{ 'rotated': optionsExpanded }" />
          </template>
        </a-button>
      </a-popover>
    </div>

    <!-- 图片预览区域 -->
    <div class="image-previews" v-if="imagePreviews.length > 0">
      <div class="preview-item" v-for="(image, index) in imagePreviews" :key="index">
        <img :src="image.url" :alt="image.name" class="preview-image" />
        <div class="preview-overlay" v-if="image.isUploading">
          <a-spin size="small" />
          <span class="upload-text">上传中...</span>
        </div>
        <div class="preview-actions">
          <a-button type="text" size="small" @click="removeImage(index)" class="remove-btn">
            <CloseOutlined />
          </a-button>
        </div>
      </div>
    </div>

    <div class="input-area">
      <textarea
        ref="inputRef"
        class="user-input"
        :value="inputValue"
        @keydown="handleKeyPress"
        @input="handleInput"
        @focus="focusInput"
        :placeholder="placeholder"
        :disabled="disabled"
      />

      <!-- 图片上传按钮 -->
      <div class="image-upload-container">
        <a-tooltip title="上传图片">
          <a-button
            type="text"
            size="small"
            class="image-upload-btn"
            @click="triggerImageUpload"
            :disabled="disabled"
          >
            <template #icon>
              <PictureOutlined />
            </template>
          </a-button>
        </a-tooltip>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          multiple
          @change="handleImageUpload"
          style="display: none"
        />
      </div>
    </div>

    <div class="send-button-container">
      <a-tooltip :title="isLoading ? '停止回答' : ''">
        <a-button
          @click="handleSendOrStop"
          :disabled="sendButtonDisabled"
          type="link"
          class="send-button"
        >
          <template #icon>
            <component :is="getIcon" class="send-btn"/>
          </template>
        </a-button>
      </a-tooltip>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, toRefs, onMounted, nextTick, watch, onBeforeUnmount } from 'vue';
import {
  SendOutlined,
  ArrowUpOutlined,
  LoadingOutlined,
  PauseOutlined,
  PlusOutlined,
  PictureOutlined,
  CloseOutlined
} from '@ant-design/icons-vue';

const inputRef = ref(null);
const fileInputRef = ref(null);
const isSingleLine = ref(true);
const optionsExpanded = ref(false);
const hasOptionsLeft = ref(false);
const singleLineHeight = ref(0);
const debounceTimer = ref(null);
const imagePreviews = ref([]); // 存储图片预览数据

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '输入问题...'
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  sendButtonDisabled: {
    type: Boolean,
    default: false
  },
  autoSize: {
    type: Object,
    default: () => ({ minRows: 2, maxRows: 6 })
  },
  sendIcon: {
    type: String,
    default: 'ArrowUpOutlined'
  },
  customClasses: {
    type: Object,
    default: () => ({})
  },
  maxImages: {
    type: Number,
    default: 5 // 最大图片数量
  },
  maxImageSize: {
    type: Number,
    default: 5 * 1024 * 1024 // 5MB 默认最大图片大小
  }
});

const emit = defineEmits([
  'update:modelValue', 
  'send', 
  'keydown', 
  'images-change', // 新增：图片变化事件
  'image-upload',  // 新增：图片上传事件
  'image-remove'   // 新增：图片删除事件
]);

// 图标映射
const iconComponents = {
  'SendOutlined': SendOutlined,
  'ArrowUpOutlined': ArrowUpOutlined,
  'PauseOutlined': PauseOutlined
};

// 根据传入的图标名动态获取组件
const getIcon = computed(() => {
  if (props.isLoading) {
    return PauseOutlined;
  }
  return iconComponents[props.sendIcon] || ArrowUpOutlined;
});

// 创建本地引用以进行双向绑定
const inputValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

// 触发图片上传
const triggerImageUpload = () => {
  if (fileInputRef.value) {
    fileInputRef.value.click();
  }
};

// 上传图片到后端
const uploadImageToServer = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    // 获取正确的token（存储在user_token中）
    const token = localStorage.getItem('user_token');
    console.log('token:', token);
    if (!token) {
      throw new Error('请先登录');
    }

    const response = await fetch('/api/chat/upload-image', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '图片上传失败');
    }

    const data = await response.json();
    return data.image_url; // 返回后端存储的图片完整地址
  } catch (error) {
    console.error('图片上传错误:', error);
    throw error;
  }
};

// 处理图片上传
const handleImageUpload = async (event) => {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  // 检查图片数量限制
  if (imagePreviews.value.length + files.length > props.maxImages) {
    console.warn(`最多只能上传 ${props.maxImages} 张图片`);
    return;
  }

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    
    // 检查文件类型
    if (!file.type.startsWith('image/')) {
      console.warn('只能上传图片文件');
      continue;
    }

    // 检查文件大小
    if (file.size > props.maxImageSize) {
      console.warn(`图片大小不能超过 ${props.maxImageSize / 1024 / 1024}MB`);
      continue;
    }

    // 先创建本地预览
    const reader = new FileReader();
    reader.onload = (e) => {
      const tempImageData = {
        file: file,
        url: e.target.result, // 临时预览URL
        name: file.name,
        size: file.size,
        type: file.type,
        isUploading: true,
        serverUrl: null // 后端URL，上传成功后更新
      };
      
      imagePreviews.value.push(tempImageData);
      
      // 触发图片变化事件
      emit('images-change', imagePreviews.value);
      emit('image-upload', tempImageData);

      // 上传到后端
      uploadImageToServer(file).then(serverUrl => {
        // 更新图片数据，将临时预览URL替换为后端URL
        const index = imagePreviews.value.findIndex(img => img.file === file);
        if (index !== -1) {
          imagePreviews.value[index] = {
            ...imagePreviews.value[index],
            url: serverUrl, // 使用后端返回的完整地址
            serverUrl: serverUrl,
            isUploading: false
          };
          
          // 触发更新事件
          emit('images-change', imagePreviews.value);
        }
      }).catch(error => {
        console.error('图片上传失败:', error);
        // 上传失败时移除预览
        const index = imagePreviews.value.findIndex(img => img.file === file);
        if (index !== -1) {
          imagePreviews.value.splice(index, 1);
          emit('images-change', imagePreviews.value);
        }
      });
    };
    reader.readAsDataURL(file);
  }

  // 清空文件输入，允许重复选择相同文件
  event.target.value = '';
};

// 删除图片
const removeImage = (index) => {
  const removedImage = imagePreviews.value[index];
  imagePreviews.value.splice(index, 1);
  
  // 触发图片变化事件
  emit('images-change', imagePreviews.value);
  emit('image-remove', removedImage);
};

// 获取所有图片文件
const getImageFiles = () => {
  return imagePreviews.value.map(item => item.file);
};

// 清空所有图片
const clearImages = () => {
  imagePreviews.value = [];
  emit('images-change', []);
};

// 处理键盘事件
const handleKeyPress = (e) => {
    const sendData = {
      text: inputValue.value,
      images: imagePreviews.value
    };
  emit('keydown', e, sendData);
};

// 处理输入事件
const handleInput = (e) => {
  const value = e.target.value;
  emit('update:modelValue', value);
};

// 处理发送按钮点击
const handleSendOrStop = () => {
  // 发送时包含文本和图片数据
  const sendData = {
    text: inputValue.value,
    images: imagePreviews.value
  };
  emit('send', sendData);
};

// 检查行数
const checkLineCount = () => {
  if (!inputRef.value || singleLineHeight.value === 0) {
    return;
  }
  const textarea = inputRef.value;
  const content = inputValue.value;

  const hasNewlines = content.includes('\n');
  let contentExceedsWidth = false;
  
  if (!hasNewlines && content.trim() && singleLineWidth.value > 0) {
    const measureDiv = document.createElement('div');
    measureDiv.style.cssText = `
      position: absolute;
      visibility: hidden;
      white-space: nowrap;
      font-family: ${getComputedStyle(textarea).fontFamily};
      font-size: ${getComputedStyle(textarea).fontSize};
      line-height: ${getComputedStyle(textarea).lineHeight};
      padding: 0;
      border: none;
      width: ${singleLineWidth.value}px;
    `;
    measureDiv.textContent = content;
    document.body.appendChild(measureDiv);
    contentExceedsWidth = measureDiv.scrollWidth > measureDiv.clientWidth;
    document.body.removeChild(measureDiv);
  }

  const shouldBeMultiLine = hasNewlines || contentExceedsWidth;
  isSingleLine.value = !shouldBeMultiLine;

  if (shouldBeMultiLine) {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(textarea.scrollHeight, singleLineHeight.value)}px`;
  } else {
    textarea.style.height = '';
  }
};

// 聚焦输入框
const focusInput = () => {
  if (inputRef.value && !props.disabled) {
    inputRef.value.focus();
  }
};

// 检查是否有左侧选项
const checkOptionsLeft = () => {
  hasOptionsLeft.value = true;
};

// 监听输入值变化
watch(inputValue, () => {
  nextTick(() => {
    checkLineCount();
  });
});

// 用于存储固定的单行宽度基准
const singleLineWidth = ref(0);

onMounted(() => {
  checkOptionsLeft();
  nextTick(() => {
    if (inputRef.value) {
      singleLineHeight.value = inputRef.value.clientHeight;
      singleLineWidth.value = inputRef.value.clientWidth;
      checkLineCount();
      inputRef.value.focus();
    }
  });
});

// 组件卸载时清除定时器
onBeforeUnmount(() => {
  if (debounceTimer.value) {
    clearTimeout(debounceTimer.value);
  }
});

// 暴露方法给父组件
defineExpose({
  getImageFiles,
  clearImages,
  triggerImageUpload,
  removeImage
});

</script>

<style lang="less" scoped>
.input-box {
  display: grid;
  width: 100%;
  margin: 0 auto;
  border: 1px solid var(--gray-200);
  border-radius: 0.8rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  gap: 8px;

  /* Default: Multi-line layout */
  padding: 0.8rem 0.75rem 0.6rem 0.75rem;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  grid-template-areas:
    "input input"
    "options send";

  .expand-options {
    justify-self: start;
  }
  .send-button-container {
    justify-self: end;
  }

  &.single-line {
    padding: 0.75rem 0.75rem;
    grid-template-columns: auto 1fr auto;
    grid-template-rows: 1fr;
    grid-template-areas: "options input send";
    align-items: center;

    .input-area {
      .user-input {
        min-height: 24px;
        height: 24px;
        align-self: center;
        white-space: nowrap;
        overflow: hidden;
      }
    }

    .expand-options, .send-button-container {
      align-self: center;
    }
  }
}

// 图片预览区域
.image-previews {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;

  .preview-item {
    position: relative;
    width: 60px;
    height: 60px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--gray-200);

    .preview-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .preview-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 10px;
      
      .upload-text {
        margin-top: 4px;
      }
    }

    .preview-actions {
      position: absolute;
      top: 2px;
      right: 2px;
      
      .remove-btn {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.6);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;

        &:hover {
          background: rgba(0, 0, 0, 0.8);
        }
      }
    }
  }
}

.input-area {
  grid-area: input;
  display: flex;
  align-items: flex-end;
  gap: 8px;

  .user-input {
    flex: 1;
    width: 100%;
    padding: 0;
    background-color: transparent;
    border: none;
    margin: 0;
    color: #222222;
    font-size: 15px;
    outline: none;
    resize: none;
    line-height: 1.5;
    font-family: inherit;
    min-height: 44px;
    max-height: 200px;

    &:focus {
      outline: none;
      box-shadow: none;
    }

    &::placeholder {
      color: #888888;
    }
  }
}

.image-upload-container {
  display: flex;
  align-items: center;

  .image-upload-btn {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--gray-600);
    transition: all 0.2s ease;

    &:hover {
      background-color: var(--gray-100);
      color: var(--main-500);
    }

    &:disabled {
      color: var(--gray-400);
      cursor: not-allowed;
    }
  }
}

.expand-options {
  grid-area: options;
  display: flex;
  align-items: center;
}

.send-button-container {
  grid-area: send;
  display: flex;
  align-items: center;
  justify-content: center;
}

.expand-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-600);
  transition: all 0.2s ease;

  &:hover {
    background-color: var(--gray-100);
    color: var(--main-500);
  }

  .anticon {
    font-size: 12px;
    transition: transform 0.2s ease;

    &.rotated {
      transform: rotate(45deg);
    }
  }
}

// Popover 选项样式
.popover-options {
  min-width: 200px;
  max-width: 300px;

  .no-options {
    color: var(--gray-700);
    font-size: 12px;
    text-align: center;
  }

  :deep(.opt-item) {
    border-radius: 12px;
    border: 1px solid var(--gray-300);
    padding: 5px 10px;
    cursor: pointer;
    font-size: 12px;
    color: var(--gray-700);
    transition: all 0.2s ease;
    margin: 4px;
    display: inline-block;

    &:hover {
      background-color: var(--main-10);
      color: var(--main-color);
    }

    &.active {
      color: var(--main-color);
      border: 1px solid var(--main-500);
      background-color: var(--main-10);
    }
  }
}

.send-button.ant-btn-icon-only {
  height: 32px;
  width: 32px;
  cursor: pointer;
  background-color: var(--main-500);
  border-radius: 50%;
  border: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  color: white;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;

  &:hover {
    background-color: var(--main-color);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    color: white;
  }

  &:active {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  &:disabled {
    background-color: var(--gray-400);
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
}

@media (max-width: 520px) {
  .input-box {
    border-radius: 15px;
    padding: 0.625rem 0.875rem;
  }
  
  .image-previews {
    .preview-item {
      width: 50px;
      height: 50px;
    }
  }
}
</style>