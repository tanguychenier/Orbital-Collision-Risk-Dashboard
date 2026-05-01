/* Cesium service. Imports the library statically: lazy `import('cesium')`
 * triggers a Temporal-Dead-Zone error in the production bundle because of
 * Cesium's internal cyclic dependencies. Static import side-steps it; the
 * heavy chunks are still split off via Vite's default code-splitting and
 * Cesium's CSS is loaded once on first call. */
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
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

// --- Visual constants -------------------------------------------------------
// Cap the number of plotted entities to keep the lazy-loaded scene
// responsive on low-end mobile devices.
const MAX_PLOTTED_CONJUNCTIONS = 50;

// Distance below which a conjunction is rendered in the "danger" red
// instead of the default cyan. Mirrors the backend triage threshold.
const HIGH_RISK_MISS_KM = 1;

// Pseudo-randomisation moduli used to scatter the synthetic markers
// across the globe when no real ECEF position is available.
const LON_MOD = 360;
const LAT_MOD = 140;
const LON_MULTIPLIER = 7;
const LAT_MULTIPLIER = 3;
const LON_OFFSET = 180;
const LAT_OFFSET = 70;

// Marker geometry. Heights are in metres (Cartesian3.fromDegrees expects
// metres for the third argument); pixel sizes are device-independent.
const MARKER_HEIGHT_M = 550_000;
const POINT_PIXEL_SIZE = 9;
const POINT_PIXEL_SIZE_HIGHLIGHTED = 16;
const POINT_OUTLINE_WIDTH = 1;
const LABEL_OFFSET_PX = -12;
const LABEL_OUTLINE_WIDTH = 2;

const COLOR_BACKGROUND = '#020617';
const COLOR_HIGH_RISK = '#ef4444';
const COLOR_NORMAL = '#22d3ee';
const COLOR_LABEL_BG = 'rgba(15,23,42,0.7)';

export async function createGlobe(opts: InitOptions): Promise<CesiumViewerHandle> {
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
  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString(COLOR_BACKGROUND);

  const entityById = new Map<string, ReturnType<typeof viewer.entities.add>>();

  for (const c of opts.conjunctions.slice(0, MAX_PLOTTED_CONJUNCTIONS)) {
    const seed = (c.sat_a.norad_id + c.sat_b.norad_id) % LON_MOD;
    const lon = ((seed * LON_MULTIPLIER) % LON_MOD) - LON_OFFSET;
    const lat = ((seed * LAT_MULTIPLIER) % LAT_MOD) - LAT_OFFSET;
    const position = Cesium.Cartesian3.fromDegrees(lon, lat, MARKER_HEIGHT_M);
    const entity = viewer.entities.add({
      id: c.id,
      position,
      point: {
        pixelSize: POINT_PIXEL_SIZE,
        color:
          c.miss_distance_km < HIGH_RISK_MISS_KM
            ? Cesium.Color.fromCssColorString(COLOR_HIGH_RISK)
            : Cesium.Color.fromCssColorString(COLOR_NORMAL),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: POINT_OUTLINE_WIDTH
      },
      label: {
        text: c.sat_a.name,
        font: '12px Inter, sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineWidth: LABEL_OUTLINE_WIDTH,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, LABEL_OFFSET_PX),
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString(COLOR_LABEL_BG)
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
        entity.point.pixelSize = (
          isActive ? POINT_PIXEL_SIZE_HIGHLIGHTED : POINT_PIXEL_SIZE
        ) as never;
      }
    }
  };
}
