<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <el-image
          class="brand-mark"
          :src="logoUrl"
          :preview-src-list="[logoUrl]"
          preview-teleported
          hide-on-click-modal
          fit="contain"
          alt="BearmeCoffee"
        />
        <div class="brand-text">
          <h1>BearmeCoffee 订单数据大盘</h1>
          <p>Excel 上传 · 全量呈现 · MySQL 存储</p>
        </div>
      </div>
      <WeatherClock />
    </header>
    <main class="app-main">
      <DashboardView />
    </main>
  </div>
</template>

<script setup lang="ts">
import DashboardView from './views/DashboardView.vue'
import WeatherClock from './components/WeatherClock.vue'
import logoUrl from './assets/logo.jpg'
</script>

<style>
* {
  box-sizing: border-box;
}
html,
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  background: #f4f6fa;
  color: #1f2937;
}
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-header {
  background: linear-gradient(120deg, #3a2a1f 0%, #5b3a26 60%, #8a5a3b 100%);
  color: #fff;
  padding: 18px 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}
.brand-mark {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  background: #fff;
  padding: 4px;
  cursor: pointer;
  flex-shrink: 0;
}
.brand-mark img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.brand-text h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.brand-text p {
  margin: 4px 0 0;
  font-size: 12px;
  opacity: 0.78;
}
.app-main {
  flex: 1;
  padding: 24px 32px 48px;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
}
@media (max-width: 720px) {
  .app-header {
    padding: 14px 18px;
  }
  .brand-text h1 {
    font-size: 18px;
  }
}
</style>
