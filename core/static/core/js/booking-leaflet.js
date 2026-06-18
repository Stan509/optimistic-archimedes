/**
 * Leaflet/OpenStreetMap booking map.
 * Used instead of Google Maps JavaScript so Google auth/billing errors never
 * show an overlay inside the booking form.
 */
(function() {
    const SITE_PREFIXES = new Set(['nyc', 'dr']);
    const state = {
        map: null,
        pickupMarker: null,
        dropoffMarker: null,
        routeLayer: null,
        activeInput: 'pickup',
    };

    function getSitePrefix() {
        const firstSegment = window.location.pathname.split('/').filter(Boolean)[0];
        return SITE_PREFIXES.has(firstSegment) ? `/${firstSegment}` : '';
    }

    function buildSiteApiUrl(path, params = {}) {
        const url = new URL(`${getSitePrefix()}${path}`, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                url.searchParams.set(key, value);
            }
        });
        return url.toString();
    }

    function field(id) {
        return document.getElementById(id);
    }

    function setField(id, value) {
        const element = field(id);
        if (element) {
            element.value = value;
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function getNumber(id) {
        const value = parseFloat(field(id)?.value || '');
        return Number.isFinite(value) ? value : null;
    }

    function getMapCenter() {
        return getSitePrefix() === '/dr'
            ? [18.7357, -69.9509]
            : [40.7128, -74.0060];
    }

    function createMarker(latLng, className, title) {
        return L.marker(latLng, {
            draggable: true,
            title,
            icon: L.divIcon({
                className: `aerolux-leaflet-marker ${className}`,
                html: '<span></span>',
                iconSize: [22, 22],
                iconAnchor: [11, 11],
            }),
        });
    }

    function markerTargetForInput(inputType) {
        if (inputType === 'pickup') return 'pickup';
        if (inputType === 'destination' && field('rad-transfer')?.checked) {
            return field('transfer_direction')?.value === 'DEST_TO_AIRPORT' ? 'pickup' : 'dropoff';
        }
        return 'dropoff';
    }

    function setCoordinates(target, lat, lng) {
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        if (target === 'pickup') {
            setField('pickup_lat', lat.toFixed(6));
            setField('pickup_lng', lng.toFixed(6));
            state.pickupMarker?.setLatLng([lat, lng]);
        } else {
            setField('dropoff_lat', lat.toFixed(6));
            setField('dropoff_lng', lng.toFixed(6));
            state.dropoffMarker?.setLatLng([lat, lng]);
        }

        fitVisibleRoute();
        calculateRoute();
    }

    function updateDistanceStatus(text) {
        const status = field('geocode-status');
        const statusText = field('geocode-status-text');
        if (status && statusText) {
            status.classList.remove('hidden');
            statusText.textContent = text;
        }
    }

    function haversineKm(lat1, lon1, lat2, lon2) {
        const radiusKm = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
        return radiusKm * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
    }

    function drawRoute(latLngs) {
        if (!state.map) return;
        if (state.routeLayer) {
            state.routeLayer.remove();
        }
        state.routeLayer = L.polyline(latLngs, {
            color: '#C9A84C',
            weight: 4,
            opacity: 0.85,
        }).addTo(state.map);
        fitVisibleRoute();
    }

    function fitVisibleRoute() {
        if (!state.map || !state.pickupMarker || !state.dropoffMarker) return;
        const pickup = state.pickupMarker.getLatLng();
        const dropoff = state.dropoffMarker.getLatLng();
        const bounds = L.latLngBounds([pickup, dropoff]);
        state.map.fitBounds(bounds, { padding: [48, 48], maxZoom: 14 });
    }

    function calculateRoute() {
        const pickupLat = getNumber('pickup_lat');
        const pickupLng = getNumber('pickup_lng');
        const dropoffLat = getNumber('dropoff_lat');
        const dropoffLng = getNumber('dropoff_lng');
        if ([pickupLat, pickupLng, dropoffLat, dropoffLng].some(value => value === null)) {
            return;
        }

        const fallbackKm = haversineKm(pickupLat, pickupLng, dropoffLat, dropoffLng);
        const fallbackLine = [[pickupLat, pickupLng], [dropoffLat, dropoffLng]];

        fetch(buildSiteApiUrl('/api/calculate-distance/', {
            origin_lat: pickupLat,
            origin_lng: pickupLng,
            destination_lat: dropoffLat,
            destination_lng: dropoffLng,
        }))
            .then(response => response.ok ? response.json() : null)
            .then(data => {
                const distanceKm = Number(data?.distance_km || fallbackKm);
                setField('distance_km', distanceKm.toFixed(2));
                updateDistanceStatus(`Route distance: ${distanceKm.toFixed(1)} km`);
            })
            .catch(() => {
                setField('distance_km', fallbackKm.toFixed(2));
                updateDistanceStatus(`Direct line: ${fallbackKm.toFixed(1)} km`);
            });

        fetch(`https://router.project-osrm.org/route/v1/driving/${pickupLng},${pickupLat};${dropoffLng},${dropoffLat}?overview=full&geometries=geojson`)
            .then(response => response.ok ? response.json() : null)
            .then(data => {
                const coordinates = data?.routes?.[0]?.geometry?.coordinates;
                if (!coordinates || !coordinates.length) {
                    drawRoute(fallbackLine);
                    return;
                }
                drawRoute(coordinates.map(([lng, lat]) => [lat, lng]));
            })
            .catch(() => drawRoute(fallbackLine));
    }

    function normalizePrediction(prediction) {
        if (prediction.place_id) {
            return {
                label: prediction.description,
                main: prediction.main_text || prediction.description,
                secondary: prediction.secondary_text || '',
                placeId: prediction.place_id,
            };
        }
        return {
            label: prediction.display_name,
            main: prediction.name || prediction.display_name,
            secondary: prediction.display_name,
            lat: Number(prediction.lat),
            lng: Number(prediction.lon),
        };
    }

    function searchOpenStreetMap(query) {
        const url = new URL('https://nominatim.openstreetmap.org/search');
        url.searchParams.set('format', 'jsonv2');
        url.searchParams.set('addressdetails', '1');
        url.searchParams.set('limit', '6');
        url.searchParams.set('q', query);
        return fetch(url.toString())
            .then(response => response.ok ? response.json() : [])
            .then(results => results.map(normalizePrediction))
            .catch(() => []);
    }

    function hideSuggestions(inputElement) {
        const dropdown = field(`leaflet-suggestions-${inputElement.id}`);
        if (dropdown) {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
        }
    }

    function showSuggestions(inputElement, inputType, suggestions) {
        let dropdown = field(`leaflet-suggestions-${inputElement.id}`);
        if (!dropdown) {
            dropdown = document.createElement('ul');
            dropdown.id = `leaflet-suggestions-${inputElement.id}`;
            dropdown.className = 'absolute z-[9999] bg-luxe-black border border-gray-800 rounded-xl mt-1 w-full max-h-56 overflow-y-auto shadow-lg';
            inputElement.parentElement.appendChild(dropdown);
        }

        dropdown.innerHTML = '';
        if (!suggestions.length) {
            dropdown.classList.add('hidden');
            return;
        }

        suggestions.forEach(suggestion => {
            const li = document.createElement('li');
            li.className = 'px-4 py-2 cursor-pointer hover:bg-luxe-gold/10 text-white text-sm border-b border-gray-800 last:border-b-0';
            li.textContent = suggestion.label;
            li.addEventListener('mousedown', event => {
                event.preventDefault();
                inputElement.value = suggestion.label;
                inputElement.dispatchEvent(new Event('input', { bubbles: true }));
                hideSuggestions(inputElement);
                selectSuggestion(suggestion, inputType);
            });
            dropdown.appendChild(li);
        });
        dropdown.classList.remove('hidden');
    }

    function selectSuggestion(suggestion, inputType) {
        const target = markerTargetForInput(inputType);
        if (Number.isFinite(suggestion.lat) && Number.isFinite(suggestion.lng)) {
            setCoordinates(target, suggestion.lat, suggestion.lng);
        }
    }

    function attachAddressInput(inputElement, inputType) {
        if (!inputElement || inputElement.dataset.leafletAutocompleteReady === 'true') return;
        inputElement.dataset.leafletAutocompleteReady = 'true';

        let timeout = null;
        inputElement.addEventListener('focus', () => {
            state.activeInput = inputType;
        });
        inputElement.addEventListener('input', () => {
            clearTimeout(timeout);
            const query = inputElement.value.trim();
            if (query.length < 3) {
                hideSuggestions(inputElement);
                return;
            }
            timeout = setTimeout(async () => {
                let suggestions = await searchOpenStreetMap(query);
                showSuggestions(inputElement, inputType, suggestions);
            }, 250);
        });
        inputElement.addEventListener('blur', () => {
            setTimeout(() => hideSuggestions(inputElement), 180);
        });
    }

    function reverseGeocode(lat, lng, inputElement) {
        if (!inputElement) return;
        const url = new URL('https://nominatim.openstreetmap.org/reverse');
        url.searchParams.set('format', 'jsonv2');
        url.searchParams.set('lat', lat);
        url.searchParams.set('lon', lng);
        fetch(url.toString())
            .then(response => response.ok ? response.json() : null)
            .then(data => {
                if (data?.display_name) {
                    inputElement.value = data.display_name;
                    inputElement.dispatchEvent(new Event('input', { bubbles: true }));
                }
            })
            .catch(() => {});
    }

    function syncAirportSelection() {
        const airportSelect = field('airport_id');
        if (!airportSelect || !airportSelect.value) return;
        const selected = airportSelect.options[airportSelect.selectedIndex];
        const lat = Number(selected?.dataset.lat);
        const lng = Number(selected?.dataset.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        const target = field('transfer_direction')?.value === 'DEST_TO_AIRPORT' ? 'dropoff' : 'pickup';
        setCoordinates(target, lat, lng);
        state.map?.setView([lat, lng], 11);
    }

    function syncMarkersFromHiddenFields() {
        const pickupLat = getNumber('pickup_lat');
        const pickupLng = getNumber('pickup_lng');
        const dropoffLat = getNumber('dropoff_lat');
        const dropoffLng = getNumber('dropoff_lng');
        if (pickupLat !== null && pickupLng !== null) {
            state.pickupMarker?.setLatLng([pickupLat, pickupLng]);
        }
        if (dropoffLat !== null && dropoffLng !== null) {
            state.dropoffMarker?.setLatLng([dropoffLat, dropoffLng]);
        }
        calculateRoute();
    }

    function init() {
        const mapElement = field('booking-map');
        if (!mapElement || typeof L === 'undefined' || mapElement.dataset.leafletReady === 'true') return;
        mapElement.dataset.leafletReady = 'true';
        mapElement.innerHTML = '';

        const center = getMapCenter();
        state.map = L.map(mapElement, {
            center,
            zoom: 11,
            zoomControl: true,
            attributionControl: true,
        });
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        }).addTo(state.map);

        state.pickupMarker = createMarker(center, 'pickup', 'Pickup point').addTo(state.map);
        state.dropoffMarker = createMarker([center[0] + 0.03, center[1] + 0.03], 'dropoff', 'Drop-off point').addTo(state.map);

        state.pickupMarker.on('dragend', () => {
            const pos = state.pickupMarker.getLatLng();
            setCoordinates('pickup', pos.lat, pos.lng);
            reverseGeocode(pos.lat, pos.lng, field('pickup_address'));
        });
        state.dropoffMarker.on('dragend', () => {
            const pos = state.dropoffMarker.getLatLng();
            setCoordinates('dropoff', pos.lat, pos.lng);
            reverseGeocode(pos.lat, pos.lng, field('rad-transfer')?.checked ? field('destination_address') : field('dropoff_address'));
        });

        state.map.on('click', event => {
            const inputType = field('rad-transfer')?.checked ? 'destination' : state.activeInput;
            const target = markerTargetForInput(inputType);
            setCoordinates(target, event.latlng.lat, event.latlng.lng);
            const inputElement = target === 'pickup'
                ? field('pickup_address')
                : (field('rad-transfer')?.checked ? field('destination_address') : field('dropoff_address'));
            reverseGeocode(event.latlng.lat, event.latlng.lng, inputElement);
        });

        attachAddressInput(field('pickup_address'), 'pickup');
        attachAddressInput(field('dropoff_address'), 'dropoff');
        attachAddressInput(field('destination_address'), 'destination');

        field('airport_id')?.addEventListener('change', syncAirportSelection);
        field('btn-switch-direction')?.addEventListener('click', () => {
            window.setTimeout(() => {
                syncAirportSelection();
                syncMarkersFromHiddenFields();
            }, 0);
        });

        window.geocodeAddress = function(query, inputType) {
            searchOpenStreetMap(query)
                .then(suggestions => {
                    if (suggestions.length) {
                        selectSuggestion(suggestions[0], inputType);
                    }
                });
        };

        window.setTimeout(() => {
            syncAirportSelection();
            syncMarkersFromHiddenFields();
            state.map.invalidateSize();
        }, 250);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
