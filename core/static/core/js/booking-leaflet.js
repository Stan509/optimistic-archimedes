/**
 * AeroLux Select Leaflet/OpenStreetMap booking map.
 *
 * Features:
 *   - Dark tile layer (CartoDB Dark)
 *   - Draggable gold & silver markers for pickup / drop-off
 *   - OSRM driving route overlay (gold polyline)
 *   - Real driving distance from OSRM (fallback = haversine)
 *   - Distance label shown on the map
 *   - Nominatim address autocomplete with suggestions dropdown
 *   - Click on map places / moves markers
 */
(function() {
    'use strict';

    const SITE_PREFIXES = new Set(['nyc', 'dr']);
    const state = {
        map: null,
        pickupMarker: null,
        dropoffMarker: null,
        routeLayer: null,
        distanceControl: null,
        activeInput: 'pickup',
    };

    // ──────────────────────────────────────────────
    // Helpers
    // ──────────────────────────────────────────────

    function getSitePrefix() {
        const seg = window.location.pathname.split('/').filter(Boolean)[0];
        return SITE_PREFIXES.has(seg) ? `/${seg}` : '';
    }

    function field(id) { return document.getElementById(id); }

    function setField(id, value) {
        const el = field(id);
        if (el) { el.value = value; el.dispatchEvent(new Event('change', { bubbles: true })); }
    }

    function getNumber(id) {
        const v = parseFloat(field(id)?.value || '');
        return Number.isFinite(v) ? v : null;
    }

    function getMapCenter() {
        return getSitePrefix() === '/dr' ? [18.7357, -69.9509] : [40.7128, -74.0060];
    }

    function isTransfer() { return field('rad-transfer')?.checked === true; }

    function isDestToAirport() { return field('transfer_direction')?.value === 'DEST_TO_AIRPORT'; }

    // ──────────────────────────────────────────────
    // Marker helpers
    // ──────────────────────────────────────────────

    function createMarker(latLng, className, title) {
        return L.marker(latLng, {
            draggable: true,
            title: title,
            icon: L.divIcon({
                className: 'aerolux-leaflet-marker ' + className,
                html: '<span></span>',
                iconSize: [22, 22],
                iconAnchor: [11, 11],
            }),
        });
    }

    function markerTargetForInput(inputType) {
        if (inputType === 'pickup') return 'pickup';
        if (inputType === 'destination' && isTransfer()) {
            return isDestToAirport() ? 'pickup' : 'dropoff';
        }
        return 'dropoff';
    }

    function setCoordinates(target, lat, lng) {
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
        if (target === 'pickup') {
            setField('pickup_lat', lat.toFixed(6));
            setField('pickup_lng', lng.toFixed(6));
            if (state.pickupMarker) state.pickupMarker.setLatLng([lat, lng]);
        } else {
            setField('dropoff_lat', lat.toFixed(6));
            setField('dropoff_lng', lng.toFixed(6));
            if (state.dropoffMarker) state.dropoffMarker.setLatLng([lat, lng]);
        }
        // Pan map to this point
        if (state.map) state.map.setView([lat, lng], state.map.getZoom());
        updateRouteAndDistance();
    }

    // ──────────────────────────────────────────────
    // Distance / route display
    // ──────────────────────────────────────────────

    function updateDistanceStatus(text) {
        const status = field('geocode-status');
        const txt = field('geocode-status-text');
        if (status && txt) {
            status.classList.remove('hidden');
            txt.textContent = text;
        }
    }

    function haversineKm(lat1, lon1, lat2, lon2) {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
        return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
    }

    /**
     * Show a small distance label in the top-right of the map.
     */
    function setDistanceLabel(km) {
        if (!state.map) return;
        if (state.distanceControl) state.map.removeControl(state.distanceControl);
        if (!km || km <= 0) return;
        state.distanceControl = L.control({ position: 'topright' });
        state.distanceControl.onAdd = function() {
            const div = L.DomUtil.create('div', 'leaflet-bar');
            div.style.background = 'rgba(10,10,10,0.85)';
            div.style.border = '1px solid rgba(201,168,76,0.25)';
            div.style.color = '#C9A84C';
            div.style.padding = '6px 14px';
            div.style.borderRadius = '8px';
            div.style.fontSize = '13px';
            div.style.fontWeight = '700';
            div.style.letterSpacing = '0.5px';
            div.style.backdropFilter = 'blur(8px)';
            div.innerHTML = '📏 ' + km.toFixed(1) + ' km';
            return div;
        };
        state.distanceControl.addTo(state.map);
    }

    // ──────────────────────────────────────────────
    // Route drawing
    // ──────────────────────────────────────────────

    function drawRoute(latLngs) {
        if (!state.map) return;
        if (state.routeLayer) state.routeLayer.remove();
        state.routeLayer = L.polyline(latLngs, {
            color: '#C9A84C',
            weight: 4,
            opacity: 0.85,
        }).addTo(state.map);
        fitVisibleRoute();
    }

    function fitVisibleRoute() {
        if (!state.map || !state.pickupMarker || !state.dropoffMarker) return;
        const p = state.pickupMarker.getLatLng();
        const d = state.dropoffMarker.getLatLng();
        state.map.fitBounds(L.latLngBounds([p, d]), { padding: [48, 48], maxZoom: 14 });
    }

    // ──────────────────────────────────────────────
    // Core: route + distance via OSRM (free, no key)
    // ──────────────────────────────────────────────

    function updateRouteAndDistance() {
        const pLat = getNumber('pickup_lat');
        const pLng = getNumber('pickup_lng');
        const dLat = getNumber('dropoff_lat');
        const dLng = getNumber('dropoff_lng');

        if ([pLat, pLng, dLat, dLng].some(v => v === null)) {
            setDistanceLabel(null);
            return;
        }

        const fallbackKm = haversineKm(pLat, pLng, dLat, dLng);
        const fallbackLine = [[pLat, pLng], [dLat, dLng]];

        // OSRM: get driving distance + route geometry
        const url = 'https://router.project-osrm.org/route/v1/driving/'
            + pLng + ',' + pLat + ';' + dLng + ',' + dLat
            + '?overview=full&geometries=geojson';

        fetch(url)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                const coords = data?.routes?.[0]?.geometry?.coordinates;
                if (coords && coords.length) {
                    const leafletCoords = coords.map(([lng, lat]) => [lat, lng]);
                    drawRoute(leafletCoords);
                    const km = data.routes[0].distance / 1000;
                    setField('distance_km', km.toFixed(2));
                    updateDistanceStatus('🚗 Route: ' + km.toFixed(1) + ' km');
                    setDistanceLabel(km);
                } else {
                    drawRoute(fallbackLine);
                    setField('distance_km', fallbackKm.toFixed(2));
                    updateDistanceStatus('📏 Direct line: ' + fallbackKm.toFixed(1) + ' km');
                    setDistanceLabel(fallbackKm);
                }
            })
            .catch(() => {
                drawRoute(fallbackLine);
                setField('distance_km', fallbackKm.toFixed(2));
                updateDistanceStatus('📏 Direct line: ' + fallbackKm.toFixed(1) + ' km');
                setDistanceLabel(fallbackKm);
            });
    }

    // ──────────────────────────────────────────────
    // Nominatim address search + autocomplete
    // ──────────────────────────────────────────────

    function normalizePrediction(p) {
        if (p.place_id) {
            return {
                label: p.display_name,
                main: p.name || p.display_name,
                secondary: p.display_name,
                lat: Number(p.lat),
                lng: Number(p.lon),
            };
        }
        return {
            label: p.display_name,
            main: p.name || p.display_name,
            secondary: p.display_name,
            lat: Number(p.lat),
            lng: Number(p.lon),
        };
    }

    function searchNominatim(query) {
        const u = new URL('https://nominatim.openstreetmap.org/search');
        u.searchParams.set('format', 'jsonv2');
        u.searchParams.set('addressdetails', '1');
        u.searchParams.set('limit', '6');
        u.searchParams.set('q', query);
        return fetch(u.toString(), { headers: { 'Accept-Language': 'en' } })
            .then(r => r.ok ? r.json() : [])
            .then(r => r.map(normalizePrediction))
            .catch(() => []);
    }

    function hideSuggestions(input) {
        const d = field('leaflet-suggestions-' + input.id);
        if (d) { d.classList.add('hidden'); d.innerHTML = ''; }
    }

    function showSuggestions(input, inputType, suggestions) {
        let d = field('leaflet-suggestions-' + input.id);
        if (!d) {
            d = document.createElement('ul');
            d.id = 'leaflet-suggestions-' + input.id;
            d.className = 'absolute z-[9999] bg-luxe-black border border-gray-800 rounded-xl mt-1 w-full max-h-56 overflow-y-auto shadow-lg';
            input.parentElement.appendChild(d);
        }
        d.innerHTML = '';
        if (!suggestions.length) { d.classList.add('hidden'); return; }

        suggestions.forEach(s => {
            const li = document.createElement('li');
            li.className = 'px-4 py-2.5 cursor-pointer hover:bg-luxe-gold/10 text-white text-sm border-b border-gray-800 last:border-b-0 hover:text-luxe-gold transition-colors';
            // Show main name + secondary detail
            li.innerHTML = '<div class="font-medium text-xs">' + escapeHtml(s.main) + '</div>'
                + '<div class="text-[10px] text-gray-500 truncate">' + escapeHtml(s.secondary.substring(0, 60)) + '</div>';
            li.addEventListener('mousedown', function(e) {
                e.preventDefault();
                input.value = s.label;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                hideSuggestions(input);
                selectSuggestion(s, inputType);
            });
            d.appendChild(li);
        });
        d.classList.remove('hidden');
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"]/g, function(m) {
            if (m === '&') return '&';
            if (m === '<') return '<';
            if (m === '>') return '>';
            if (m === '"') return '"';
            return m;
        });
    }

    function selectSuggestion(suggestion, inputType) {
        if (!Number.isFinite(suggestion.lat) || !Number.isFinite(suggestion.lng)) return;
        const target = markerTargetForInput(inputType);
        setCoordinates(target, suggestion.lat, suggestion.lng);
        // Zoom to the selected address
        if (state.map) state.map.setView([suggestion.lat, suggestion.lng], 13);
    }

    // ──────────────────────────────────────────────
    // Wire up address inputs
    // ──────────────────────────────────────────────

    function attachAddressInput(inputElement, inputType) {
        if (!inputElement || inputElement.dataset.leafletReady === 'true') return;
        inputElement.dataset.leafletReady = 'true';

        let timeout = null;
        inputElement.addEventListener('focus', function() {
            state.activeInput = inputType;
        });
        inputElement.addEventListener('input', function() {
            clearTimeout(timeout);
            const q = this.value.trim();
            if (q.length < 3) { hideSuggestions(this); return; }
            timeout = setTimeout(async () => {
                const suggestions = await searchNominatim(q);
                showSuggestions(this, inputType, suggestions);
            }, 280);
        });
        inputElement.addEventListener('blur', function() {
            setTimeout(() => hideSuggestions(this), 200);
        });
    }

    function reverseGeocode(lat, lng, inputElement) {
        if (!inputElement) return;
        const u = new URL('https://nominatim.openstreetmap.org/reverse');
        u.searchParams.set('format', 'jsonv2');
        u.searchParams.set('lat', lat);
        u.searchParams.set('lon', lng);
        fetch(u.toString())
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d?.display_name) {
                    inputElement.value = d.display_name;
                    inputElement.dispatchEvent(new Event('input', { bubbles: true }));
                }
            })
            .catch(function() {});
    }

    // ──────────────────────────────────────────────
    // Airport selection
    // ──────────────────────────────────────────────

    function syncAirportSelection() {
        const select = field('airport_id');
        if (!select || !select.value) return;
        const opt = select.options[select.selectedIndex];
        const lat = Number(opt?.dataset?.lat);
        const lng = Number(opt?.dataset?.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        const target = isDestToAirport() ? 'dropoff' : 'pickup';
        setCoordinates(target, lat, lng);
        if (state.map) state.map.setView([lat, lng], 11);
    }

    // ──────────────────────────────────────────────
    // Initialization
    // ──────────────────────────────────────────────

    function init() {
        const mapEl = field('booking-map');
        if (!mapEl || typeof L === 'undefined' || mapEl.dataset.leafletReady === 'true') return;
        mapEl.dataset.leafletReady = 'true';
        mapEl.innerHTML = '';

        const center = getMapCenter();
        state.map = L.map(mapEl, { center: center, zoom: 11, zoomControl: true, attributionControl: true });

        // Dark tile layer (CartoDB – free, no key)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        }).addTo(state.map);

        // Create markers
        state.pickupMarker = createMarker(center, 'pickup', 'Pickup').addTo(state.map);
        state.dropoffMarker = createMarker([center[0] + 0.03, center[1] + 0.03], 'dropoff', 'Drop-off').addTo(state.map);

        // Marker drag events
        state.pickupMarker.on('dragend', function() {
            const pos = state.pickupMarker.getLatLng();
            setField('pickup_lat', pos.lat.toFixed(6));
            setField('pickup_lng', pos.lng.toFixed(6));
            reverseGeocode(pos.lat, pos.lng, field('pickup_address'));
            updateRouteAndDistance();
        });
        state.dropoffMarker.on('dragend', function() {
            const pos = state.dropoffMarker.getLatLng();
            setField('dropoff_lat', pos.lat.toFixed(6));
            setField('dropoff_lng', pos.lng.toFixed(6));
            const addrInput = isTransfer() ? field('destination_address') : field('dropoff_address');
            reverseGeocode(pos.lat, pos.lng, addrInput);
            updateRouteAndDistance();
        });

        // Map click: place / move marker
        state.map.on('click', function(e) {
            const inputType = isTransfer() ? 'destination' : state.activeInput;
            const target = markerTargetForInput(inputType);
            setCoordinates(target, e.latlng.lat, e.latlng.lng);
            const addr = target === 'pickup'
                ? field('pickup_address')
                : (isTransfer() ? field('destination_address') : field('dropoff_address'));
            reverseGeocode(e.latlng.lat, e.latlng.lng, addr);
        });

        // Wire up address autocompletes
        attachAddressInput(field('pickup_address'), 'pickup');
        attachAddressInput(field('dropoff_address'), 'dropoff');
        attachAddressInput(field('destination_address'), 'destination');

        // Airport select
        field('airport_id')?.addEventListener('change', function() {
            syncAirportSelection();
            updateRouteAndDistance();
        });

        // Direction switch: re-sync markers after DOM update
        field('btn-switch-direction')?.addEventListener('click', function() {
            window.setTimeout(function() {
                syncAirportSelection();
                // Swap coordinates in hidden fields (already done in template JS)
                updateRouteAndDistance();
            }, 0);
        });

        // Expose geocodeAddress for legacy inline callers
        window.geocodeAddress = function(query, inputType) {
            searchNominatim(query).then(function(suggestions) {
                if (suggestions.length) selectSuggestion(suggestions[0], inputType);
            });
        };

        // Initial sync
        window.setTimeout(function() {
            syncAirportSelection();
            const pLat = getNumber('pickup_lat');
            const pLng = getNumber('pickup_lng');
            const dLat = getNumber('dropoff_lat');
            const dLng = getNumber('dropoff_lng');
            if (pLat !== null && pLng !== null) state.pickupMarker.setLatLng([pLat, pLng]);
            if (dLat !== null && dLng !== null) state.dropoffMarker.setLatLng([dLat, dLng]);
            updateRouteAndDistance();
            if (state.map) state.map.invalidateSize();
        }, 300);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();