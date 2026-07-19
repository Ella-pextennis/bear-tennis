<template>
  <div class="weather-clock">
    <div class="time-block">
      <div class="time">{{ timeText }}</div>
      <div class="date">{{ dateText }}</div>
    </div>
    <div class="weather-block" :class="{ loading: loading }">
      <span v-if="error" class="weather-icon" title="天气加载失败">🌥️</span>
      <span v-else class="weather-icon">{{ weatherInfo.icon }}</span>
      <div class="weather-info">
        <div class="weather-temp">
          <span v-if="!error && weather.temp !== null">{{ weather.temp }}°C</span>
          <span v-else-if="error" class="err-text">天气离线</span>
          <span v-else class="placeholder">--</span>
        </div>
        <div class="weather-desc">{{ weatherInfo.desc }}{{ locationName }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

interface WeatherState {
  temp: number | null
  code: number | null
  windSpeed: number | null
}

const props = defineProps<{
  latitude?: number
  longitude?: number
  locationName?: string
}>()

const LAT = props.latitude ?? 39.9042 // 默认北京
const LON = props.longitude ?? 116.4074
const LOCATION = props.locationName ?? '北京'

const timeText = ref('')
const dateText = ref('')
const weather = ref<WeatherState>({ temp: null, code: null, windSpeed: null })
const loading = ref(true)
const error = ref(false)

let clockTimer: ReturnType<typeof setInterval> | null = null
let weatherTimer: ReturnType<typeof setInterval> | null = null

const WEEK_DAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

const WEATHER_MAP: Record<number, { icon: string; desc: string }> = {
  0: { icon: '☀️', desc: '晴' },
  1: { icon: '🌤️', desc: '主晴' },
  2: { icon: '⛅', desc: '多云' },
  3: { icon: '☁️', desc: '阴' },
  45: { icon: '🌫️', desc: '雾' },
  48: { icon: '🌫️', desc: '雾凇' },
  51: { icon: '🌦️', desc: '毛毛雨' },
  53: { icon: '🌦️', desc: '毛毛雨' },
  55: { icon: '🌦️', desc: '强毛毛雨' },
  56: { icon: '🌧️', desc: '冻毛毛雨' },
  57: { icon: '🌧️', desc: '强冻毛毛雨' },
  61: { icon: '🌧️', desc: '小雨' },
  63: { icon: '🌧️', desc: '中雨' },
  65: { icon: '🌧️', desc: '大雨' },
  66: { icon: '🌧️', desc: '冻雨' },
  67: { icon: '🌧️', desc: '强冻雨' },
  71: { icon: '🌨️', desc: '小雪' },
  73: { icon: '🌨️', desc: '中雪' },
  75: { icon: '❄️', desc: '大雪' },
  77: { icon: '🌨️', desc: '雪粒' },
  80: { icon: '🌦️', desc: '阵雨' },
  81: { icon: '🌧️', desc: '强阵雨' },
  82: { icon: '⛈️', desc: '暴阵雨' },
  85: { icon: '🌨️', desc: '阵雪' },
  86: { icon: '❄️', desc: '强阵雪' },
  95: { icon: '⛈️', desc: '雷暴' },
  96: { icon: '⛈️', desc: '雷暴冰雹' },
  99: { icon: '⛈️', desc: '强雷暴冰雹' },
}

const weatherInfo = computed(() => {
  if (weather.value.code === null) return { icon: '⏳', desc: '加载中' }
  return WEATHER_MAP[weather.value.code] || { icon: '🌡️', desc: '未知' }
})

const locationName = computed(() => (error.value ? '' : ` · ${LOCATION}`))

function pad(n: number): string {
  return n < 10 ? '0' + n : String(n)
}

function updateClock() {
  const now = new Date()
  timeText.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  const y = now.getFullYear()
  const m = now.getMonth() + 1
  const d = now.getDate()
  const w = WEEK_DAYS[now.getDay()]
  dateText.value = `${y}年${m}月${d}日 ${w}`
}

async function fetchWeather() {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current_weather=true&timezone=Asia%2FShanghai`
  try {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const cw = data?.current_weather
    if (!cw) throw new Error('no current_weather')
    weather.value = {
      temp: typeof cw.temperature === 'number' ? Math.round(cw.temperature) : null,
      code: typeof cw.weathercode === 'number' ? cw.weathercode : null,
      windSpeed: typeof cw.windspeed === 'number' ? cw.windspeed : null,
    }
    error.value = false
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  fetchWeather()
  // 每 10 分钟刷新一次天气
  weatherTimer = setInterval(fetchWeather, 10 * 60 * 1000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (weatherTimer) clearInterval(weatherTimer)
})
</script>

<style scoped>
.weather-clock {
  display: flex;
  align-items: center;
  gap: 18px;
  color: #fff;
}
.time-block {
  text-align: right;
  line-height: 1.2;
}
.time {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 1px;
}
.date {
  font-size: 12px;
  opacity: 0.82;
  margin-top: 4px;
}
.weather-block {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
  min-width: 140px;
}
.weather-block.loading {
  opacity: 0.7;
}
.weather-icon {
  font-size: 30px;
  line-height: 1;
}
.weather-info {
  line-height: 1.25;
}
.weather-temp {
  font-size: 16px;
  font-weight: 600;
}
.weather-desc {
  font-size: 11px;
  opacity: 0.86;
  white-space: nowrap;
}
.err-text {
  font-size: 13px;
  opacity: 0.8;
}
.placeholder {
  opacity: 0.5;
}
@media (max-width: 900px) {
  .weather-clock {
    gap: 10px;
  }
  .time {
    font-size: 18px;
  }
  .weather-block {
    min-width: auto;
    padding: 6px 10px;
  }
  .weather-icon {
    font-size: 24px;
  }
}
</style>
