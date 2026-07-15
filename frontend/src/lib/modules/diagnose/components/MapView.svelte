<script>
	import { onDestroy, onMount } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';

	import {
		createFieldNote,
		createObservationZone,
		deleteFieldNote,
		deleteObservationZone,
		fetchCogLayers,
		fetchFieldNotes,
		fetchObservationZones,
		fieldNoteMediaUrl,
		updateFieldNote,
		updateObservationZone
	} from '$lib/modules/diagnose/api';
	import { LULC_LEGEND, MAX_FIELD_NOTE_MEDIA_BYTES, OBSERVATION_ZONE_COLOR, FIELD_NOTE_COLOR, ZONE_COLORS } from '$lib/modules/diagnose/map-constants';
	import FieldNoteIcon from '$lib/modules/diagnose/components/icons/FieldNoteIcon.svelte';
	import ObservationZoneIcon from '$lib/modules/diagnose/components/icons/ObservationZoneIcon.svelte';

	const BASE_LAYERS = {
		osm: {
			id: 'base-osm',
			label: 'OpenStreetMap',
			tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
			attribution: '© OpenStreetMap contributors'
		},
		esri: {
			id: 'base-esri',
			label: 'ESRI Imagery',
			tiles: [
				'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
			],
			attribution: '© Esri, Maxar, Earthstar Geographics'
		}
	};

	const UUID_RE =
		/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

	function zoneIdFromFeature(f) {
		const id = String(f.properties?.id ?? '');
		return UUID_RE.test(id) ? id : null;
	}

	/** @param {string} hex */
	function contrastTextColor(hex) {
		const normalized = String(hex || '#000000').replace('#', '');
		if (normalized.length !== 6) return '#ffffff';
		const r = parseInt(normalized.slice(0, 2), 16);
		const g = parseInt(normalized.slice(2, 4), 16);
		const b = parseInt(normalized.slice(4, 6), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.55 ? '#000000' : '#ffffff';
	}

	function closeSelectedZone() {
		selectedZone = null;
		editingSelectedZone = null;
		showSelectedZoneMenu = false;
	}

	function closeSelectedFieldNote() {
		selectedFieldNote = null;
		editingSelectedFieldNote = null;
		showSelectedFieldNoteMenu = false;
	}

	function selectLayer(layer) {
		selectedLayer = layer;
		closeSelectedZone();
		closeSelectedFieldNote();
		cancelPendingForms();
	}

	function cancelPendingForms() {
		pendingPoint = null;
		pendingZone = null;
		addingFieldNote = false;
		zoneDraw = false;
		noteText = '';
		notePhoto = undefined;
		noteAudio = undefined;
		if (notePhotoPreview) URL.revokeObjectURL(notePhotoPreview);
		notePhotoPreview = null;
		if (noteAudioPreview) URL.revokeObjectURL(noteAudioPreview);
		noteAudioPreview = null;
		noteMediaError = '';
		zoneText = '';
		zoneDescription = '';
		resetDrawState();
	}

	function isPlacingOnMap() {
		return zoneDraw || (addingFieldNote && !pendingPoint);
	}

	/** Fallback expressions; runtime sizes set from viewport height in updateDrawSizes(). */
	const VERTEX_RADIUS = 11;
	const LINE_WIDTH = 3.5;
	const FIELD_NOTE_PIN_BASE = 1.35;
	const FIELD_NOTE_PIN_FILL = FIELD_NOTE_COLOR;
	let fieldNotePinReady = false;

	function ensureFieldNotePinIcon() {
		if (!map) return Promise.resolve();
		if (fieldNotePinReady) return Promise.resolve();

		const w = 48;
		const h = 62;
		const canvas = document.createElement('canvas');
		canvas.width = w;
		canvas.height = h;
		const ctx = canvas.getContext('2d');
		if (!ctx) return Promise.resolve();

		const cx = w / 2;
		const headY = 18;
		const headR = 15;

		function pinPath() {
			ctx.beginPath();
			ctx.arc(cx, headY, headR, Math.PI, 0, false);
			ctx.lineTo(cx, h - 4);
			ctx.closePath();
		}

		pinPath();
		ctx.fillStyle = FIELD_NOTE_PIN_FILL;
		ctx.fill();

		pinPath();
		ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
		ctx.lineWidth = 2;
		ctx.lineJoin = 'round';
		ctx.stroke();

		ctx.beginPath();
		ctx.arc(cx, headY, 5, 0, Math.PI * 2);
		ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
		ctx.fill();

		if (map.hasImage('field-note-pin')) map.removeImage('field-note-pin');
		map.addImage('field-note-pin', ctx.getImageData(0, 0, w, h), { pixelRatio: 2 });
		fieldNotePinReady = true;
		return Promise.resolve();
	}

	let lastHoverPoint = null;

	function markerRadiusPx() {
		if (!map) return VERTEX_RADIUS;
		const h = map.getContainer().clientHeight || 700;
		return Math.max(10, Math.round(h * 0.032 * 0.7));
	}

	function lineWidthPx() {
		if (!map) return LINE_WIDTH;
		const h = map.getContainer().clientHeight || 700;
		return Math.max(3, h * 0.007 * 0.7);
	}

	function fieldNotePinSize() {
		return Math.max(0.75, (markerRadiusPx() / VERTEX_RADIUS) * FIELD_NOTE_PIN_BASE);
	}

	function clickableFeatureLayers() {
		if (!selectedLayer || selectedLayer.kind !== 'primary') return [];
		if (selectedLayer.id === 'observation-zones' && showZonesLayer) {
			return ['zones-fill', 'zones-line', 'zones-label'];
		}
		if (selectedLayer.id === 'field-notes' && showFieldNotesLayer) {
			return ['field-notes-point'];
		}
		return [];
	}

	function isOverClickableFeature(point) {
		if (!mapReady || !map || !point) return false;
		const layers = clickableFeatureLayers();
		if (!layers.length) return false;
		const hit = map.queryRenderedFeatures(point, { layers });
		for (const f of hit) {
			if (selectedLayer?.id === 'observation-zones') {
				if (zoneIdFromFeature(f)) return true;
			} else if (selectedLayer?.id === 'field-notes') {
				const id = String(f.properties?.id ?? f.id ?? '');
				if (UUID_RE.test(id)) return true;
			}
		}
		return false;
	}

	function updateMapCursor(point = lastHoverPoint) {
		if (!mapReady || !map) return;
		const canvas = map.getCanvas();
		if (isPlacingOnMap()) {
			canvas.style.cursor = dragVertexIndex !== null ? 'grabbing' : 'crosshair';
			return;
		}
		if (zoneDraw || pendingZone || addingFieldNote) {
			canvas.style.cursor = '';
			return;
		}
		if (point && isOverClickableFeature(point)) {
			canvas.style.cursor = 'pointer';
			return;
		}
		canvas.style.cursor = '';
	}

	function hitTolerancePx() {
		return markerRadiusPx() * 1.4;
	}

	function updateDrawSizes() {
		if (!mapReady) return;
		const r = markerRadiusPx();
		const w = lineWidthPx();
		const stroke = Math.max(1.5, r * 0.14);
		if (map.getLayer('draw-preview-vertices')) {
			map.setPaintProperty('draw-preview-vertices', 'circle-radius', r);
			map.setPaintProperty('draw-preview-vertices', 'circle-stroke-width', stroke);
		}
		if (map.getLayer('field-notes-point')) {
			map.setLayoutProperty('field-notes-point', 'icon-size', fieldNotePinSize());
		}
		if (map.getLayer('draw-preview-field-note')) {
			map.setLayoutProperty('draw-preview-field-note', 'icon-size', fieldNotePinSize());
		}
		for (const id of ['draw-preview-line', 'draw-preview-dash', 'zones-line']) {
			if (map.getLayer(id)) map.setPaintProperty(id, 'line-width', w);
		}
	}

	function ensureDrawPreviewOnTop() {
		if (!mapReady) return;
		for (const id of [
			'draw-preview-fill',
			'draw-preview-line',
			'draw-preview-dash',
			'draw-preview-vertices',
			'draw-preview-field-note'
		]) {
			if (map.getLayer(id)) map.moveLayer(id);
		}
	}

	let { project, refreshKey = 0 } = $props();

	const watershedBounds = $derived(project?.bounds ?? null);

	function cogTileUrl(layerId) {
		const params = new URLSearchParams();
		params.set('project_id', project.id);
		return `/api/diagnose/layers/cog/${layerId}/tiles/WebMercatorQuad/{z}/{x}/{y}?${params.toString()}`;
	}

	function removeCogLayers() {
		if (!map) return;
		for (const layer of cogLayers) {
			const layerId = `cog-${layer.id}`;
			if (map.getLayer(layerId)) map.removeLayer(layerId);
			if (map.getSource(layerId)) map.removeSource(layerId);
		}
		for (const styleLayer of map.getStyle().layers ?? []) {
			if (!styleLayer.id.startsWith('cog-')) continue;
			if (map.getLayer(styleLayer.id)) map.removeLayer(styleLayer.id);
			if (map.getSource(styleLayer.id)) map.removeSource(styleLayer.id);
		}
	}

	let container;
	let map;
	let noteText = $state('');
	let notePhoto = $state(undefined);
	let noteAudio = $state(undefined);
	let notePhotoPreview = $state(null);
	let noteAudioPreview = $state(null);
	let noteMediaError = $state('');
	let pendingPoint = $state(null);
	let status = $state('Loading map…');

	let baseLayer = $state('osm');
	const activeAttribution = $derived(
		baseLayer === 'osm' ? BASE_LAYERS.osm.attribution : BASE_LAYERS.esri.attribution
	);
	let selectedLayer = $state(null);
	let addingFieldNote = $state(false);
	let showZonesLayer = $state(true);
	let showFieldNotesLayer = $state(true);
	let mapReady = $state(false);
	let cogLayers = $state([]);
	let cogVisibility = $state({});
	let primaryLayerOrder = $state(['observation-zones', 'field-notes']);
	let sidebarWidth = $state(256);
	let sidebarResizing = $state(false);
	/** @type {{ category: 'secondary' | 'primary' | null, index: number | null }} */
	let dragReorder = $state({ category: null, index: null });

	const PRIMARY_LAYER_LABELS = {
		'observation-zones': 'Observation zones',
		'field-notes': 'Field notes'
	};

	let zoneDraw = $state(false);
	let drawCoords = $state([]);
	let cursorLngLat = $state(null);
	let dragVertexIndex = $state(null);
	let pendingZone = $state(null);
	let zoneText = $state('');
	let zoneDescription = $state('');
	let zoneColor = $state(OBSERVATION_ZONE_COLOR);
	let savingZone = $state(false);
	let selectedZone = $state(null);
	let editingSelectedZone = $state(null);
	let savedZones = $state([]);
	let savedFieldNotes = $state([]);
	let selectedFieldNote = $state(null);
	let editingSelectedFieldNote = $state(null);
	let showSelectedZoneMenu = $state(false);
	let showSelectedFieldNoteMenu = $state(false);
	let savingFieldNote = $state(false);

	let lastTapTime = 0;
	let lastTapIndex = -1;
	let didDrag = false;

	onMount(async () => {
		map = new maplibregl.Map({
			container,
			style: {
				version: 8,
				sources: {
					[BASE_LAYERS.osm.id]: {
						type: 'raster',
						tiles: [...BASE_LAYERS.osm.tiles],
						tileSize: 256
					},
					[BASE_LAYERS.esri.id]: {
						type: 'raster',
						tiles: [...BASE_LAYERS.esri.tiles],
						tileSize: 256
					}
				},
				layers: [
					{
						id: BASE_LAYERS.osm.id,
						type: 'raster',
						source: BASE_LAYERS.osm.id,
						layout: { visibility: 'visible' }
					},
					{
						id: BASE_LAYERS.esri.id,
						type: 'raster',
						source: BASE_LAYERS.esri.id,
						layout: { visibility: 'none' }
					}
				]
			},
			center: [0, 20],
			zoom: 2
		});

		map.addControl(new maplibregl.NavigationControl(), 'top-left');

		map.on('load', async () => {
			mapReady = true;
			map.setMaxBounds(null);
			applyBasemapVisibility(BASE_LAYERS.osm.id, baseLayer === 'osm');
			applyBasemapVisibility(BASE_LAYERS.esri.id, baseLayer === 'esri');
			await ensureFieldNotePinIcon();
			loadWatershedBoundary();
			await loadCogLayers();
			await reloadObservationZones();
			await reloadFieldNotes();
			if (cogLayers.length > 0) {
				selectLayer({ kind: 'secondary', id: cogLayers[0].id });
			} else {
				selectLayer({ kind: 'primary', id: 'observation-zones' });
			}
			initDrawPreview();
			updateDrawSizes();
			ensureDrawPreviewOnTop();
			status = 'Ready';
			requestAnimationFrame(() => map?.resize());
		});

		map.on('zoom', () => {
			updateDrawSizes();
			setDrawPreviewFromState();
		});
		map.on('resize', updateDrawSizes);

		const resizeObserver = new ResizeObserver(() => map?.resize());
		resizeObserver.observe(container);
		onDestroy(() => resizeObserver.disconnect());

		window.addEventListener('mousemove', onSidebarResizeMove);
		window.addEventListener('mouseup', onSidebarResizeEnd);
		onDestroy(() => {
			window.removeEventListener('mousemove', onSidebarResizeMove);
			window.removeEventListener('mouseup', onSidebarResizeEnd);
		});

		map.on('click', onMapClick);
		map.on('dblclick', onMapDblClick);
		map.on('mousedown', onMapMouseDown);
		map.on('mousemove', onMapMouseMove);
		map.on('mouseup', onMapMouseUp);
		map.on('mouseleave', () => {
			lastHoverPoint = null;
			updateMapCursor();
		});
	});

	onDestroy(() => {
		fieldNotePinReady = false;
		map?.remove();
	});

	$effect(() => {
		void sidebarWidth;
		if (mapReady) requestAnimationFrame(() => map?.resize());
	});

	$effect(() => {
		if (!mapReady) return;
		void zoneDraw;
		void pendingZone;
		void addingFieldNote;
		void pendingPoint;
		void drawCoords.length;
		void cursorLngLat;
		void dragVertexIndex;
		void zoneColor;
		void selectedLayer;
		void showZonesLayer;
		void showFieldNotesLayer;

		if (zoneDraw || pendingZone) {
			map.doubleClickZoom.disable();
		} else {
			map.doubleClickZoom.enable();
		}

		updateMapCursor();

		updatePreviewColor(zoneColor);
		updateDrawPreview();
		ensureDrawPreviewOnTop();
	});

	$effect(() => {
		if (!mapReady) return;
		applyBasemapVisibility(BASE_LAYERS.osm.id, baseLayer === 'osm');
		applyBasemapVisibility(BASE_LAYERS.esri.id, baseLayer === 'esri');
	});

	$effect(() => {
		if (!mapReady || !refreshKey) return;
		void refreshKey;
		void reloadObservationZones();
		void reloadFieldNotes();
	});

	function updatePreviewColor(color) {
		if (!mapReady) return;
		if (map.getLayer('draw-preview-fill')) {
			map.setPaintProperty('draw-preview-fill', 'fill-color', color);
			map.setPaintProperty('draw-preview-line', 'line-color', color);
			map.setPaintProperty('draw-preview-dash', 'line-color', color);
			map.setPaintProperty('draw-preview-vertices', 'circle-color', color);
		}
	}

	function screenPoint(lngLat) {
		const p = map.project(lngLat);
		if (Array.isArray(p)) return { x: p[0], y: p[1] };
		return { x: p.x, y: p.y };
	}

	function findVertexIndex(e, coords) {
		for (let i = 0; i < coords.length; i++) {
			const p = screenPoint(coords[i]);
			const dx = p.x - e.point.x;
			const dy = p.y - e.point.y;
			if (Math.sqrt(dx * dx + dy * dy) <= hitTolerancePx()) return i;
		}
		return null;
	}

	function isNearPoint(e, pt) {
		const p = screenPoint(pt);
		const dx = p.x - e.point.x;
		const dy = p.y - e.point.y;
		return Math.sqrt(dx * dx + dy * dy) <= hitTolerancePx();
	}

	function activeCoords() {
		if (pendingZone?.coords) return pendingZone.coords;
		return drawCoords;
	}

	function polygonFromCoords(coords) {
		return { type: 'Polygon', coordinates: [[...coords, coords[0]]] };
	}

	function initDrawPreview() {
		map.addSource('draw-preview', {
			type: 'geojson',
			data: { type: 'FeatureCollection', features: [] }
		});
		map.addLayer({
			id: 'draw-preview-fill',
			type: 'fill',
			source: 'draw-preview',
			filter: ['==', ['get', 'kind'], 'fill'],
			paint: { 'fill-color': '#f59e0b', 'fill-opacity': 0.5 }
		});
		map.addLayer({
			id: 'draw-preview-line',
			type: 'line',
			source: 'draw-preview',
			filter: ['==', ['get', 'kind'], 'line'],
			paint: { 'line-color': '#d97706', 'line-width': LINE_WIDTH }
		});
		map.addLayer({
			id: 'draw-preview-dash',
			type: 'line',
			source: 'draw-preview',
			filter: ['==', ['get', 'kind'], 'dash'],
			paint: {
				'line-color': '#ea580c',
				'line-width': LINE_WIDTH,
				'line-dasharray': [2, 2]
			}
		});
		map.addLayer({
			id: 'draw-preview-vertices',
			type: 'circle',
			source: 'draw-preview',
			filter: ['==', ['get', 'kind'], 'vertex'],
			paint: {
				'circle-radius': VERTEX_RADIUS,
				'circle-color': '#ea580c',
				'circle-stroke-width': 2,
				'circle-stroke-color': '#ffffff'
			}
		});
		map.addLayer({
			id: 'draw-preview-field-note',
			type: 'symbol',
			source: 'draw-preview',
			filter: ['==', ['get', 'kind'], 'field-note'],
			layout: {
				'icon-image': 'field-note-pin',
				'icon-size': fieldNotePinSize(),
				'icon-anchor': 'bottom',
				'icon-allow-overlap': true
			}
		});
	}

	function updateDrawPreview() {
		if (!mapReady || !map.getSource('draw-preview')) return;
		const features = [];

		const coords = activeCoords();
		for (const c of coords) {
			features.push({
				type: 'Feature',
				properties: { kind: 'vertex' },
				geometry: { type: 'Point', coordinates: c }
			});
		}

		const drawing = zoneDraw;
		const cursor = drawing ? cursorLngLat : null;

		const ring = cursor && drawing ? [...coords, cursor] : [...coords];
		if (ring.length >= 2) {
			features.push({
				type: 'Feature',
				properties: { kind: 'line' },
				geometry: { type: 'LineString', coordinates: [...ring, ring[0]] }
			});
		}
		if (ring.length >= 3) {
			features.push({
				type: 'Feature',
				properties: { kind: 'fill' },
				geometry: { type: 'Polygon', coordinates: [[...ring, ring[0]]] }
			});
		}
		if (drawing && cursor && coords.length >= 1) {
			features.push({
				type: 'Feature',
				properties: { kind: 'dash' },
				geometry: { type: 'LineString', coordinates: [coords[coords.length - 1], cursor] }
			});
		}

		if (pendingPoint) {
			features.push({
				type: 'Feature',
				properties: { kind: 'field-note' },
				geometry: { type: 'Point', coordinates: pendingPoint }
			});
		}

		map.getSource('draw-preview').setData({
			type: 'FeatureCollection',
			features
		});
	}

	function setDrawPreviewFromState() {
		updateDrawPreview();
	}

	function finishPolygon(coords) {
		if (coords.length < 3) return;
		const ring = [...coords, coords[0]];
		pendingZone = {
			geometry: { type: 'Polygon', coordinates: [ring] },
			coords: [...coords]
		};
		zoneDraw = false;
		drawCoords = [];
		cursorLngLat = null;
		zoneDescription = '';
		status = 'Enter title and description — drag vertices to adjust';
		setDrawPreviewFromState();
	}

	function onMapMouseDown(e) {
		if (pendingZone?.coords) {
			const idx = findVertexIndex(e, pendingZone.coords);
			if (idx !== null) {
				dragVertexIndex = idx;
				return;
			}
		}
		if (zoneDraw) {
			const idx = findVertexIndex(e, drawCoords);
			if (idx !== null) dragVertexIndex = idx;
		}
	}

	function onMapClick(e) {
		if (didDrag) {
			didDrag = false;
			return;
		}

		if (!zoneDraw && !pendingZone && !addingFieldNote) {
			if (selectedLayer?.kind === 'primary' && selectedLayer.id === 'observation-zones') {
				const hit = map.queryRenderedFeatures(e.point, {
					layers: ['zones-fill', 'zones-line', 'zones-label']
				});
				if (hit.length > 0) {
					const f = hit[0];
					const id = zoneIdFromFeature(f);
					if (id) {
						editingSelectedZone = null;
						showSelectedZoneMenu = false;
						selectedZone = {
							id,
							text: String(f.properties?.text ?? ''),
							description: String(f.properties?.description ?? ''),
							color: String(f.properties?.color ?? OBSERVATION_ZONE_COLOR)
						};
						closeSelectedFieldNote();
						status = 'Observation zone selected';
						return;
					}
				}
				closeSelectedZone();
			} else if (selectedLayer?.kind === 'primary' && selectedLayer.id === 'field-notes') {
				const hit = map.queryRenderedFeatures(e.point, {
					layers: ['field-notes-point']
				});
				if (hit.length > 0) {
					const f = hit[0];
					const id = String(f.properties?.id ?? f.id ?? '');
					if (UUID_RE.test(id)) {
						showSelectedFieldNoteMenu = false;
						editingSelectedFieldNote = null;
						selectedFieldNote = {
							id,
							text: String(f.properties?.text ?? ''),
							photo_path: f.properties?.photo_path ?? null,
							audio_path: f.properties?.audio_path ?? null,
							created_at: f.properties?.created_at ?? ''
						};
					closeSelectedZone();
					status = 'Field note selected';
						return;
					}
				}
				closeSelectedFieldNote();
			}
		}

		if (addingFieldNote && !zoneDraw && !pendingZone) {
			pendingPoint = [e.lngLat.lng, e.lngLat.lat];
			setDrawPreviewFromState();
			status = 'Add text and optional media, then save';
			return;
		}

		const lngLat = [e.lngLat.lng, e.lngLat.lat];

		if (!zoneDraw) return;

		drawCoords = [...drawCoords, lngLat];
		setDrawPreviewFromState();
		status = `Polygon: ${drawCoords.length} point(s) — double-click last point to finish`;
	}

	function onMapDblClick(e) {
		e.preventDefault();
		if (zoneDraw && drawCoords.length >= 3) {
			const last = drawCoords[drawCoords.length - 1];
			if (isNearPoint(e, last)) {
				finishPolygon(drawCoords);
			}
		}
	}

	function onMapMouseMove(e) {
		const lngLat = [e.lngLat.lng, e.lngLat.lat];

		if (dragVertexIndex !== null) {
			didDrag = true;
			if (pendingZone?.coords) {
				const coords = [...pendingZone.coords];
				coords[dragVertexIndex] = lngLat;
				pendingZone = {
					...pendingZone,
					coords,
					geometry: polygonFromCoords(coords)
				};
			} else {
				const coords = [...drawCoords];
				coords[dragVertexIndex] = lngLat;
				drawCoords = coords;
			}
			setDrawPreviewFromState();
			return;
		}

		if (zoneDraw) {
			cursorLngLat = lngLat;
			setDrawPreviewFromState();
		}

		if (!dragVertexIndex && !zoneDraw) {
			lastHoverPoint = e.point;
			updateMapCursor(e.point);
		}
	}

	function onMapMouseUp() {
		dragVertexIndex = null;
	}

	function firstOverlayLayerId() {
		for (const layer of map.getStyle().layers ?? []) {
			if (
				layer.id.startsWith('cog-') ||
				layer.id.startsWith('zones-') ||
				layer.id.startsWith('field-notes-')
			) {
				return layer.id;
			}
		}
		return undefined;
	}

	function applyBasemapVisibility(layerId, visible) {
		if (!mapReady || !map.getLayer(layerId)) return;
		map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
		if (visible) {
			const before = firstOverlayLayerId();
			if (before) map.moveLayer(layerId, before);
		}
	}

	function setBaseLayer(id) {
		baseLayer = id;
		applyBasemapVisibility(BASE_LAYERS.osm.id, id === 'osm');
		applyBasemapVisibility(BASE_LAYERS.esri.id, id === 'esri');
	}

	function toggleOsm(visible) {
		if (visible) setBaseLayer('osm');
	}

	function toggleEsri(visible) {
		if (visible) setBaseLayer('esri');
	}

	function setLayerVisibility(layerId, visible) {
		if (!map.getLayer(layerId)) return;
		map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
	}

	function toggleZonesLayer(visible) {
		showZonesLayer = visible;
		for (const id of ['zones-fill', 'zones-line', 'zones-label']) {
			setLayerVisibility(id, visible);
		}
	}

	function toggleFieldNotesLayer(visible) {
		showFieldNotesLayer = visible;
		setLayerVisibility('field-notes-point', visible);
	}

	function ensureCogAboveBasemaps() {
		applyLayerStackOrder();
	}

	function applyLayerStackOrder() {
		if (!mapReady) return;
		for (const layer of cogLayers) {
			const id = `cog-${layer.id}`;
			if (map.getLayer(id)) map.moveLayer(id);
		}
		if (map.getLayer('watershed-fill')) map.moveLayer('watershed-fill');
		if (map.getLayer('watershed-line')) map.moveLayer('watershed-line');
		for (const key of primaryLayerOrder) {
			const ids =
				key === 'observation-zones'
					? ['zones-fill', 'zones-line', 'zones-label']
					: ['field-notes-point'];
			for (const id of ids) {
				if (map.getLayer(id)) map.moveLayer(id);
			}
		}
		ensureDrawPreviewOnTop();
	}

	function reorderList(list, from, to) {
		const copy = [...list];
		const [item] = copy.splice(from, 1);
		copy.splice(to, 0, item);
		return copy;
	}

	function startLayerDrag(category, index, e) {
		dragReorder = { category, index };
		e.dataTransfer.effectAllowed = 'move';
		e.dataTransfer.setData('text/plain', `${category}:${index}`);
	}

	function onLayerDragOver(e) {
		e.preventDefault();
		e.dataTransfer.dropEffect = 'move';
	}

	function onLayerDrop(category, targetIndex, e) {
		e.preventDefault();
		const { category: srcCategory, index: srcIndex } = dragReorder;
		if (srcCategory !== category || srcIndex === null || srcIndex === targetIndex) {
			endLayerDrag();
			return;
		}
		if (category === 'secondary') {
			cogLayers = reorderList(cogLayers, srcIndex, targetIndex);
		} else {
			primaryLayerOrder = reorderList(primaryLayerOrder, srcIndex, targetIndex);
		}
		endLayerDrag();
		applyLayerStackOrder();
	}

	function endLayerDrag() {
		dragReorder = { category: null, index: null };
	}

	function onSidebarResizeStart(e) {
		sidebarResizing = true;
		e.preventDefault();
	}

	function onSidebarResizeMove(e) {
		if (!sidebarResizing) return;
		sidebarWidth = Math.min(480, Math.max(200, e.clientX));
	}

	function onSidebarResizeEnd() {
		sidebarResizing = false;
	}

	function resetDrawState() {
		drawCoords = [];
		cursorLngLat = null;
		dragVertexIndex = null;
		lastTapTime = 0;
		lastTapIndex = -1;
		setDrawPreviewFromState();
	}

	function startObservationZoneDraw() {
		cancelPendingForms();
		selectLayer({ kind: 'primary', id: 'observation-zones' });
		zoneDraw = true;
		zoneColor = OBSERVATION_ZONE_COLOR;
		ensureDrawPreviewOnTop();
		updateDrawSizes();
		status = 'Click corners — double-click last point to finish';
	}

	function startFieldNoteAdd() {
		cancelPendingForms();
		selectLayer({ kind: 'primary', id: 'field-notes' });
		addingFieldNote = true;
		status = 'Click the map to place the field note';
	}

	function cancelZoneDraw() {
		zoneDraw = false;
		resetDrawState();
		if (!pendingZone) status = 'Ready';
	}

	async function loadCogLayers() {
		try {
			removeCogLayers();
			const { cog_layers } = await fetchCogLayers(watershedBounds, project.id);
			cogLayers = cog_layers;
			if (cog_layers.length === 0) {
				status = 'No COG layers configured (set COG_LAYERS in .env)';
				return;
			}
			for (const layer of cog_layers) {
				if (layer.status === 'error') {
					status = `LULC error: ${layer.error ?? 'unknown'}`;
					continue;
				}
				cogVisibility = { ...cogVisibility, [layer.id]: true };
				const sourceId = `cog-${layer.id}`;
				const tileUrl = cogTileUrl(layer.id);
				map.addSource(sourceId, {
					type: 'raster',
					tiles: [tileUrl],
					tileSize: 256,
					...(watershedBounds ? { bounds: watershedBounds } : {})
				});
				const beforeId = map.getLayer('watershed-fill') ? 'watershed-fill' : undefined;
				map.addLayer(
					{ id: sourceId, type: 'raster', source: sourceId, paint: { 'raster-opacity': 1 } },
					beforeId
				);
				ensureCogAboveBasemaps();
				ensureDrawPreviewOnTop();
			}
			fitToWatershed();
		} catch (err) {
			status = `LULC unavailable: ${err instanceof Error ? err.message : String(err)}`;
		}
	}

	function fitToWatershed() {
		if (!map || !watershedBounds) return;
		map.fitBounds(
			[
				[watershedBounds[0], watershedBounds[1]],
				[watershedBounds[2], watershedBounds[3]]
			],
			{ padding: 40, maxZoom: 14, duration: 0 }
		);
	}

	function loadWatershedBoundary() {
		if (!project?.watershed_geometry) return;
		const data = {
			type: 'FeatureCollection',
			features: [
				{
					type: 'Feature',
					properties: { name: project.watershed_name },
					geometry: project.watershed_geometry
				}
			]
		};
		if (map.getSource('watershed')) {
			map.getSource('watershed').setData(data);
		} else {
			map.addSource('watershed', { type: 'geojson', data });
			map.addLayer({
				id: 'watershed-fill',
				type: 'fill',
				source: 'watershed',
				paint: { 'fill-color': '#9ca3af', 'fill-opacity': 0.08 }
			});
		}
		if (map.getLayer('watershed-line')) map.removeLayer('watershed-line');
		map.addLayer({
			id: 'watershed-line',
			type: 'line',
			source: 'watershed',
			paint: {
				'line-color': '#6b7280',
				'line-width': 2.5,
				'line-opacity': 1
			}
		});
	}

	function addGeoJsonSource(sourceId, data, layers, promoteId) {
		if (map.getSource(sourceId)) {
			map.getSource(sourceId).setData(data);
			return;
		}
		map.addSource(sourceId, {
			type: 'geojson',
			data,
			...(promoteId ? { promoteId } : {})
		});
		for (const spec of layers) map.addLayer(spec);
		updateDrawSizes();
		ensureDrawPreviewOnTop();
	}

	function removeGeoJsonSource(sourceId, layerIds) {
		for (const layerId of layerIds) {
			if (map.getLayer(layerId)) map.removeLayer(layerId);
		}
		if (map.getSource(sourceId)) map.removeSource(sourceId);
	}

	async function reloadObservationZones() {
		if (!project?.id) return;
		const data = await fetchObservationZones(project.id);
		savedZones = data.features.map((f) => ({
			id: String(f.id ?? ''),
			text: String(f.properties?.text ?? ''),
			description: String(f.properties?.description ?? ''),
			color: String(f.properties?.color ?? OBSERVATION_ZONE_COLOR)
		}));
		const features = data.features.map((f) => {
			const id = String(f.id ?? '');
			return {
				...f,
				id,
				properties: {
					...f.properties,
					id,
					color: f.properties?.color ?? OBSERVATION_ZONE_COLOR
				}
			};
		});
		const zoneLayers = [
			{
				id: 'zones-fill',
				type: 'fill',
				source: 'zones',
				paint: {
					'fill-color': ['coalesce', ['get', 'color'], OBSERVATION_ZONE_COLOR],
					'fill-opacity': 0.4
				}
			},
			{
				id: 'zones-line',
				type: 'line',
				source: 'zones',
				paint: {
					'line-color': ['coalesce', ['get', 'color'], OBSERVATION_ZONE_COLOR],
					'line-width': LINE_WIDTH
				}
			},
			{
				id: 'zones-label',
				type: 'symbol',
				source: 'zones',
				layout: {
					'text-field': ['get', 'text'],
					'text-size': 11,
					'text-anchor': 'center',
					'text-allow-overlap': true
				},
				paint: {
					'text-color': '#ffffff',
					'text-halo-color': ['coalesce', ['get', 'color'], OBSERVATION_ZONE_COLOR],
					'text-halo-width': 8,
					'text-halo-blur': 0
				}
			}
		];
		removeGeoJsonSource('zones', ['zones-label', 'zones-line', 'zones-fill']);
		addGeoJsonSource('zones', { type: 'FeatureCollection', features }, zoneLayers, 'id');
		toggleZonesLayer(showZonesLayer);
		applyLayerStackOrder();
	}

	async function reloadFieldNotes() {
		if (!project?.id) return;
		const data = await fetchFieldNotes(project.id);
		savedFieldNotes = data.features.map((f) => ({
			id: String(f.id ?? f.properties?.id ?? ''),
			text: String(f.properties?.text ?? ''),
			photo_path: f.properties?.photo_path ?? null,
			audio_path: f.properties?.audio_path ?? null,
			created_at: String(f.properties?.created_at ?? '')
		}));
		const features = data.features.map((f) => {
			const id = String(f.id ?? f.properties?.id ?? '');
			return {
				...f,
				id,
				properties: { ...f.properties, id }
			};
		});
		await ensureFieldNotePinIcon();
		removeGeoJsonSource('field-notes', ['field-notes-point']);
		addGeoJsonSource(
			'field-notes',
			{ type: 'FeatureCollection', features },
			[
				{
					id: 'field-notes-point',
					type: 'symbol',
					source: 'field-notes',
					layout: {
						'icon-image': 'field-note-pin',
						'icon-size': fieldNotePinSize(),
						'icon-anchor': 'bottom',
						'icon-allow-overlap': true
					}
				}
			],
			'id'
		);
		toggleFieldNotesLayer(showFieldNotesLayer);
		applyLayerStackOrder();
	}

	async function saveObservationZone() {
		if (!pendingZone) return;
		savingZone = true;
		try {
			await createObservationZone(
				project.id,
				pendingZone.geometry,
				zoneText.trim(),
				zoneDescription.trim(),
				zoneColor
			);
			pendingZone = null;
			zoneText = '';
			zoneDescription = '';
			resetDrawState();
			await reloadObservationZones();
			status = 'Observation zone saved';
		} catch (err) {
			status = `Save failed: ${err instanceof Error ? err.message : String(err)}`;
		} finally {
			savingZone = false;
		}
	}

	function cancelPendingZone() {
		pendingZone = null;
		zoneText = '';
		zoneDescription = '';
		resetDrawState();
		status = 'Ready';
	}

	function startEditSelectedZone() {
		if (!selectedZone) return;
		editingSelectedZone = { ...selectedZone };
		showSelectedZoneMenu = false;
	}

	function cancelEditSelectedZone() {
		editingSelectedZone = null;
	}

	async function saveSelectedZone() {
		if (!editingSelectedZone) return;
		savingZone = true;
		try {
			const updated = await updateObservationZone(editingSelectedZone.id, {
				text: editingSelectedZone.text.trim(),
				description: editingSelectedZone.description.trim(),
				color: editingSelectedZone.color
			});
			selectedZone = {
				id: editingSelectedZone.id,
				text: String(updated.properties?.text ?? editingSelectedZone.text),
				description: String(
					updated.properties?.description ?? editingSelectedZone.description
				),
				color: String(updated.properties?.color ?? editingSelectedZone.color)
			};
			editingSelectedZone = null;
			await reloadObservationZones();
			status = 'Observation zone updated';
		} catch (err) {
			status = `Update failed: ${err instanceof Error ? err.message : String(err)}`;
		} finally {
			savingZone = false;
		}
	}

	async function deleteSelectedZone() {
		if (!selectedZone) return;
		showSelectedZoneMenu = false;
		if (!confirm('Delete this observation zone?')) return;
		try {
			await deleteObservationZone(selectedZone.id);
			closeSelectedZone();
			await reloadObservationZones();
			status = 'Observation zone deleted';
		} catch (err) {
			status = `Delete failed: ${err instanceof Error ? err.message : String(err)}`;
		}
	}

	function onFieldNotePhotoChange(e) {
		noteMediaError = '';
		const file = e.currentTarget.files?.[0];
		if (!file) {
			notePhoto = undefined;
			if (notePhotoPreview) URL.revokeObjectURL(notePhotoPreview);
			notePhotoPreview = null;
			return;
		}
		if (file.size > MAX_FIELD_NOTE_MEDIA_BYTES) {
			noteMediaError = 'Image must be 50MB or smaller';
			e.currentTarget.value = '';
			notePhoto = undefined;
			if (notePhotoPreview) URL.revokeObjectURL(notePhotoPreview);
			notePhotoPreview = null;
			return;
		}
		notePhoto = file;
		if (notePhotoPreview) URL.revokeObjectURL(notePhotoPreview);
		notePhotoPreview = file.type.startsWith('image/') ? URL.createObjectURL(file) : null;
	}

	function onFieldNoteAudioChange(e) {
		noteMediaError = '';
		const file = e.currentTarget.files?.[0];
		if (!file) {
			noteAudio = undefined;
			if (noteAudioPreview) URL.revokeObjectURL(noteAudioPreview);
			noteAudioPreview = null;
			return;
		}
		if (file.size > MAX_FIELD_NOTE_MEDIA_BYTES) {
			noteMediaError = 'Audio must be 50MB or smaller';
			e.currentTarget.value = '';
			noteAudio = undefined;
			if (noteAudioPreview) URL.revokeObjectURL(noteAudioPreview);
			noteAudioPreview = null;
			return;
		}
		noteAudio = file;
		if (noteAudioPreview) URL.revokeObjectURL(noteAudioPreview);
		noteAudioPreview = URL.createObjectURL(file);
	}

	async function submitFieldNote() {
		if (!pendingPoint) return;
		if (noteMediaError) return;
		try {
			await createFieldNote(
				project.id,
				{ type: 'Point', coordinates: pendingPoint },
				noteText,
				notePhoto,
				noteAudio
			);
			cancelPendingForms();
			addingFieldNote = false;
			await reloadFieldNotes();
			status = 'Field note saved';
		} catch (err) {
			status = String(err);
		}
	}

	function startEditSelectedFieldNote() {
		if (!selectedFieldNote) return;
		editingSelectedFieldNote = { ...selectedFieldNote };
		showSelectedFieldNoteMenu = false;
	}

	function cancelEditSelectedFieldNote() {
		editingSelectedFieldNote = null;
	}

	async function saveSelectedFieldNote() {
		if (!editingSelectedFieldNote) return;
		savingFieldNote = true;
		try {
			const updated = await updateFieldNote(editingSelectedFieldNote.id, {
				text: editingSelectedFieldNote.text.trim()
			});
			selectedFieldNote = {
				id: editingSelectedFieldNote.id,
				text: String(updated.properties?.text ?? editingSelectedFieldNote.text),
				photo_path: updated.properties?.photo_path ?? editingSelectedFieldNote.photo_path,
				audio_path: updated.properties?.audio_path ?? editingSelectedFieldNote.audio_path,
				created_at: updated.properties?.created_at ?? editingSelectedFieldNote.created_at
			};
			editingSelectedFieldNote = null;
			await reloadFieldNotes();
			status = 'Field note updated';
		} catch (err) {
			status = `Update failed: ${err instanceof Error ? err.message : String(err)}`;
		} finally {
			savingFieldNote = false;
		}
	}

	async function deleteSelectedFieldNote() {
		if (!selectedFieldNote) return;
		showSelectedFieldNoteMenu = false;
		if (!confirm('Delete this field note?')) return;
		try {
			await deleteFieldNote(selectedFieldNote.id);
			closeSelectedFieldNote();
			await reloadFieldNotes();
			status = 'Field note deleted';
		} catch (err) {
			status = `Delete failed: ${err instanceof Error ? err.message : String(err)}`;
		}
	}

	function toggleCog(id, visible) {
		cogVisibility = { ...cogVisibility, [id]: visible };
		setLayerVisibility(`cog-${id}`, visible);
	}
</script>

<div class="flex h-full min-h-0 w-full">
	<aside
		class="flex shrink-0 flex-col overflow-hidden bg-white font-body"
		style:width="{sidebarWidth}px"
	>
		<div class="border-b border-brand-navy/10 p-3">
			<h3 class="m-0 mb-2 font-headline text-xs font-semibold tracking-wide text-brand-navy/60 uppercase">
				Base layer
			</h3>
			<select
				class="w-full cursor-pointer rounded border border-brand-navy/20 bg-white px-2 py-1.5 font-body text-sm text-brand-navy"
				value={baseLayer}
				onchange={(e) => setBaseLayer(e.currentTarget.value)}
			>
				<option value="osm">OpenStreetMap</option>
				<option value="esri">ESRI Imagery</option>
			</select>
		</div>

		<div class="min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-3">
			<h3 class="m-0 mb-2 font-headline text-xs font-semibold tracking-wide text-brand-navy/60 uppercase">
				Secondary data
			</h3>
			{#each cogLayers as layer, index (layer.id)}
				<div
					class="mb-1 flex min-w-0 items-center gap-1 rounded px-1 py-1.5 text-sm"
					class:layer-row-selected={selectedLayer?.kind === 'secondary' && selectedLayer.id === layer.id}
					class:layer-row-dragging={dragReorder.category === 'secondary' && dragReorder.index === index}
					ondragover={onLayerDragOver}
					ondrop={(e) => onLayerDrop('secondary', index, e)}
				>
					<button
						type="button"
						class="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded border-0 bg-transparent p-0 text-brand-steel hover:bg-brand-sky/20 hover:text-brand-navy disabled:opacity-40"
						disabled={layer.status === 'error'}
						aria-label={(cogVisibility[layer.id] ?? true) ? 'Hide layer' : 'Show layer'}
						onclick={() => toggleCog(layer.id, !(cogVisibility[layer.id] ?? true))}
					>
						{#if cogVisibility[layer.id] ?? true}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
								<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
								<circle cx="12" cy="12" r="3" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
								<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
								<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
								<path d="M1 1l22 22" />
								<path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
							</svg>
						{/if}
					</button>
					<button
						type="button"
						class="min-w-0 flex-1 cursor-pointer truncate border-0 bg-transparent p-0 text-left text-brand-navy"
						title={layer.name}
						onclick={() => selectLayer({ kind: 'secondary', id: layer.id })}
					>
						{layer.name}
					</button>
					<div
						class="layer-drag-handle"
						draggable="true"
						role="button"
						tabindex="-1"
						aria-label="Drag to reorder layer"
						ondragstart={(e) => startLayerDrag('secondary', index, e)}
						ondragend={endLayerDrag}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="h-4 w-4" aria-hidden="true">
							<circle cx="9" cy="6" r="1.4" fill="currentColor" />
							<circle cx="15" cy="6" r="1.4" fill="currentColor" />
							<circle cx="9" cy="12" r="1.4" fill="currentColor" />
							<circle cx="15" cy="12" r="1.4" fill="currentColor" />
							<circle cx="9" cy="18" r="1.4" fill="currentColor" />
							<circle cx="15" cy="18" r="1.4" fill="currentColor" />
						</svg>
					</div>
				</div>
				{#if layer.error}
					<p class="m-0 mb-2 truncate px-2 text-xs text-red-600" title={layer.error}>{layer.error}</p>
				{/if}
			{:else}
				<p class="m-0 text-xs text-brand-steel">No secondary layers configured</p>
			{/each}

			<h3 class="m-0 mt-4 mb-2 font-headline text-xs font-semibold tracking-wide text-brand-navy/60 uppercase">
				Primary layers
			</h3>
			{#each primaryLayerOrder as layerId, index (layerId)}
				<div
					class="mb-1 flex min-w-0 items-center gap-1 rounded px-1 py-1.5 text-sm"
					class:layer-row-selected={selectedLayer?.kind === 'primary' && selectedLayer.id === layerId}
					class:layer-row-dragging={dragReorder.category === 'primary' && dragReorder.index === index}
					ondragover={onLayerDragOver}
					ondrop={(e) => onLayerDrop('primary', index, e)}
				>
					{#if layerId === 'observation-zones'}
						<button
							type="button"
							class="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded border-0 bg-transparent p-0 text-brand-steel hover:bg-brand-sky/20 hover:text-brand-navy"
							aria-label={showZonesLayer ? 'Hide layer' : 'Show layer'}
							onclick={() => toggleZonesLayer(!showZonesLayer)}
						>
							{#if showZonesLayer}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
									<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
									<circle cx="12" cy="12" r="3" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
									<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
									<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
									<path d="M1 1l22 22" />
									<path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
								</svg>
							{/if}
						</button>
						<button
							type="button"
							class="flex min-w-0 flex-1 cursor-pointer items-center gap-2 border-0 bg-transparent p-0 text-left text-brand-navy"
							onclick={() => selectLayer({ kind: 'primary', id: 'observation-zones' })}
						>
							<ObservationZoneIcon size="sm" />
							<span class="truncate">{PRIMARY_LAYER_LABELS[layerId]}</span>
						</button>
					{:else}
						<button
							type="button"
							class="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded border-0 bg-transparent p-0 text-brand-steel hover:bg-brand-sky/20 hover:text-brand-navy"
							aria-label={showFieldNotesLayer ? 'Hide layer' : 'Show layer'}
							onclick={() => toggleFieldNotesLayer(!showFieldNotesLayer)}
						>
							{#if showFieldNotesLayer}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
									<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
									<circle cx="12" cy="12" r="3" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
									<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
									<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
									<path d="M1 1l22 22" />
									<path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
								</svg>
							{/if}
						</button>
						<button
							type="button"
							class="flex min-w-0 flex-1 cursor-pointer items-center gap-2 border-0 bg-transparent p-0 text-left text-brand-navy"
							onclick={() => selectLayer({ kind: 'primary', id: 'field-notes' })}
						>
							<FieldNoteIcon size="sm" />
							<span class="truncate">{PRIMARY_LAYER_LABELS[layerId]}</span>
						</button>
					{/if}
					<div
						class="layer-drag-handle"
						draggable="true"
						role="button"
						tabindex="-1"
						aria-label="Drag to reorder layer"
						ondragstart={(e) => startLayerDrag('primary', index, e)}
						ondragend={endLayerDrag}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="h-4 w-4" aria-hidden="true">
							<circle cx="9" cy="6" r="1.4" fill="currentColor" />
							<circle cx="15" cy="6" r="1.4" fill="currentColor" />
							<circle cx="9" cy="12" r="1.4" fill="currentColor" />
							<circle cx="15" cy="12" r="1.4" fill="currentColor" />
							<circle cx="9" cy="18" r="1.4" fill="currentColor" />
							<circle cx="15" cy="18" r="1.4" fill="currentColor" />
						</svg>
					</div>
				</div>
			{/each}
		</div>
	</aside>

	<div
		class="sidebar-resize-handle"
		class:sidebar-resize-active={sidebarResizing}
		role="separator"
		aria-orientation="vertical"
		aria-label="Resize sidebar"
		onmousedown={onSidebarResizeStart}
	></div>

	<!-- Map (full width beside left panel; floating cards overlay the right side) -->
	<div class="relative h-full min-h-0 flex-1">
		<div bind:this={container} class="h-full w-full"></div>

		<div
			class="pointer-events-none absolute top-3 right-3 z-10 flex max-h-[calc(100%-3.5rem)] w-72 flex-col gap-3 overflow-y-auto"
		>
			{#if selectedLayer?.kind === 'secondary'}
				{@const layer = cogLayers.find((l) => l.id === selectedLayer.id)}
				<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
					<h3 class="m-0 mb-1 text-base font-semibold">{layer?.name ?? 'Layer'}</h3>
					<p class="m-0 mb-3 text-xs text-gray-500">LULC legend</p>
					<ul class="m-0 list-none space-y-2 p-0">
						{#each LULC_LEGEND as item}
							<li class="flex items-center gap-2 text-sm">
								<span
									class="inline-block h-4 w-4 shrink-0 rounded border border-gray-300"
									style="background-color: {item.color}"
								></span>
								<span class="text-gray-700">{item.label}</span>
							</li>
						{/each}
					</ul>
				</div>
			{:else if selectedLayer?.kind === 'primary' && selectedLayer.id === 'observation-zones'}
				<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
					<h3 class="m-0 mb-1 text-base font-semibold">Observation zones</h3>
					<p class="m-0 mb-3 text-xs text-gray-500">
						Click a zone on the map to view details, or add a new polygon.
					</p>
					<button
						type="button"
						class="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border-0 px-3 py-2.5 font-body text-sm text-white hover:opacity-90"
						style:background-color={OBSERVATION_ZONE_COLOR}
						onclick={startObservationZoneDraw}
					>
						<span class="text-lg leading-none">+</span> Add observation zone
					</button>
					{#if zoneDraw}
						<p class="m-0 mt-3 text-xs text-amber-700">
							Drawing… click corners, double-click last point to finish.
						</p>
						<button
							type="button"
							class="mt-2 cursor-pointer border-0 bg-transparent p-0 text-sm text-gray-600 underline"
							onclick={cancelZoneDraw}
						>
							Cancel drawing
						</button>
					{/if}
				</div>

				{#if pendingZone}
					<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
						<h3 class="m-0 mb-3 text-base font-semibold">New observation zone</h3>
						<label for="annot-text" class="text-sm text-gray-600">Title</label>
						<input
							id="annot-text"
							type="text"
							class="my-1.5 mb-3 box-border w-full rounded border border-gray-300 p-2 text-sm"
							bind:value={zoneText}
							placeholder="Zone title"
						/>
						<label for="annot-desc" class="text-sm text-gray-600">Description</label>
						<textarea
							id="annot-desc"
							class="my-1.5 mb-3 box-border w-full rounded border border-gray-300 p-2 text-sm"
							bind:value={zoneDescription}
							placeholder="Description…"
							rows="3"
						></textarea>
						<p class="m-0 mb-2 text-sm text-gray-600">Colour</p>
						<div class="mb-4 flex flex-wrap gap-2">
							{#each ZONE_COLORS as c}
								<button
									type="button"
									class="h-8 w-8 cursor-pointer rounded-full border-2"
									class:border-gray-900={zoneColor === c.hex}
									class:border-transparent={zoneColor !== c.hex}
									style="background-color: {c.hex}"
									title={c.label}
									aria-label={c.label}
									onclick={() => (zoneColor = c.hex)}
								></button>
							{/each}
						</div>
						<div class="flex gap-2">
							<button
								class="cursor-pointer rounded border-0 bg-brand-blue px-3 py-1.5 font-body text-sm text-white disabled:opacity-60"
								disabled={savingZone}
								onclick={saveObservationZone}
							>
								{savingZone ? 'Saving…' : 'Save'}
							</button>
							<button
								class="cursor-pointer rounded border-0 bg-brand-steel px-3 py-1.5 font-body text-sm text-white hover:bg-brand-navy"
								onclick={cancelPendingZone}
							>
								Cancel
							</button>
						</div>
					</div>
				{:else if editingSelectedZone}
					<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
						<h3 class="m-0 mb-3 text-base font-semibold">Edit observation zone</h3>
						<label for="edit-text" class="text-sm text-gray-600">Title</label>
						<input
							id="edit-text"
							type="text"
							class="my-1.5 mb-3 box-border w-full rounded border border-gray-300 p-2 text-sm"
							bind:value={editingSelectedZone.text}
						/>
						<label for="edit-desc" class="text-sm text-gray-600">Description</label>
						<textarea
							id="edit-desc"
							class="my-1.5 mb-3 box-border w-full rounded border border-gray-300 p-2 text-sm"
							bind:value={editingSelectedZone.description}
							rows="3"
						></textarea>
						<p class="m-0 mb-2 text-sm text-gray-600">Colour</p>
						<div class="mb-4 flex flex-wrap gap-2">
							{#each ZONE_COLORS as c}
								<button
									type="button"
									class="h-8 w-8 cursor-pointer rounded-full border-2"
									class:border-gray-900={editingSelectedZone.color === c.hex}
									class:border-transparent={editingSelectedZone.color !== c.hex}
									style="background-color: {c.hex}"
									title={c.label}
									onclick={() => (editingSelectedZone.color = c.hex)}
								></button>
							{/each}
						</div>
						<div class="flex gap-2">
							<button
								class="cursor-pointer rounded border-0 bg-brand-blue px-3 py-1.5 font-body text-sm text-white disabled:opacity-60"
								disabled={savingZone}
								onclick={saveSelectedZone}
							>
								Save
							</button>
							<button
								class="cursor-pointer rounded border-0 bg-brand-steel px-3 py-1.5 font-body text-sm text-white hover:bg-brand-navy"
								onclick={cancelEditSelectedZone}
							>
								Cancel
							</button>
						</div>
					</div>
				{:else if selectedZone}
					{@const zoneTitleColor = contrastTextColor(selectedZone.color)}
					<div class="pointer-events-auto overflow-hidden rounded-lg bg-white shadow-lg">
						<div
							class="flex items-center justify-between gap-2 px-4 py-3"
							style:background-color={selectedZone.color}
							style:color={zoneTitleColor}
						>
							<h3 class="m-0 min-w-0 flex-1 font-headline text-base leading-snug font-semibold">
								{selectedZone.text || 'Untitled zone'}
							</h3>
							<div class="flex shrink-0 items-center gap-1">
								<div class="relative">
									<button
										type="button"
										class="flex h-8 w-8 cursor-pointer items-center justify-center rounded border-0 bg-transparent hover:bg-black/10"
										style:color={zoneTitleColor}
										aria-label="More actions"
										onclick={() => (showSelectedZoneMenu = !showSelectedZoneMenu)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
											<circle cx="12" cy="5" r="1.5" />
											<circle cx="12" cy="12" r="1.5" />
											<circle cx="12" cy="19" r="1.5" />
										</svg>
									</button>
									{#if showSelectedZoneMenu}
										<div
											class="absolute right-0 z-20 mt-1 min-w-28 overflow-hidden rounded border border-gray-200 bg-white text-brand-navy shadow-lg"
										>
											<button
												type="button"
												class="block w-full cursor-pointer border-0 bg-white px-3 py-2 text-left text-sm hover:bg-gray-50"
												onclick={startEditSelectedZone}
											>
												Edit
											</button>
											<button
												type="button"
												class="block w-full cursor-pointer border-0 bg-white px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
												onclick={deleteSelectedZone}
											>
												Delete
											</button>
										</div>
									{/if}
								</div>
								<button
									type="button"
									class="cursor-pointer rounded border border-current/30 bg-transparent px-2 py-1 text-xs hover:bg-black/10"
									style:color={zoneTitleColor}
									onclick={closeSelectedZone}
								>
									Close
								</button>
							</div>
						</div>
						<div class="p-4">
							<p class="m-0 text-sm leading-relaxed whitespace-pre-wrap text-brand-navy">
								{selectedZone.description || '—'}
							</p>
						</div>
					</div>
				{/if}
			{:else if selectedLayer?.kind === 'primary' && selectedLayer.id === 'field-notes'}
				<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
					<h3 class="m-0 mb-1 text-base font-semibold">Field notes</h3>
					<p class="m-0 mb-3 text-xs text-gray-500">
						Click a note on the map to view details, or add a new point.
					</p>
					<button
						type="button"
						class="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border-0 px-3 py-2.5 font-body text-sm text-brand-navy hover:opacity-90"
						style:background-color={FIELD_NOTE_COLOR}
						onclick={startFieldNoteAdd}
					>
						<span class="text-lg leading-none">+</span> Add field note
					</button>
					{#if addingFieldNote && !pendingPoint}
						<p class="m-0 mt-3 text-xs text-amber-700">Click the map to place the field note.</p>
						<button
							type="button"
							class="mt-2 cursor-pointer border-0 bg-transparent p-0 text-sm text-gray-600 underline"
							onclick={cancelPendingForms}
						>
							Cancel
						</button>
					{/if}
				</div>

				{#if pendingPoint}
					<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
						<h3 class="m-0 mb-3 text-base font-semibold">New field note</h3>
						<label for="note-text" class="text-sm text-gray-600">Text</label>
						<textarea
							id="note-text"
							class="my-1.5 mb-3 box-border w-full rounded border border-gray-300 p-2 text-sm"
							bind:value={noteText}
							placeholder="Field note…"
							rows="4"
						></textarea>
						<label for="note-photo" class="text-sm text-gray-600">Photo (max 50MB)</label>
						<input
							id="note-photo"
							type="file"
							accept="image/*"
							class="my-1.5 mb-2 block w-full text-sm"
							onchange={onFieldNotePhotoChange}
						/>
						{#if notePhotoPreview}
							<img
								src={notePhotoPreview}
								alt="Preview"
								class="mb-3 max-h-40 w-full rounded border border-gray-200 object-cover"
							/>
						{:else if notePhoto}
							<p class="m-0 mb-3 text-xs text-gray-500">Photo: {notePhoto.name}</p>
						{/if}
						<label for="note-audio" class="text-sm text-gray-600">Audio (max 50MB)</label>
						<input
							id="note-audio"
							type="file"
							accept="audio/*"
							class="my-1.5 mb-2 block w-full text-sm"
							onchange={onFieldNoteAudioChange}
						/>
						{#if noteAudioPreview}
							<audio controls src={noteAudioPreview} class="mb-3 w-full"></audio>
						{:else if noteAudio}
							<p class="m-0 mb-3 text-xs text-gray-500">Audio: {noteAudio.name}</p>
						{/if}
						{#if noteMediaError}
							<p class="m-0 mb-2 text-xs text-red-600">{noteMediaError}</p>
						{/if}
						<div class="flex gap-2">
							<button
								class="cursor-pointer rounded border-0 bg-blue-600 px-3 py-1.5 text-sm text-white"
								onclick={submitFieldNote}
							>
								Save
							</button>
							<button
								class="cursor-pointer rounded border-0 bg-brand-steel px-3 py-1.5 font-body text-sm text-white hover:bg-brand-navy"
								onclick={cancelPendingForms}
							>
								Cancel
							</button>
						</div>
					</div>
				{:else if editingSelectedFieldNote}
					<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
						<h3 class="m-0 mb-3 text-base font-semibold">Edit field note</h3>
						<label for="edit-note-text" class="text-sm text-gray-600">Text</label>
						<textarea
							id="edit-note-text"
							class="my-1.5 mb-4 box-border w-full rounded border border-gray-300 p-2 text-sm"
							bind:value={editingSelectedFieldNote.text}
							rows="4"
						></textarea>
						<div class="flex gap-2">
							<button
								class="cursor-pointer rounded border-0 bg-brand-blue px-3 py-1.5 font-body text-sm text-white disabled:opacity-60"
								disabled={savingFieldNote}
								onclick={saveSelectedFieldNote}
							>
								{savingFieldNote ? 'Saving…' : 'Save'}
							</button>
							<button
								class="cursor-pointer rounded border-0 bg-brand-steel px-3 py-1.5 font-body text-sm text-white hover:bg-brand-navy"
								onclick={cancelEditSelectedFieldNote}
							>
								Cancel
							</button>
						</div>
					</div>
				{:else if selectedFieldNote}
					<div class="pointer-events-auto rounded-lg bg-white p-4 shadow-lg">
						<div class="mb-3 flex items-start justify-between gap-2">
							<h3 class="m-0 text-base font-semibold">Field note</h3>
							<div class="flex shrink-0 items-center gap-1">
								<div class="relative">
									<button
										type="button"
										class="flex h-8 w-8 cursor-pointer items-center justify-center rounded border-0 bg-transparent text-gray-600 hover:bg-gray-100"
										aria-label="More actions"
										onclick={() => (showSelectedFieldNoteMenu = !showSelectedFieldNoteMenu)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
											<circle cx="12" cy="5" r="1.5" />
											<circle cx="12" cy="12" r="1.5" />
											<circle cx="12" cy="19" r="1.5" />
										</svg>
									</button>
									{#if showSelectedFieldNoteMenu}
										<div
											class="absolute right-0 z-20 mt-1 min-w-28 overflow-hidden rounded border border-gray-200 bg-white shadow-lg"
										>
											<button
												type="button"
												class="block w-full cursor-pointer border-0 bg-white px-3 py-2 text-left text-sm hover:bg-gray-50"
												onclick={startEditSelectedFieldNote}
											>
												Edit
											</button>
											<button
												type="button"
												class="block w-full cursor-pointer border-0 bg-white px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
												onclick={deleteSelectedFieldNote}
											>
												Delete
											</button>
										</div>
									{/if}
								</div>
								<button
									type="button"
									class="cursor-pointer rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
									onclick={closeSelectedFieldNote}
								>
									Close
								</button>
							</div>
						</div>
						<div class="mb-3">
							<span class="mb-0.5 block text-xs font-semibold text-gray-500 uppercase">Text</span>
							<p class="m-0 text-sm whitespace-pre-wrap">{selectedFieldNote.text || '—'}</p>
						</div>
						{#if selectedFieldNote.photo_path}
							{@const mediaUrl = fieldNoteMediaUrl(selectedFieldNote.photo_path)}
							{#if mediaUrl && selectedFieldNote.photo_path.match(/\.(jpe?g|png|gif|webp)$/i)}
								<img
									src={mediaUrl}
									alt="Field note photo"
									class="mb-3 max-h-48 w-full rounded border border-gray-200 object-cover"
								/>
							{:else if mediaUrl}
								<a
									href={mediaUrl}
									target="_blank"
									rel="noopener noreferrer"
									class="mb-3 block text-sm text-blue-600 underline"
								>
									View photo
								</a>
							{/if}
						{/if}
						{#if selectedFieldNote.audio_path}
							{@const audioUrl = fieldNoteMediaUrl(selectedFieldNote.audio_path)}
							{#if audioUrl}
								<audio controls src={audioUrl} class="w-full"></audio>
							{/if}
						{/if}
					</div>
				{/if}
			{/if}
		</div>

		<div class="absolute bottom-2 left-2 z-10 max-w-[50%] rounded bg-white/90 px-2 py-1 text-sm shadow">
			{status}
		</div>
		<div
			class="absolute right-2 bottom-1 z-10 max-w-[45%] truncate rounded bg-white/80 px-2 py-0.5 text-[10px] text-gray-600 shadow-sm"
		>
			{activeAttribution}
		</div>
	</div>
</div>
