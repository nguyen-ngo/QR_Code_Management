/**
 * QR Code Destination Page JavaScript - Complete with Geolocation
 * Handles staff check-in functionality and form interactions
 */

// Global variables
let isSubmitting = false;
let currentTime = new Date();

// NEW: Geolocation variables
let userLocation = {
    latitude: null,
    longitude: null,
    accuracy: null,
    altitude: null,
    timestamp: null,
    source: 'manual',
    address: null
};
let locationRequestActive = false;
let locationWatchId = null;

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('QR Destination page initialized with geolocation');
    
    initializePage();
    setupEventListeners();
    startTimeUpdater();
    
    // NEW: Initialize geolocation
    initializeGeolocation();
});

function initializePage() {
    // Focus on employee ID input
    const employeeInput = document.getElementById('employee_id');
    if (employeeInput) {
        employeeInput.focus();
    }
    
    // Initialize current time display
    updateCurrentTime();
    
    // Add page load animation
    document.body.classList.add('page-loaded');
}

function setupEventListeners() {
    const form = document.getElementById('checkinForm');
    const employeeInput = document.getElementById('employee_id');
    
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    if (employeeInput) {
        // Real-time input validation
        employeeInput.addEventListener('input', handleInputChange);
        employeeInput.addEventListener('blur', validateEmployeeId);
        employeeInput.addEventListener('keypress', handleKeyPress);
        
        // Auto-uppercase input
        employeeInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    }
    
    // Handle page visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
}

// Initialize geolocation functionality
function initializeGeolocation() {
    console.log('📍 Initializing geolocation system...');
    
    if (!navigator.geolocation) {
        console.log('⚠️ Geolocation not supported by this browser');
        showLocationStatus('error', 'Location services not supported');
        return;
    }
    
    console.log('✅ Geolocation API available');
    
    // Request location immediately
    requestUserLocation();
    
    // Set up continuous watching for better accuracy
    if ('permissions' in navigator) {
        navigator.permissions.query({ name: 'geolocation' }).then(function(result) {
            console.log('📍 Geolocation permission status:', result.state);
            
            if (result.state === 'granted') {
                startLocationWatching();
            }
            
            result.onchange = function() {
                console.log('📍 Geolocation permission changed to:', result.state);
                if (result.state === 'granted') {
                    requestUserLocation();
                    startLocationWatching();
                } else {
                    stopLocationWatching();
                }
            };
        });
    }
}

// NEW: Check location permissions
function checkLocationPermission() {
    if (navigator.permissions) {
        navigator.permissions.query({name: 'geolocation'}).then(function(result) {
            console.log('🔐 Location permission status:', result.state);
            
            if (result.state === 'granted') {
                console.log('✅ Location permission granted');
            } else if (result.state === 'prompt') {
                console.log('❓ Location permission will be requested');
            } else if (result.state === 'denied') {
                console.log('❌ Location permission denied');
                showLocationStatus('error', 'Location permission denied - enable in browser settings');
            }
        }).catch(function(error) {
            console.log('⚠️ Permission query failed:', error);
        });
    }
}

// Request user's current location
function requestUserLocation() {
    if (locationRequestActive) {
        console.log('⏭️ Location request already active');
        return;
    }
    
    locationRequestActive = true;
    showLocationStatus('loading', 'Getting your location...');
    
    const options = {
        enableHighAccuracy: true,    // Use GPS for better accuracy
        timeout: 15000,              // Wait up to 15 seconds
        maximumAge: 300000           // Accept cached location up to 5 minutes old
    };
    
    console.log('📡 Requesting location with options:', options);
    
    navigator.geolocation.getCurrentPosition(
        handleLocationSuccess,
        handleLocationError,
        options
    );
    
    // Set backup timeout
    setTimeout(() => {
        if (locationRequestActive && !userLocation.latitude) {
            console.log('⏰ Location request backup timeout');
            handleLocationError({ code: 3, message: 'Request timed out' });
        }
    }, 16000);
}

// Ensure location form fields exist
function ensureLocationFormFields() {
    const form = document.getElementById('checkinForm');
    if (!form) {
        console.log('⚠️ Check-in form not found');
        return;
    }
    
    const locationFields = ['latitude', 'longitude', 'accuracy', 'altitude', 'location_source', 'address'];
    
    locationFields.forEach(fieldName => {
        if (!document.getElementById(fieldName)) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.id = fieldName;
            input.name = fieldName;
            input.value = '';
            form.appendChild(input);
            console.log(`✅ Created hidden field: ${fieldName}`);
        }
    });
}

// Handle successful location retrieval
function handleLocationSuccess(position) {
    locationRequestActive = false;
    
    const coords = position.coords;
    console.log('✅ Location obtained:', {
        latitude: coords.latitude,
        longitude: coords.longitude,
        accuracy: coords.accuracy,
        altitude: coords.altitude,
        timestamp: position.timestamp
    });
    
    // Validate coordinates
    if (!coords.latitude || !coords.longitude) {
        console.log('⚠️ Invalid coordinates received');
        handleLocationError({ code: 2, message: 'Invalid coordinates' });
        return;
    }
    
    // Store location data with validation
    userLocation = {
        latitude: Number(coords.latitude).toFixed(6),  // Limit precision
        longitude: Number(coords.longitude).toFixed(6),
        accuracy: coords.accuracy ? Math.round(coords.accuracy) : null,
        altitude: coords.altitude ? Math.round(coords.altitude) : null,
        timestamp: position.timestamp,
        source: 'gps',
        address: null
    };
    
    console.log('💾 Stored location data:', userLocation);
    
    // Update form fields immediately
    updateLocationFormFields();
    
    // Update display
    updateLocationDisplay();
    
    // Show success status
    const accuracyText = coords.accuracy ? `±${Math.round(coords.accuracy)}m` : 'unknown';
    showLocationStatus('success', `Location captured (${accuracyText} accuracy)`);
    
    // Try to get address
    reverseGeocodeLocation(coords.latitude, coords.longitude);
}

// Handle location errors
function handleLocationError(error) {
    locationRequestActive = false;
    
    let message = 'Unable to get location';
    
    console.log('❌ Location error:', error);
    
    switch(error.code) {
        case error.PERMISSION_DENIED:
            message = 'Location access denied - please enable in browser settings';
            break;
        case error.POSITION_UNAVAILABLE:
            message = 'Location unavailable - GPS signal weak';
            break;
        case error.TIMEOUT:
            message = 'Location request timed out';
            break;
        default:
            message = 'Location error occurred';
    }
    
    showLocationStatus('error', `${message} - check-in will continue without location`);
    userLocation.source = 'manual';
    updateLocationFormFields();
}

// Enhanced form initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 QR Destination page initialized with enhanced location tracking');
    
    // Initialize the page
    initializePage();
    setupEventListeners();
    startTimeUpdater();
    
    // Initialize geolocation
    initializeGeolocation();
    
    // Add hidden form fields for location data
    ensureLocationFormFields();
});

// Start watching location for continuous updates
function startLocationWatching() {
    if (locationWatchId !== null) {
        console.log('👁️ Already watching location');
        return;
    }
    
    console.log('👁️ Starting location watching for better accuracy...');
    
    const options = {
        enableHighAccuracy: true,
        timeout: 30000,
        maximumAge: 60000
    };
    
    locationWatchId = navigator.geolocation.watchPosition(
        function(position) {
            // Only update if accuracy is better
            if (!userLocation.accuracy || position.coords.accuracy < userLocation.accuracy) {
                console.log('📍 Location updated with better accuracy:', position.coords.accuracy);
                handleLocationSuccess(position);
            }
        },
        function(error) {
            console.log('⚠️ Location watch error:', error);
        },
        options
    );
}

// NEW: Stop watching location
function stopLocationWatching() {
    if (locationWatchId !== null) {
        navigator.geolocation.clearWatch(locationWatchId);
        locationWatchId = null;
        console.log('⏹️ Stopped watching location');
    }
}

// Update form fields with location data
function updateLocationFormFields() {
    const fields = {
        'latitude': userLocation.latitude || '',
        'longitude': userLocation.longitude || '',
        'accuracy': userLocation.accuracy || '',
        'altitude': userLocation.altitude || '',
        'location_source': userLocation.source || 'manual',  // FIXED: was 'locationSource'
        'address': userLocation.address || ''
    };
    
    // Update hidden form fields
    Object.keys(fields).forEach(fieldId => {
        let field = document.getElementById(fieldId);
        if (!field) {
            // Create hidden input if it doesn't exist
            field = document.createElement('input');
            field.type = 'hidden';
            field.id = fieldId;
            field.name = fieldId;
            document.getElementById('checkinForm').appendChild(field);
        }
        field.value = fields[fieldId];
    });
    
    console.log('📝 Updated form fields with location data:', fields);
}

// NEW: Update location display
function updateLocationDisplay() {
    if (userLocation.latitude && userLocation.longitude) {
        const elements = {
            'displayLatitude': userLocation.latitude.toFixed(6),
            'displayLongitude': userLocation.longitude.toFixed(6),
            'displayAccuracy': userLocation.accuracy ? `±${Math.round(userLocation.accuracy)}m` : 'Unknown',
            'displayAddress': userLocation.address || 'Loading...'
        };
        
        Object.keys(elements).forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = elements[elementId];
            }
        });
    }
}

// NEW: Reverse geocode coordinates to get address
function reverseGeocodeLocation(lat, lng) {
    console.log('🏠 Getting address from coordinates...');
    
    // Try multiple geocoding services for better reliability
    const services = [
        {
            name: 'BigDataCloud',
            url: `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`,
            parser: (data) => data.locality || data.city || data.neighbourhood || ''
        },
        {
            name: 'OpenStreetMap',
            url: `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1`,
            parser: (data) => data.display_name ? data.display_name.split(',')[0] : ''
        }
    ];
    
    tryGeocodingService(0, services);
}

function tryGeocodingService(index, services) {
    if (index >= services.length) {
        console.log('⚠️ All geocoding services failed');
        const displayAddress = document.getElementById('displayAddress');
        if (displayAddress) {
            displayAddress.textContent = 'Address not available';
        }
        return;
    }
    
    const service = services[index];
    
    fetch(service.url)
        .then(response => response.json())
        .then(data => {
            const address = service.parser(data);
            
            if (address) {
                userLocation.address = address;
                document.getElementById('address').value = address;
                
                const displayAddress = document.getElementById('displayAddress');
                if (displayAddress) {
                    displayAddress.textContent = address;
                }
                
                console.log(`🏠 Address found using ${service.name}:`, address);
                return;
            }
            
            // Try next service
            tryGeocodingService(index + 1, services);
        })
        .catch(error => {
            console.log(`⚠️ ${service.name} geocoding failed:`, error);
            // Try next service
            tryGeocodingService(index + 1, services);
        });
}

// NEW: Show location status to user
function showLocationStatus(type, message) {
    const statusElement = document.getElementById('locationStatus');
    const messageElement = document.getElementById('locationMessage');
    
    if (!statusElement || !messageElement) {
        console.log('📍 Location status elements not found');
        return;
    }
    
    statusElement.className = `location-status ${type}`;
    statusElement.style.display = 'flex';
    
    let icon = '📡';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';
    
    messageElement.innerHTML = `${icon} ${message}`;
    
    // Auto-hide after 8 seconds unless it's loading
    if (type !== 'loading') {
        setTimeout(() => {
            statusElement.style.display = 'none';
        }, 8000);
    }
}

// NEW: Get accuracy level description
function getAccuracyLevel(accuracy) {
    if (!accuracy) return 'unknown';
    if (accuracy <= 50) return 'high';
    if (accuracy <= 100) return 'medium';
    return 'low';
}

// NEW: Toggle location info display
function toggleLocationInfo() {
    const locationInfo = document.getElementById('locationInfo');
    if (!locationInfo) return;
    
    if (locationInfo.style.display === 'none' || !locationInfo.style.display) {
        updateLocationDisplay();
        locationInfo.style.display = 'block';
    } else {
        locationInfo.style.display = 'none';
    }
}

// NEW: Retry location request
function retryLocationRequest() {
    console.log('🔄 Retrying location request...');
    
    // Stop any existing watch
    stopLocationWatching();
    
    // Reset location data
    userLocation = {
        latitude: null,
        longitude: null,
        accuracy: null,
        altitude: null,
        timestamp: null,
        source: 'manual',
        address: null
    };
    
    // Clear form fields
    updateLocationFormFields();
    
    // Request location again
    requestUserLocation();
}

// NEW: Get current location data for external use
function getCurrentLocationData() {
    return {
        hasLocation: !!(userLocation.latitude && userLocation.longitude),
        latitude: userLocation.latitude,
        longitude: userLocation.longitude,
        accuracy: userLocation.accuracy,
        altitude: userLocation.altitude,
        source: userLocation.source,
        timestamp: userLocation.timestamp,
        address: userLocation.address
    };
}

function handleFormSubmit(e) {
    e.preventDefault();
    
    if (isSubmitting) {
        return false;
    }
    
    const employeeId = document.getElementById('employee_id').value.trim();
    
    if (!validateEmployeeId()) {
        return false;
    }
    
    // NEW: Ensure location data is up to date before submission
    updateLocationFormFields();
    
    submitCheckin(employeeId);
}

function handleInputChange(e) {
    const input = e.target;
    const value = input.value.trim();
    
    // Clear previous validation states
    input.classList.remove('error', 'success');
    hideStatusMessage();
    
    // Real-time validation feedback
    if (value.length >= 3) {
        if (isValidEmployeeId(value)) {
            input.classList.add('success');
        } else {
            input.classList.add('error');
        }
    }
}

function handleKeyPress(e) {
    // Allow only alphanumeric characters
    const char = String.fromCharCode(e.which);
    if (!/[A-Za-z0-9]/.test(char)) {
        e.preventDefault();
        shakeInput(e.target);
    }
    
    // Submit on Enter key
    if (e.key === 'Enter') {
        e.preventDefault();
        handleFormSubmit(e);
    }
}

function validateEmployeeId() {
    const employeeInput = document.getElementById('employee_id');
    const employeeId = employeeInput.value.trim();
    
    if (!employeeId) {
        showValidationError(employeeInput, 'Employee ID is required');
        return false;
    }
    
    if (employeeId.length < 3) {
        showValidationError(employeeInput, 'Employee ID must be at least 3 characters');
        return false;
    }
    
    if (employeeId.length > 20) {
        showValidationError(employeeInput, 'Employee ID must be 20 characters or less');
        return false;
    }
    
    if (!isValidEmployeeId(employeeId)) {
        showValidationError(employeeInput, 'Employee ID can only contain letters and numbers');
        return false;
    }
    
    clearValidationError(employeeInput);
    return true;
}

function isValidEmployeeId(id) {
    return /^[A-Za-z0-9]+$/.test(id);
}

function showValidationError(input, message) {
    input.classList.add('error');
    showStatusMessage(message, 'error');
    shakeInput(input);
    input.focus();
}

function clearValidationError(input) {
    input.classList.remove('error');
    input.classList.add('success');
}

function shakeInput(input) {
    input.style.animation = 'shake 0.5s';
    setTimeout(() => {
        input.style.animation = '';
    }, 500);
}

function submitCheckin(employeeId) {
    if (isSubmitting) {
        console.log('⏭️ Already submitting, ignoring duplicate request');
        return false;
    }
    
    isSubmitting = true;
    updateSubmitButton(true);
    hideStatusMessage();
    
    console.log('📤 Starting check-in submission for:', employeeId);
    console.log('📍 Current location data:', userLocation);
    
    // Ensure location data is in the form
    updateLocationFormFields();
    
    // Prepare form data with CORRECT field names
    const formData = new FormData();
    formData.append('employee_id', employeeId);
    
    formData.append('latitude', userLocation.latitude || '');
    formData.append('longitude', userLocation.longitude || '');
    formData.append('accuracy', userLocation.accuracy || '');
    formData.append('altitude', userLocation.altitude || '');
    formData.append('location_source', userLocation.source || 'manual');
    formData.append('address', userLocation.address || '');
    
    // DEBUG: Log exactly what we're sending
    console.log('📤 Form data being submitted:');
    for (let [key, value] of formData.entries()) {
        console.log(`   ${key}: "${value}"`);
    }
    
    // Get the current URL for the check-in endpoint
    const currentUrl = window.location.pathname;
    const checkinUrl = `${currentUrl}/checkin`;
    
    console.log('🎯 Submitting to URL:', checkinUrl);
    
    fetch(checkinUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        console.log('📡 Server response status:', response.status);
        return response.json();
    })
    .then(data => {
        isSubmitting = false;
        updateSubmitButton(false);
        
        console.log('📥 Server response:', data);
        
        if (data.success) {
            showSuccessPage(data);
            console.log('✅ Check-in successful with location:', data.data?.has_location || false);
            
            // Stop location watching after successful check-in
            stopLocationWatching();
        } else {
            showStatusMessage(data.message || 'Check-in failed', 'error');
            console.log('❌ Check-in failed:', data.message);
        }
    })
    .catch(error => {
        isSubmitting = false;
        updateSubmitButton(false);
        showStatusMessage('Network error. Please check your connection and try again.', 'error');
        console.error('❌ Network error:', error);
    });
}

function showSuccessPage(data) {
    // Hide the check-in form and location status
    const checkinCard = document.querySelector('.checkin-card');
    const locationStatus = document.getElementById('locationStatus');
    const locationInfo = document.getElementById('locationInfo');
    const locationControls = document.querySelector('.location-controls');
    
    if (checkinCard) checkinCard.style.display = 'none';
    if (locationStatus) locationStatus.style.display = 'none';
    if (locationInfo) locationInfo.style.display = 'none';
    if (locationControls) locationControls.style.display = 'none';
    
    // Show success card
    const successCard = document.getElementById('successCard');
    if (successCard) {
        successCard.style.display = 'block';
        
        // Populate success details
        const elements = {
            'successEmployeeId': data.employee_id || '-',
            'successLocation': data.location || window.locationName || '-',
            'successEvent': data.event || window.eventName || '-',
            'successTime': data.time || new Date().toLocaleTimeString(),
            'successDate': data.date || new Date().toLocaleDateString()
        };
        
        Object.keys(elements).forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = elements[elementId];
            }
        });
        
        // NEW: Show location info in success card if available
        const successLocationInfo = document.getElementById('successLocationInfo');
        const successGpsInfo = document.getElementById('successGpsInfo');
        
        if (data.has_location && userLocation.latitude && userLocation.longitude) {
            let locationText = `Captured (±${Math.round(userLocation.accuracy || 0)}m)`;
            if (userLocation.address) {
                locationText += ` - ${userLocation.address}`;
            }
            
            if (successGpsInfo) successGpsInfo.textContent = locationText;
            if (successLocationInfo) successLocationInfo.style.display = 'block';
        }
        
        // Scroll to success card
        successCard.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Auto-refresh page after 30 seconds
    setTimeout(() => {
        console.log('🔄 Auto-refreshing page...');
        window.location.reload();
    }, 30000);
}

function showStatusMessage(message, type) {
    const statusElement = document.getElementById('statusMessage');
    if (!statusElement) return;
    
    statusElement.className = `status-message ${type}`;
    statusElement.innerHTML = `
        <div class="status-content">
            <i class="fas ${getStatusIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;
    statusElement.style.display = 'block';
    
    // Auto-hide info messages
    if (type === 'info') {
        setTimeout(() => {
            statusElement.style.display = 'none';
        }, 3000);
    }
}

function hideStatusMessage() {
    const statusElement = document.getElementById('statusMessage');
    if (statusElement) {
        statusElement.style.display = 'none';
    }
}

function getStatusIcon(type) {
    switch(type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-triangle';
        case 'info': return 'fa-info-circle';
        case 'warning': return 'fa-exclamation-circle';
        default: return 'fa-info-circle';
    }
}

function updateSubmitButton(isLoading) {
    const submitBtn = document.getElementById('submitBtn') || document.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    
    const btnContent = submitBtn.querySelector('.btn-content');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    
    if (isLoading) {
        submitBtn.disabled = true;
        if (btnContent) btnContent.style.display = 'none';
        if (btnLoader) btnLoader.style.display = 'flex';
    } else {
        submitBtn.disabled = false;
        if (btnContent) btnContent.style.display = 'flex';
        if (btnLoader) btnLoader.style.display = 'none';
    }
}

function startTimeUpdater() {
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
}

function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
    
    currentTime = now;
}

function handleVisibilityChange() {
    if (!document.hidden) {
        // Page became visible, update time immediately
        updateCurrentTime();
        
        // NEW: Request location again if we don't have it and haven't submitted yet
        if (!userLocation.latitude && !isSubmitting) {
            console.log('🔄 Page visible again, retrying location...');
            setTimeout(requestUserLocation, 1000);
        }
    }
}

function checkInAnother() {
    // Stop location watching
    stopLocationWatching();
    
    // Reload page
    window.location.reload();
}

// NEW: Cleanup function for page unload
function cleanup() {
    stopLocationWatching();
    console.log('🧹 Cleaned up geolocation resources');
}

// NEW: Setup cleanup handlers
window.addEventListener('beforeunload', cleanup);
window.addEventListener('pagehide', cleanup);

// NEW: Export geolocation functions for global use
window.requestUserLocation = requestUserLocation;
window.getCurrentLocationData = getCurrentLocationData;
window.retryLocationRequest = retryLocationRequest;
window.toggleLocationInfo = toggleLocationInfo;
window.stopLocationWatching = stopLocationWatching;
window.startLocationWatching = startLocationWatching;

console.log('📍 QR Destination with Geolocation loaded successfully!');
console.log('🔧 Available functions: requestUserLocation(), getCurrentLocationData(), retryLocationRequest(), toggleLocationInfo()');
console.log('📊 Location tracking ready for check-ins!');