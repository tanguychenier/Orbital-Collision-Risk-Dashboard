/* Lazy-loaded Cesium service. Imports the heavy library only when called. */
import type { ConjunctionListItem } from '@/api/types';

export interface CesiumViewerHandle {
  destroy: () => void;
  highlight: (id: string | null) => void;
}

interface InitOptions {
  container: HTMLElement;
  conjunctions: ConjunctionListItem[];
  onSelect?: (id: string) => void;
}

export async function createGlobe(opts: InitOptions): Promise<CesiumViewerHandle> {
  const Cesium = await import('cesium');
  await import('cesium/Build/Cesium/Widgets/widgets.css');

  // Use a public default ion token only if user provided one
  const ionToken = (import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined) ?? '';
  if (ionToken) {
    Cesium.Ion.defaultAccessToken = ionToken;
  }

  const viewer = new Cesium.Viewer(opts.container, {
    animation: false,
    timeline: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    baseLayerPicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false
  });
  viewer.scene.globe.enableLighting = true;
  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#020617');

  const entityById = new Map<string, ReturnType<typeof viewer.entities.add>>();

  for (const c of opts.conjunctions.slice(0, 50)) {
    const seed = (c.sat_a.norad_id + c.sat_b.norad_id) % 360;
    const lon = ((seed * 7) % 360) - 180;
    const lat = ((seed * 3) % 140) - 70;
    const position = Cesium.Cartesian3.fromDegrees(lon, lat, 550_000);
    const entity = viewer.entities.add({
      id: c.id,
      position,
      point: {
        pixelSize: 9,
        color:
          c.miss_distance_km < 1
            ? Cesium.Color.fromCssColorString('#ef4444')
            : Cesium.Color.fromCssColorString('#22d3ee'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1
      },
      label: {
        text: c.sat_a.name,
        font: '12px Inter, sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -12),
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString('rgba(15,23,42,0.7)')
      }
    });
    entityById.set(c.id, entity);
  }

  if (opts.onSelect) {
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((evt: unknown) => {
      const position = (evt as { position?: unknown }).position;
      if (!position) return;
      const picked = viewer.scene.pick(position as never);
      if (picked && picked.id && typeof picked.id.id === 'string') {
        opts.onSelect?.(picked.id.id);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  return {
    destroy: () => {
      try {
        viewer.destroy();
      } catch {
        /* ignore */
      }
    },
    highlight: (id: string | null) => {
      for (const [key, entity] of entityById.entries()) {
        if (!entity.point) continue;
        const isActive = key === id;
        entity.point.pixelSize = (isActive ? 16 : 9) as never;
      }
    }
  };
}
