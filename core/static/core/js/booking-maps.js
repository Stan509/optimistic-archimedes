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

// Initialize Google Maps
function initializeGoogleMaps() {
    // Fetch API key from backend
    fetch('/api/google-maps-key/')
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
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${googleMapsApiKey}&libraries=places,routes`;
    script.async = true;
    script.defer = true;
    script.onload = initializeMapAndAutocomplete;
    document.head.appendChild(script);
}

// Initialize map and autocomplete
function initializeMapAndAutocomplete() {
    const mapElement = document.getElementById('booking-map');
    if (!mapElement) return;

    // Initialize map
    const defaultCenter = { lat: 40.7128, lng: -74.0060 }; // NYC default
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

    // Setup autocomplete for pickup address
    const pickupAddressInput = document.getElementById('pickup_address');
    if (pickupAddressInput) {
        pickupAutocomplete = new google.maps.places.Autocomplete(pickupAddressInput, {
            componentRestrictions: { country: ['us', 'do'] }, // USA and Dominican Republic
            types: ['address'],
            fields: ['place_id', 'geometry', 'formatted_address', 'name'],
        });

        pickupAutocomplete.addListener('place_changed', function() {
            const place = pickupAutocomplete.getPlace();
            if (place.geometry) {
                const lat = place.geometry.location.lat();
                const lng = place.geometry.location.lng();
                document.getElementById('pickup_lat').value = lat;
                document.getElementById('pickup_lng').value = lng;
                pickupAddressInput.value = place.formatted_address;
                updateMap();
                calculateDistance();
            }
        });

        // Autocomplete suggestions on input
        pickupAddressInput.addEventListener('input', function() {
            if (this.value.length >= 2) {
                fetchAddressSuggestions(this.value, 'pickup', this);
            }
        });
    }

    // Setup autocomplete for dropoff address
    const dropoffAddressInput = document.getElementById('dropoff_address');
    const destinationAddressInput = document.getElementById('destination_address');
    const activeDropoffInput = dropoffAddressInput || destinationAddressInput;

    if (activeDropoffInput) {
        dropoffAutocomplete = new google.maps.places.Autocomplete(activeDropoffInput, {
            componentRestrictions: { country: ['us', 'do'] },
            types: ['address'],
            fields: ['place_id', 'geometry', 'formatted_address', 'name'],
        });

        dropoffAutocomplete.addListener('place_changed', function() {
            const place = dropoffAutocomplete.getPlace();
            if (place.geometry) {
                const lat = place.geometry.location.lat();
                const lng = place.geometry.location.lng();
                document.getElementById('dropoff_lat').value = lat;
                document.getElementById('dropoff_lng').value = lng;
                activeDropoffInput.value = place.formatted_address;
                updateMap();
                calculateDistance();
            }
        });

        activeDropoffInput.addEventListener('input', function() {
            if (this.value.length >= 2) {
                fetchAddressSuggestions(this.value, 'dropoff', this);
            }
        });
    }

    // Handle airport selection
    const airportSelect = document.getElementById('airport_id');
    if (airportSelect) {
        airportSelect.addEventListener('change', function() {
            if (this.value) {
                const selectedOption = this.options[this.selectedIndex];
                const lat = parseFloat(selectedOption.dataset.lat);
                const lng = parseFloat(selectedOption.dataset.lng);
                document.getElementById('pickup_lat').value = lat;
                document.getElementById('pickup_lng').value = lng;
                map.setCenter({ lat, lng });
                updateMap();
                calculateDistance();
            }
        });
    }
}

// Update map with markers and directions
function updateMap() {
    const pickupLat = parseFloat(document.getElementById('pickup_lat').value);
    const pickupLng = parseFloat(document.getElementById('pickup_lng').value);
    const dropoffLat = parseFloat(document.getElementById('dropoff_lat').value);
    const dropoffLng = parseFloat(document.getElementById('dropoff_lng').value);

    if (pickupLat && pickupLng && dropoffLat && dropoffLng) {
        const origin = { lat: pickupLat, lng: pickupLng };
        const destination = { lat: dropoffLat, lng: dropoffLng };

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
                    document.getElementById('distance_km').value = distance.toFixed(2);
                    displayDistance(distance);
                }
            } else {
                // Fallback to straight line distance
                calculateHaversineDistance(pickupLat, pickupLng, dropoffLat, dropoffLng);
            }
        });

        // Zoom to fit both points
        const bounds = new google.maps.LatLngBounds();
        bounds.extend({ lat: pickupLat, lng: pickupLng });
        bounds.extend({ lat: dropoffLat, lng: dropoffLng });
        map.fitBounds(bounds);
    } else if (pickupLat && pickupLng) {
        map.setCenter({ lat: pickupLat, lng: pickupLng });
        map.setZoom(15);
    }
}

// Calculate distance via API
function calculateDistance() {
    const pickupLat = parseFloat(document.getElementById('pickup_lat').value);
    const pickupLng = parseFloat(document.getElementById('pickup_lng').value);
    const dropoffLat = parseFloat(document.getElementById('dropoff_lat').value);
    const dropoffLng = parseFloat(document.getElementById('dropoff_lng').value);

    if (!pickupLat || !pickupLng || !dropoffLat || !dropoffLng) return;

    fetch(`/api/calculate-distance/?origin_lat=${pickupLat}&origin_lng=${pickupLng}&destination_lat=${dropoffLat}&destination_lng=${dropoffLng}`)
        .then(response => response.json())
        .then(data => {
            if (data.distance_km) {
                document.getElementById('distance_km').value = data.distance_km;
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
    document.getElementById('distance_km').value = distance.toFixed(2);
    displayDistance(distance);
}

// Display distance info to user
function displayDistance(distance) {
    const distanceDisplay = document.getElementById('distance-display');
    if (distanceDisplay) {
        distanceDisplay.textContent = `Distance: ${distance.toFixed(2)} km`;
        distanceDisplay.classList.remove('hidden');
    }

    // Trigger pricing recalculation
    const event = new Event('change');
    document.getElementById('booking-step1-form').dispatchEvent(event);
}

// Fetch address suggestions from Google Places API
function fetchAddressSuggestions(input, type, inputElement) {
    fetch(`/api/address-autocomplete/?input=${encodeURIComponent(input)}&language=en`)
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
    let dropdown = document.getElementById(`suggestions-${type}`);
    if (!dropdown) {
        dropdown = document.createElement('ul');
        dropdown.id = `suggestions-${type}`;
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
    fetch(`/api/place-details/?place_id=${encodeURIComponent(placeId)}`)
        .then(response => response.json())
        .then(data => {
            if (data.latitude && data.longitude) {
                if (type === 'pickup') {
                    document.getElementById('pickup_lat').value = data.latitude;
                    document.getElementById('pickup_lng').value = data.longitude;
                } else if (type === 'dropoff') {
                    document.getElementById('dropoff_lat').value = data.latitude;
                    document.getElementById('dropoff_lng').value = data.longitude;
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
