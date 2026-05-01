<script setup lang="ts">
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue';
import type { ConjunctionTimelinePoint } from '@/api/types';
import type { EChartsType, EChartsOption } from 'echarts';

type ChartHandle = EChartsType;

interface Props {
  points: readonly ConjunctionTimelinePoint[];
  loading: boolean;
}

const props = defineProps<Props>();

const containerRef = shallowRef<HTMLDivElement | null>(null);
const instanceRef = shallowRef<ChartHandle | null>(null);
const resizeObserverRef = shallowRef<ResizeObserver | null>(null);

async function ensureChart(): Promise<ChartHandle | null> {
  if (instanceRef.value !== null) {
    return instanceRef.value;
  }
  if (containerRef.value === null) {
    return null;
  }
  const echarts = await import('echarts');
  const chart = echarts.init(containerRef.value, undefined, { renderer: 'canvas' }) as unknown as ChartHandle;
  instanceRef.value = chart;
  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.value);
    resizeObserverRef.value = observer;
  }
  return chart;
}

function buildOption(points: readonly ConjunctionTimelinePoint[]): EChartsOption {
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  const dates = sorted.map((p) => p.date);
  const totals = sorted.map((p) => p.total);
  const lt5 = sorted.map((p) => p.miss_lt_5km);
  const lt1 = sorted.map((p) => p.miss_lt_1km);
  return {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['Total', '< 5 km', '< 1 km'],
      textStyle: { color: '#cbd5e1' }
    },
    grid: { left: 50, right: 24, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: { color: '#cbd5e1', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: 'Conjunctions',
      nameTextStyle: { color: '#cbd5e1' },
      axisLabel: { color: '#cbd5e1', fontSize: 10 }
    },
    series: [
      {
        name: 'Total',
        type: 'line',
        areaStyle: { color: 'rgba(34, 211, 238, 0.18)' },
        lineStyle: { color: '#22d3ee' },
        symbol: 'none',
        data: totals
      },
      {
        name: '< 5 km',
        type: 'line',
        areaStyle: { color: 'rgba(249, 115, 22, 0.20)' },
        lineStyle: { color: '#f97316' },
        symbol: 'none',
        data: lt5
      },
      {
        name: '< 1 km',
        type: 'line',
        areaStyle: { color: 'rgba(220, 38, 38, 0.30)' },
        lineStyle: { color: '#dc2626' },
        symbol: 'none',
        data: lt1
      }
    ]
  };
}

async function render(): Promise<void> {
  const chart = await ensureChart();
  if (chart === null) {
    return;
  }
  if (props.points.length === 0) {
    chart.clear();
    return;
  }
  chart.setOption(buildOption(props.points), true);
  if (props.loading) {
    chart.showLoading();
  } else {
    chart.hideLoading();
  }
}

onMounted(() => {
  void render();
});

watch(
  () => [props.points, props.loading] as const,
  () => {
    void render();
  },
  { deep: true }
);

onBeforeUnmount(() => {
  if (resizeObserverRef.value !== null) {
    resizeObserverRef.value.disconnect();
    resizeObserverRef.value = null;
  }
  if (instanceRef.value !== null) {
    instanceRef.value.dispose();
    instanceRef.value = null;
  }
});
</script>

<template>
  <div class="w-full h-[320px]" data-testid="timeline-chart">
    <div
      ref="containerRef"
      class="w-full h-full"
      role="img"
      aria-label="Conjunctions per day timeline chart"
    />
  </div>
</template>
