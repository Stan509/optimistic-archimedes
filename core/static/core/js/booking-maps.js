/**
 * Google Maps integration for booking form
 * Handles address autocomplete, map display, and distance calculation
 */

let map = null;
let directionsService = null;
let directionsRenderer = null;
let pickupAutocomplete = null;
let dropoffAutocomplete = null;
let googleMapsApiKey = null;
const SITE_PREFIXES = new Set(['nyc', 'dr']);

function getSitePrefix() {
    const firstSegment = window.location.pathname.split('/').filter(Boolean)[0];
    if (SITE_PREFIXES.has(firstSegment)) {
        return `/${firstSegment}`;
    }
    return '';
}

function buildSiteApiUrl(path, params = {}) {
    const prefix = window.AEROLUX_API_PREFIX || getSitePrefix();
    const url = new URL(`${prefix}${path}`, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            url.searchParams.set(key, value);
        }
    });
    return url.toString();
}

function getNumberFieldValue(id) {
    const element = document.getElementById(id);
    if (!element) return NaN;
    return parseFloat(element.value);
}

function setFieldValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.value = value;
    }
}

function hasValidCoordinates(...values) {
    return values.every(value => Number.isFinite(value));
}

// Initialize Google Maps
function initializeGoogleMaps() {
    if (window.google && google.maps && google.maps.places) {
        initializeMapAndAutocomplete();
        return;
    }

    if (document.querySelector('script[data-aerolux-google-maps="true"]')) {
        return;
    }

    // Fetch API key from backend
    fetch(buildSiteApiUrl('/api/google-maps-key/'))
        .then(response => response.json())
        .then(data => {
            googleMapsApiKey = data.api_key;
            if (googleMapsApiKey) {
                loadGoogleMapsLibraries();
            }
        })
        .catch(error => console.error('Error fetching Google Maps API key:', error));
}

// Load Google Maps libraries
function loadGoogleMapsLibraries() {
    if (window.google && google.maps && google.maps.places) {
        initializeMapAndAutocomplete();
        return;
    }

    const script = document.createElement('script');
    script.dataset.aeroluxGoogleMaps = 'true';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(googleMapsApiKey)}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = initializeMapAndAutocomplete;
    document.head.appendChild(script);
}

// Initialize map and autocomplete
function initializeMapAndAutocomplete() {
    const mapElement = document.getElementById('booking-map');

    if (mapElement && !map) {
        const defaultCenter = getSitePrefix() === '/dr'
            ? { lat: 18.7357, lng: -69.9509 }
            : { lat: 40.7128, lng: -74.0060 };

        map = new google.maps.Map(mapElement, {
            zoom: 12,
            center: defaultCenter,
            styles: getDarkMapStyles(),
            controlSize: 28,
            mapTypeControl: false,
            fullscreenControl: true,
            streetViewControl: false,
        });

        directionsService = new google.maps.DirectionsService();
        directionsRenderer = new google.maps.DirectionsRenderer({
            map: map,
            suppressPolylines: false,
            polylineOptions: {
                strokeColor: '#C9A84C',
                strokeWeight: 3,
                strokeOpacity: 0.8,
            },
        });
    }

    const attachAutocomplete = (inputElement, type) => {
        if (!inputElement || inputElement.dataset.mapsAutocompleteReady === 'true') {
            return null;
        }

        inputElement.dataset.mapsAutocompleteReady = 'true';
        const autocomplete = new google.maps.places.Autocomplete(inputElement, {
            componentRestrictions: { country: ['us', 'do'] },
            types: ['address'],
            fields: ['place_id', 'geometry', 'formatted_address', 'name'],
        });

        autocomplete.addListener('place_changed', function() {
            const place = autocomplete.getPlace();
            if (place.geometry && place.geometry.location) {
                const lat = place.geometry.location.lat();
                const lng = place.geometry.location.lng();
                if (type === 'pickup') {
                    setFieldValue('pickup_lat', lat);
                    setFieldValue('pickup_lng', lng);
                } else {
                    setFieldValue('dropoff_lat', lat);
                    setFieldValue('dropoff_lng', lng);
                }
                inputElement.value = place.formatted_address || place.name || inputElement.value;
                updateMap();
                calculateDistance();
            }
        });

        let suggestionTimeout = null;
        inputElement.addEventListener('input', function() {
            clearTimeout(suggestionTimeout);
            if (this.value.trim().length >= 2) {
                suggestionTimeout = setTimeout(() => {
                    fetchAddressSuggestions(this.value, type, this);
                }, 250);
            }
        });

        return autocomplete;
    };

    // Setup autocomplete for pickup address
    const pickupAddressInput = document.getElementById('pickup_address');
    pickupAutocomplete = attachAutocomplete(pickupAddressInput, 'pickup');

    // Setup autocomplete for destination fields. Airport transfers use
    // destination_address while point-to-point uses dropoff_address.
    const dropoffAddressInput = document.getElementById('dropoff_address');
    const destinationAddressInput = document.getElementById('destination_address');
    dropoffAutocomplete = attachAutocomplete(dropoffAddressInput, 'dropoff');
    attachAutocomplete(destinationAddressInput, 'dropoff');

    // Handle airport selection
    const airportSelect = document.getElementById('airport_id');
    if (airportSelect) {
        airportSelect.addEventListener('change', function() {
            if (this.value) {
                const selectedOption = this.options[this.selectedIndex];
                const lat = parseFloat(selectedOption.dataset.lat);
                const lng = parseFloat(selectedOption.dataset.lng);
                if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
                setFieldValue('pickup_lat', lat);
                setFieldValue('pickup_lng', lng);
                if (map) {
                    map.setCenter({ lat, lng });
                }
                updateMap();
                calculateDistance();
            }
        });
    }
}

// Update map with markers and directions
function updateMap() {
    const pickupLat = getNumberFieldValue('pickup_lat');
    const pickupLng = getNumberFieldValue('pickup_lng');
    const dropoffLat = getNumberFieldValue('dropoff_lat');
    const dropoffLng = getNumberFieldValue('dropoff_lng');

    if (hasValidCoordinates(pickupLat, pickupLng, dropoffLat, dropoffLng)) {
        const origin = { lat: pickupLat, lng: pickupLng };
        const destination = { lat: dropoffLat, lng: dropoffLng };

        if (!directionsService || !directionsRenderer) {
            calculateHaversineDistance(pickupLat, pickupLng, dropoffLat, dropoffLng);
            return;
        }

        directionsService.route({
            origin: origin,
            destination: destination,
            travelMode: google.maps.TravelMode.DRIVING,
            avoidHighways: false,
            avoidTolls: false,
        }, function(result, status) {
            if (status === google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
                const route = result.routes[0];
                if (route && route.legs[0]) {
                    const distance = route.legs[0].distance.value / 1000; // Convert to km
                    setFieldValue('distance_km', distance.toFixed(2));
                    displayDistance(distance);
                }
            } else {
                // Fallback to straight line distance
                calculateHaversineDistance(pickupLat, pickupLng, dropoffLat, dropoffLng);
            }
        });

        // Zoom to fit both points
        if (map) {
            const bounds = new google.maps.LatLngBounds();
            bounds.extend({ lat: pickupLat, lng: pickupLng });
            bounds.extend({ lat: dropoffLat, lng: dropoffLng });
            map.fitBounds(bounds);
        }
    } else if (hasValidCoordinates(pickupLat, pickupLng) && map) {
        map.setCenter({ lat: pickupLat, lng: pickupLng });
        map.setZoom(15);
    }
}

// Calculate distance via API
function calculateDistance() {
    const pickupLat = getNumberFieldValue('pickup_lat');
    const pickupLng = getNumberFieldValue('pickup_lng');
    const dropoffLat = getNumberFieldValue('dropoff_lat');
    const dropoffLng = getNumberFieldValue('dropoff_lng');

    if (!hasValidCoordinates(pickupLat, pickupLng, dropoffLat, dropoffLng)) return;

    fetch(buildSiteApiUrl('/api/calculate-distance/', {
        origin_lat: pickupLat,
        origin_lng: pickupLng,
        destination_lat: dropoffLat,
        destination_lng: dropoffLng,
    }))
        .then(response => response.json())
        .then(data => {
            if (data.distance_km) {
                setFieldValue('distance_km', data.distance_km);
                displayDistance(data.distance_km);
            }
        })
        .catch(error => console.error('Error calculating distance:', error));
}

// Calculate haversine distance (fallback)
function calculateHaversineDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;
    setFieldValue('distance_km', distance.toFixed(2));
    displayDistance(distance);
}

// Display distance info to user
function displayDistance(distance) {
    const numericDistance = Number(distance);
    if (!Number.isFinite(numericDistance)) return;

    const distanceDisplay = document.getElementById('distance-display');
    if (distanceDisplay) {
        distanceDisplay.textContent = `Distance: ${numericDistance.toFixed(2)} km`;
        distanceDisplay.classList.remove('hidden');
    }

    // Trigger pricing recalculation
    const event = new Event('change');
    const form = document.getElementById('booking-step1-form');
    if (form) {
        form.dispatchEvent(event);
    }
}

// Fetch address suggestions from Google Places API
function fetchAddressSuggestions(input, type, inputElement) {
    fetch(buildSiteApiUrl('/api/address-autocomplete/', {
        input,
        language: document.documentElement.lang || 'en',
    }))
        .then(response => response.json())
        .then(data => {
            if (data.predictions && data.predictions.length > 0) {
                showSuggestions(data.predictions, type, inputElement);
            }
        })
        .catch(error => console.error('Error fetching suggestions:', error));
}

// Display address suggestions
function showSuggestions(predictions, type, inputElement) {
    // Create suggestions dropdown
    const dropdownId = `suggestions-${type}-${inputElement.id || 'field'}`;
    let dropdown = document.getElementById(dropdownId);
    if (!dropdown) {
        dropdown = document.createElement('ul');
        dropdown.id = dropdownId;
        dropdown.className = 'absolute z-[9999] bg-luxe-black border border-gray-800 rounded-xl mt-1 w-full max-h-48 overflow-y-auto shadow-lg';
        inputElement.parentElement.appendChild(dropdown);
    } else {
        dropdown.innerHTML = '';
    }

    predictions.forEach(prediction => {
        const li = document.createElement('li');
        li.className = 'px-4 py-2 cursor-pointer hover:bg-luxe-gold/10 text-white text-sm border-b border-gray-800 last:border-b-0';
        li.textContent = prediction.description;
        li.addEventListener('click', () => {
            inputElement.value = prediction.description;
            dropdown.innerHTML = '';
            dropdown.classList.add('hidden');
            // Fetch place details to get coordinates
            fetchPlaceDetails(prediction.place_id, type);
        });
        dropdown.appendChild(li);
    });

    // Show dropdown
    dropdown.classList.remove('hidden');
}

// Fetch place details (coordinates)
function fetchPlaceDetails(placeId, type) {
    fetch(buildSiteApiUrl('/api/place-details/', { place_id: placeId }))
        .then(response => response.json())
        .then(data => {
            const latitude = Number(data.latitude);
            const longitude = Number(data.longitude);
            if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
                if (type === 'pickup') {
                    setFieldValue('pickup_lat', latitude);
                    setFieldValue('pickup_lng', longitude);
                } else if (type === 'dropoff') {
                    setFieldValue('dropoff_lat', latitude);
                    setFieldValue('dropoff_lng', longitude);
                }
                updateMap();
                calculateDistance();
            }
        })
        .catch(error => console.error('Error fetching place details:', error));
}

// Dark map styles for luxury aesthetic
function getDarkMapStyles() {
    return [
        { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
        {
            featureType: 'administrative.locality',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#d59563' }],
        },
        {
            featureType: 'poi',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#d59563' }],
        },
        {
            featureType: 'poi.park',
            elementType: 'geometry',
            stylers: [{ color: '#263c3f' }],
        },
        {
            featureType: 'poi.park',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#6b9080' }],
        },
        {
            featureType: 'road',
            elementType: 'geometry',
            stylers: [{ color: '#38414e' }],
        },
        {
            featureType: 'road',
            elementType: 'geometry.stroke',
            stylers: [{ color: '#212a37' }],
        },
        {
            featureType: 'road',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#9ca5b3' }],
        },
        {
            featureType: 'road.highway',
            elementType: 'geometry',
            stylers: [{ color: '#746855' }],
        },
        {
            featureType: 'road.highway',
            elementType: 'geometry.stroke',
            stylers: [{ color: '#1f2835' }],
        },
        {
            featureType: 'road.highway',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#f3751b' }],
        },
        {
            featureType: 'transit',
            elementType: 'geometry',
            stylers: [{ color: '#2f3948' }],
        },
        {
            featureType: 'transit.station',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#d59563' }],
        },
        {
            featureType: 'water',
            elementType: 'geometry',
            stylers: [{ color: '#17263c' }],
        },
        {
            featureType: 'water',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#515c6d' }],
        },
        {
            featureType: 'water',
            elementType: 'labels.text.stroke',
            stylers: [{ color: '#17263c' }],
        },
    ];
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeGoogleMaps);
