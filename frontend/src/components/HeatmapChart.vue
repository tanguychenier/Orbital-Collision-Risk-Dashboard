<script setup lang="ts">
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue';
import type { HeatmapAltitudeInclinationResponse } from '@/api/types';
import type { ECharts, EChartsOption } from 'echarts';

interface Props {
  matrix: HeatmapAltitudeInclinationResponse | null;
  loading: boolean;
}

const props = defineProps<Props>();

const containerRef = shallowRef<HTMLDivElement | null>(null);
const instanceRef = shallowRef<ECharts | null>(null);
const resizeObserverRef = shallowRef<ResizeObserver | null>(null);

async function ensureChart(): Promise<ECharts | null> {
  if (instanceRef.value !== null) {
    return instanceRef.value;
  }
  if (containerRef.value === null) {
    return null;
  }
  const echarts = await import('echarts');
  const chart = echarts.init(containerRef.value, undefined, { renderer: 'canvas' }) as unknown as ECharts;
  instanceRef.value = chart;
  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.value);
    resizeObserverRef.value = observer;
  }
  return chart;
}

function buildOption(matrix: HeatmapAltitudeInclinationResponse): EChartsOption {
  const data: Array<[number, number, number]> = [];
  let maxCount = 0;
  for (let i = 0; i < matrix.counts.length; i += 1) {
    const row = matrix.counts[i];
    for (let j = 0; j < row.length; j += 1) {
      data.push([j, i, row[j]]);
      if (row[j] > maxCount) {
        maxCount = row[j];
      }
    }
  }
  const inclinationLabels = matrix.inclination_bands.map(
    (lower) => `${lower}-${lower + matrix.inclination_step_deg}°`
  );
  const altitudeLabels = matrix.altitude_bands.map(
    (lower) => `${lower}-${lower + matrix.altitude_step_km}`
  );
  return {
    tooltip: {
      position: 'top',
      formatter: (params) => {
        const arrayParams = params as unknown as { data: [number, number, number] };
        const [j, i, count] = arrayParams.data;
        return `${altitudeLabels[i]} km × ${inclinationLabels[j]}<br/><strong>${count}</strong> satellites`;
      }
    },
    grid: { left: 70, right: 24, top: 20, bottom: 70 },
    xAxis: {
      type: 'category',
      data: inclinationLabels,
      name: 'Inclination',
      nameLocation: 'middle',
      nameGap: 40,
      axisLabel: {
        interval: 1,
        fontSize: 10,
        rotate: 45,
        color: '#cbd5e1'
      }
    },
    yAxis: {
      type: 'category',
      data: altitudeLabels,
      name: 'Altitude (km)',
      nameLocation: 'middle',
      nameGap: 60,
      axisLabel: { interval: 1, fontSize: 10, color: '#cbd5e1' }
    },
    visualMap: {
      min: 0,
      max: Math.max(maxCount, 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#cbd5e1' },
      inRange: {
        color: ['#0f172a', '#155e75', '#0891b2', '#22d3ee', '#fde68a', '#f97316', '#dc2626']
      }
    },
    series: [
      {
        type: 'heatmap',
        name: 'Satellites',
        data,
        progressive: 1000,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };
}

async function render(): Promise<void> {
  const chart = await ensureChart();
  if (chart === null) {
    return;
  }
  if (props.matrix === null) {
    chart.clear();
    return;
  }
  chart.setOption(buildOption(props.matrix), true);
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
  () => [props.matrix, props.loading] as const,
  () => {
    void render();
  }
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
  <div class="w-full h-[480px]" data-testid="heatmap-chart">
    <div ref="containerRef" class="w-full h-full" role="img" aria-label="Altitude versus inclination heatmap" />
  </div>
</template>
