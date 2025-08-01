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
    console.log('🚀 Initializing page...');
    // Focus on employee ID input
    const employeeInput = document.getElementById('employee_id');
    if (employeeInput) {
        employeeInput.focus();
    }
}

function setupEventListeners() {
    console.log('🎧 Setting up event listeners...');
    const form = document.getElementById('checkinForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
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
    
    // Store location data with validation (keep as numbers, not strings)
    userLocation = {
        latitude: Number(coords.latitude),  // Keep as number for calculations
        longitude: Number(coords.longitude),
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
    if (!navigator.geolocation || locationWatchId !== null) {
        return;
    }
    
    const watchOptions = {
        enableHighAccuracy: true,
        timeout: 30000,
        maximumAge: 600000  // 10 minutes
    };
    
    locationWatchId = navigator.geolocation.watchPosition(
        handleLocationSuccess,
        (error) => {
            console.log('⚠️ Location watch error:', error);
            // Don't show error for watch failures, just log them
        },
        watchOptions
    );
    
    console.log('👁️ Started location watching');
}

// Stop watching location
function stopLocationWatching() {
    if (locationWatchId !== null) {
        navigator.geolocation.clearWatch(locationWatchId);
        locationWatchId = null;
        console.log('⏹️ Stopped location watching');
    }
}

// Update form fields with location data
function updateLocationFormFields() {
    // CRITICAL FIX: Use correct field names that match server expectations
    const fields = {
        'latitude': userLocation.latitude ? userLocation.latitude.toFixed(6) : '',  // Convert to string with precision here
        'longitude': userLocation.longitude ? userLocation.longitude.toFixed(6) : '',
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

// Update location display
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
        
        console.log('🖥️ Updated location display');
    }
}

// Reverse geocode coordinates to get address
function reverseGeocodeLocation(lat, lng) {
    console.log('🏠 Getting address from coordinates...');
    
    // Use a free geocoding service
    const geocodeUrl = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`;
    
    fetch(geocodeUrl)
        .then(response => response.json())
        .then(data => {
            if (data && (data.locality || data.city || data.principalSubdivision)) {
                const address = [
                    data.locality || data.city,
                    data.principalSubdivision,
                    data.countryName
                ].filter(Boolean).join(', ');
                
                userLocation.address = address;
                updateLocationFormFields();
                updateLocationDisplay();
                
                console.log('🏠 Address found:', address);
            } else {
                console.log('🏠 No address found');
                userLocation.address = 'Address not available';
                updateLocationFormFields();
                updateLocationDisplay();
            }
        })
        .catch(error => {
            console.log('⚠️ Geocoding error:', error);
            userLocation.address = 'Address lookup failed';
            updateLocationFormFields();
            updateLocationDisplay();
        });
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

// Show location status to user
function showLocationStatus(type, message) {
    const statusElement = document.getElementById('locationStatus');
    const messageElement = document.getElementById('locationMessage');
    
    if (statusElement && messageElement) {
        statusElement.className = `location-status ${type}`;
        messageElement.textContent = message;
        
        // Auto-hide success messages after 3 seconds
        if (type === 'success') {
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 3000);
        } else {
            statusElement.style.display = 'block';
        }
    }
    
    console.log(`📍 Location status: ${type} - ${message}`);
}

// NEW: Get accuracy level description
function getAccuracyLevel(accuracy) {
    if (!accuracy) return 'unknown';
    if (accuracy <= 50) return 'high';
    if (accuracy <= 100) return 'medium';
    return 'low';
}

// Toggle location info display
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

// Retry location request
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

// Get current location data for external use
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
    
    if (!employeeId) {
        showStatusMessage('Please enter your Employee ID', 'error');
        return false;
    }
    
    if (!employeeId.match(/^[A-Za-z0-9]{3,20}$/)) {
        showStatusMessage('Invalid Employee ID format. Use 3-20 alphanumeric characters.', 'error');
        return false;
    }
    
    // Ensure location data is up to date before submission
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
    
    // CRITICAL FIX: Use exact field names that server expects
    formData.append('latitude', userLocation.latitude ? userLocation.latitude.toFixed(6) : '');
    formData.append('longitude', userLocation.longitude ? userLocation.longitude.toFixed(6) : '');
    formData.append('accuracy', userLocation.accuracy || '');
    formData.append('altitude', userLocation.altitude || '');
    formData.append('location_source', userLocation.source || 'manual');  // FIXED: was locationSource
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
    console.log('🎉 Showing success page with data:', data);
    
    // Hide the form
    const form = document.getElementById('checkinForm');
    if (form) {
        form.style.display = 'none';
    }
    
    // Show success message
    showStatusMessage(`Check-in successful for ${data.data.employee_id}!`, 'success');
    
    // You can customize this to show a proper success page
    // For now, just show the success message and reload after 3 seconds
    setTimeout(() => {
        location.reload();
    }, 3000);;
let locationRequestActive = false;
let locationWatchId = null;

// Utility function to show status messages
function showStatusMessage(message, type = 'info') {
    // This function should exist in your original code
    // If not, here's a simple implementation
    console.log(`Status: ${type} - ${message}`);
    
    // Try to find existing status display element
    let statusEl = document.getElementById('statusMessage');
    if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.id = 'statusMessage';
        statusEl.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 1000;
            font-weight: 500;
        `;
        document.body.appendChild(statusEl);
    }
    
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    
    // Style based on type
    if (type === 'error') {
        statusEl.style.backgroundColor = '#fee2e2';
        statusEl.style.color = '#dc2626';
        statusEl.style.border = '1px solid #fecaca';
    } else if (type === 'success') {
        statusEl.style.backgroundColor = '#dcfce7';
        statusEl.style.color = '#16a34a';
        statusEl.style.border = '1px solid #bbf7d0';
    } else {
        statusEl.style.backgroundColor = '#dbeafe';
        statusEl.style.color = '#2563eb';
        statusEl.style.border = '1px solid #bfdbfe';
    }
    
    statusEl.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusEl.style.display = 'none';
    }, 5000);
}

// Utility function to hide status messages
function hideStatusMessage() {
    const statusEl = document.getElementById('statusMessage');
    if (statusEl) {
        statusEl.style.display = 'none';
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
    const submitBtn = document.querySelector('#checkinForm button[type="submit"]');
    if (submitBtn) {
        if (isLoading) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Check In';
        }
    }
}

function startTimeUpdater() {
    console.log('⏰ Starting time updater...');
    // Update current time display
    setInterval(() => {
        const timeElement = document.getElementById('currentTime');
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString();
        }
    }, 1000);
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