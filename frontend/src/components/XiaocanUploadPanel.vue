<template>
  <el-collapse v-model="activeNames" class="upload-collapse">
    <el-collapse-item name="upload">
      <template #title>
        <span class="collapse-title">
          <el-icon><UploadFilled /></el-icon>
          小蚕订单上传
          <span class="collapse-hint">每次上传将清空并替换已有小蚕数据</span>
        </span>
      </template>

      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="true"
        :show-file-list="false"
        :http-request="customUpload"
        accept=".xlsx,.xlsm"
        :before-upload="beforeUpload"
        class="compact-upload"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽 Excel 到此处，或<em>点击选择文件</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx / .xlsm，包含列：下单平台、订单时间、小蚕订单编号</div>
        </template>
      </el-upload>

      <el-progress
        v-if="uploading || polling || progress === 100"
        :percentage="progress"
        :status="progress === 100 ? 'success' : ''"
        :stroke-width="8"
        style="margin-top: 10px"
      />

      <div v-if="polling" class="polling-text">
        <el-icon><Loading /></el-icon>
        {{ pollingText }}
      </div>

      <el-alert
        v-if="result && result.result"
        :title="successTitle"
        type="success"
        :closable="false"
        show-icon
        style="margin-top: 10px"
      >
        <div class="result-grid">
          <span><b>导入行数</b> {{ result.result.total_rows }}</span>
          <span><b>匹配原订单</b> {{ result.result.matched_count }}</span>
          <span><b>未匹配</b> {{ result.result.unmatched_count }}</span>
        </div>
      </el-alert>

      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        :closable="false"
        show-icon
        style="margin-top: 10px"
      />
    </el-collapse-item>
  </el-collapse>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Loading, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { uploadXiaocanExcel, fetchTaskStatus, type TaskResult } from '../api'

const emit = defineEmits<{ (e: 'imported', result: TaskResult): void }>()

const activeNames = ref<string[]>([])
const uploadRef = ref()
const uploading = ref(false)
const polling = ref(false)
const progress = ref(0)
const result = ref<TaskResult | null>(null)
const errorMsg = ref('')
const pollingText = ref('')

const successTitle = computed(() =>
  result.value && result.value.result?.matched_count && result.value.result.matched_count > 0
    ? '导入成功，已匹配原订单'
    : '导入成功（无原订单匹配，请确认订单号格式一致）',
)

function beforeUpload(file: File): boolean {
  errorMsg.value = ''
  const ok = /\.(xlsx|xlsm)$/i.test(file.name)
  if (!ok) {
    ElMessage.error('仅支持 .xlsx / .xlsm 文件')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件超过 50MB 限制')
    return false
  }
  return true
}

async function customUpload(options: UploadRequestOptions) {
  uploading.value = true
  polling.value = false
  progress.value = 0
  result.value = null
  errorMsg.value = ''
  try {
    const uploadRes = await uploadXiaocanExcel(options.file as File, (pct) => {
      progress.value = pct
    })

    if (uploadRes.status === 'success') {
      progress.value = 100
      result.value = uploadRes
      emit('imported', uploadRes)
      ElMessage.success('导入完成')
    } else {
      await startPolling(uploadRes.task_id)
    }
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '未知错误'
    errorMsg.value = `导入失败：${detail}`
    progress.value = 0
  } finally {
    uploading.value = false
  }
}

async function startPolling(taskId: string) {
  polling.value = true
  pollingText.value = '正在处理，请稍候...'
  try {
    for (let i = 0; i < 120; i++) {
      const status = await fetchTaskStatus(taskId)
      progress.value = status.progress
      pollingText.value = status.message || '处理中...'

      if (status.status === 'success') {
        progress.value = 100
        result.value = status
        emit('imported', status)
        ElMessage.success(status.message || '导入完成')
        break
      }
      if (status.status === 'failed') {
        errorMsg.value = status.error || '导入失败'
        progress.value = 0
        break
      }
      await new Promise((r) => setTimeout(r, 1000))
    }
  } catch (err: any) {
    errorMsg.value = `轮询失败：${err?.message || '未知错误'}`
  } finally {
    polling.value = false
  }
}
</script>

<style scoped>
.upload-collapse {
  border: none;
  margin-bottom: 8px;
}
.upload-collapse :deep(.el-collapse-item__header) {
  font-size: 13px;
  color: #909399;
  border: none;
  background: transparent;
  padding-left: 0;
  min-height: 32px;
  height: 32px;
  line-height: 32px;
}
.upload-collapse :deep(.el-collapse-item__wrap) {
  border: none;
}
.upload-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 12px;
}
.collapse-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 400;
}
.collapse-hint {
  font-size: 11px;
  color: #c0c4cc;
  margin-left: 4px;
}
.compact-upload :deep(.el-upload-dragger) {
  padding: 20px;
}
.compact-upload :deep(.el-icon--upload) {
  font-size: 40px;
  margin-bottom: 4px;
}
.result-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 4px;
  font-size: 13px;
}
.result-grid b {
  color: #606266;
  margin-right: 6px;
  font-weight: 500;
}
.polling-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  margin-top: 8px;
}
</style>
