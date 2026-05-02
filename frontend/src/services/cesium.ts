/* Cesium service.
 *
 * We deliberately do NOT do `import * as Cesium from 'cesium'`. In dev,
 * Vite's esbuild dep optimiser pre-bundles Cesium from its ES-source
 * tangle and the result silently fails to render the globe on Firefox
 * 130+ (Chromium masks the bug). In production, `vite-plugin-cesium`
 * already injects a `<script src="/cesium/Cesium.js">` tag and rewrites
 * `import * as Cesium from 'cesium'` to read from the global. Reading
 * the global directly works the same in both modes, so we use it -- and
 * a dev-only Vite plugin (see `vite.config.ts`) injects the same UMD
 * script tag in dev so `window.Cesium` is available. */
import type * as CesiumNS from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import type { ConjunctionListItem } from '@/api/types';

declare global {
  interface Window {
    Cesium?: typeof CesiumNS;
  }
}

const Cesium: typeof CesiumNS = (() => {
  if (typeof window === 'undefined' || window.Cesium === undefined) {
    throw new Error(
      'Cesium UMD bundle not loaded. Expected `/cesium/Cesium.js` to define window.Cesium.'
    );
  }
  return window.Cesium;
})();

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

// Marker geometry. Heights are in metres (Cartesian3.fromDegrees expects
// metres for the third argument); pixel sizes are device-independent.
const KM_TO_M = 1000;
const POINT_PIXEL_SIZE = 9;
const POINT_PIXEL_SIZE_HIGHLIGHTED = 16;
const POINT_OUTLINE_WIDTH = 1;
const LABEL_OFFSET_PX = -12;
const LABEL_OUTLINE_WIDTH = 2;
const POLYLINE_WIDTH_PX = 1.5;

const COLOR_BACKGROUND = '#020617';
const COLOR_HIGH_RISK = '#ef4444';
const COLOR_NORMAL = '#22d3ee';
const COLOR_LABEL_BG = 'rgba(15,23,42,0.7)';

export async function createGlobe(opts: InitOptions): Promise<CesiumViewerHandle> {
  // Use a public Cesium ION token only if the user supplied one. Without a
  // token, the default ION imagery provider fails silently and the globe
  // ends up as a featureless blue ellipsoid. We fall back to OpenStreetMap
  // tiles (no token required, free and reliable) so the Earth always
  // renders for end users out of the box.
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
    selectionIndicator: false,
    // Imagery: a single 2048×1024 Natural Earth II texture stitched from
    // Cesium's bundled tile set (public domain, no attribution-by-third-
    // party requirement, no auth, no rate limits, no CORS).
    //
    // We use SingleTileImageryProvider rather than the tile-pyramid
    // providers because Cesium's TMS pyramid pipeline turned out to skip
    // the imagery request silently in Firefox 130+ when served via Vite's
    // dev middleware (no tile request fired, while Chromium fired the
    // expected six). A single tile sidesteps the entire tiling-scheme
    // initialisation path and renders identically on every modern engine.
    baseLayer: ionToken
      ? undefined
      : new Cesium.ImageryLayer(
          await Cesium.SingleTileImageryProvider.fromUrl('/earth-natural-earth-ii.jpg', {
            rectangle: Cesium.Rectangle.fromDegrees(-180, -90, 180, 90),
            credit: new Cesium.Credit('Natural Earth II - public domain', true)
          })
        )
  });
  viewer.scene.globe.enableLighting = true;
  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString(COLOR_BACKGROUND);

  const entityById = new Map<string, ReturnType<typeof viewer.entities.add>>();

  for (const c of opts.conjunctions.slice(0, MAX_PLOTTED_CONJUNCTIONS)) {
    // Conjunctions whose TLEs failed to propagate carry a null position
    // pair; skip them rather than placing them at an arbitrary point so
    // the scene stays truthful (markers reflect actual orbital state).
    if (c.tca_position_a === null || c.tca_position_b === null) continue;

    const a = Cesium.Cartesian3.fromDegrees(
      c.tca_position_a.longitude_deg,
      c.tca_position_a.latitude_deg,
      c.tca_position_a.altitude_km * KM_TO_M
    );
    const b = Cesium.Cartesian3.fromDegrees(
      c.tca_position_b.longitude_deg,
      c.tca_position_b.latitude_deg,
      c.tca_position_b.altitude_km * KM_TO_M
    );
    // Encounter-point marker: midpoint between the two satellites at TCA.
    const midpoint = Cesium.Cartesian3.midpoint(a, b, new Cesium.Cartesian3());
    const isHighRisk = c.miss_distance_km < HIGH_RISK_MISS_KM;
    const colorHex = isHighRisk ? COLOR_HIGH_RISK : COLOR_NORMAL;
    const color = Cesium.Color.fromCssColorString(colorHex);

    const entity = viewer.entities.add({
      id: c.id,
      position: midpoint,
      point: {
        pixelSize: POINT_PIXEL_SIZE,
        color,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: POINT_OUTLINE_WIDTH
      },
      label: {
        text: `${c.sat_a.name} ↔ ${c.sat_b.name}`,
        font: '12px Inter, sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineWidth: LABEL_OUTLINE_WIDTH,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, LABEL_OFFSET_PX),
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString(COLOR_LABEL_BG)
      },
      polyline: {
        positions: [a, b],
        width: POLYLINE_WIDTH_PX,
        material: color,
        arcType: Cesium.ArcType.NONE
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
