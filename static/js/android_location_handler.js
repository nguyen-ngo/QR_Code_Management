/**
 * Enhanced Android Location Fix - Separate Module
 * File: static/js/android_location_handler.js
 * 
 * This module addresses Android-specific geolocation issues:
 * 1. Android Chrome timeout handling
 * 2. Progressive fallback strategy
 * 3. Enhanced permission detection
 * 4. Network location fallback
 * 5. Multiple retry attempts with different configurations
 */

// Android-specific geolocation configuration
const ANDROID_LOCATION_CONFIG = {
    // Primary attempt - High accuracy with reasonable timeout
    highAccuracy: {
        enableHighAccuracy: true,
        timeout: 15000,  // Increased from 10000 for Android
        maximumAge: 60000 // Reduced cache time for fresh location
    },
    
    // Fallback attempt - Network-based location
    networkBased: {
        enableHighAccuracy: false,
        timeout: 20000,  // Longer timeout for network-based
        maximumAge: 300000
    },
    
    // Final attempt - Any available location
    anyLocation: {
        enableHighAccuracy: false,
        timeout: 30000,  // Maximum patience for Android
        maximumAge: 600000
    }
};

// Enhanced location request with Android-specific handling
function requestAndroidEnhancedLocation() {
    console.log("📱 Starting Android-enhanced location request...");
    
    if (typeof locationRequestActive !== 'undefined' && locationRequestActive) {
        console.log("📍 Location request already active, skipping Android enhancement");
        return;
    }

    if (!navigator.geolocation) {
        console.log("❌ Geolocation not supported");
        if (typeof userLocation !== 'undefined') {
            userLocation.source = "manual";
        }
        if (typeof currentUserLocation !== 'undefined') {
            currentUserLocation.source = "manual";
        }
        return;
    }

    // Set active flag
    if (typeof locationRequestActive !== 'undefined') {
        locationRequestActive = true;
    }
    if (typeof locationCaptureActive !== 'undefined') {
        locationCaptureActive = true;
    }

    console.log("📱 Attempting Android-optimized location sequence...");
    
    // Start progressive location attempts
    attemptAndroidLocationSequence();
}

function attemptAndroidLocationSequence() {
    console.log("🔄 Android Location Sequence - Attempt 1: High Accuracy GPS");
    
    // Attempt 1: High accuracy with Android-optimized timeout
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log("✅ Android high-accuracy location success!");
            handleAndroidLocationSuccess(position, "gps_high_accuracy");
        },
        (error) => {
            console.log(`❌ High accuracy failed (${error.message}), trying network-based...`);
            attemptNetworkBasedLocation();
        },
        ANDROID_LOCATION_CONFIG.highAccuracy
    );
}

function attemptNetworkBasedLocation() {
    console.log("🔄 Android Location Sequence - Attempt 2: Network-based");
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log("✅ Android network-based location success!");
            handleAndroidLocationSuccess(position, "network");
        },
        (error) => {
            console.log(`❌ Network-based failed (${error.message}), trying any location...`);
            attemptAnyAvailableLocation();
        },
        ANDROID_LOCATION_CONFIG.networkBased
    );
}

function attemptAnyAvailableLocation() {
    console.log("🔄 Android Location Sequence - Attempt 3: Any available");
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log("✅ Android any-location success!");
            handleAndroidLocationSuccess(position, "any");
        },
        (error) => {
            console.log(`❌ All location attempts failed (${error.message}), trying watchPosition...`);
            attemptWatchPosition();
        },
        ANDROID_LOCATION_CONFIG.anyLocation
    );
}

function attemptWatchPosition() {
    console.log("🔄 Android Location Sequence - Attempt 4: Watch Position (single shot)");
    
    let watchId = null;
    let watchTimeout = null;
    
    // Set timeout for watch attempt
    watchTimeout = setTimeout(() => {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
        }
        console.log("❌ Watch position timed out, location failed");
        handleAndroidLocationError("All location methods failed");
    }, 25000);
    
    // Use watchPosition for more persistent location tracking
    watchId = navigator.geolocation.watchPosition(
        (position) => {
            console.log("✅ Android watch position success!");
            
            // Clear watch and timeout
            navigator.geolocation.clearWatch(watchId);
            clearTimeout(watchTimeout);
            
            handleAndroidLocationSuccess(position, "watch");
        },
        (error) => {
            console.log(`❌ Watch position error: ${error.message}`);
            // Don't clear watch immediately, let timeout handle it
        },
        {
            enableHighAccuracy: false,
            timeout: 20000,
            maximumAge: 0  // Force fresh location
        }
    );
}

function handleAndroidLocationSuccess(position, source) {
    console.log(`✅ Android location obtained successfully via ${source}`);
    console.log(`📍 Coordinates: ${position.coords.latitude}, ${position.coords.longitude}`);
    console.log(`📊 Accuracy: ${position.coords.accuracy}m`);

    // Create location object
    const locationData = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        altitude: position.coords.altitude,
        timestamp: new Date(),
        source: source,
        address: null,
    };

    // Update global location variables based on what's available
    if (typeof userLocation !== 'undefined') {
        Object.assign(userLocation, locationData);
        console.log("📍 Updated userLocation with Android data");
        
        // Trigger reverse geocoding if function exists
        if (typeof reverseGeocode === 'function') {
            reverseGeocode(userLocation.latitude, userLocation.longitude);
        }
    }

    if (typeof currentUserLocation !== 'undefined') {
        Object.assign(currentUserLocation, locationData);
        console.log("📍 Updated currentUserLocation with Android data");
        
        // Trigger enhanced reverse geocoding if function exists
        if (typeof reverseGeocodeEnhanced === 'function') {
            reverseGeocodeEnhanced(currentUserLocation.latitude, currentUserLocation.longitude);
        }
    }

    // Clear active flags
    if (typeof locationRequestActive !== 'undefined') {
        locationRequestActive = false;
    }
    if (typeof locationCaptureActive !== 'undefined') {
        locationCaptureActive = false;
    }

    // Log success for monitoring
    logLocationAction('android_location_success', {
        source: source,
        accuracy: position.coords.accuracy,
        coordinates: `${position.coords.latitude},${position.coords.longitude}`
    });
}

function handleAndroidLocationError(errorMessage) {
    console.log(`❌ Android location error: ${errorMessage}`);
    
    // Update global location variables
    if (typeof userLocation !== 'undefined') {
        userLocation.source = "manual";
    }
    if (typeof currentUserLocation !== 'undefined') {
        currentUserLocation.source = "manual";
    }

    // Clear active flags
    if (typeof locationRequestActive !== 'undefined') {
        locationRequestActive = false;
    }
    if (typeof locationCaptureActive !== 'undefined') {
        locationCaptureActive = false;
    }

    // Log error for monitoring
    logLocationAction('android_location_error', {
        error: errorMessage,
        userAgent: navigator.userAgent
    });
}

// Enhanced permission checking for Android
function checkAndroidLocationPermissions() {
    console.log("📱 Checking Android location permissions...");
    
    // Check if permissions API is available (newer Android browsers)
    if ('permissions' in navigator) {
        navigator.permissions.query({name: 'geolocation'}).then(function(result) {
            console.log(`📱 Geolocation permission: ${result.state}`);
            
            if (result.state === 'granted') {
                console.log("✅ Android location permission granted");
                requestAndroidEnhancedLocation();
            } else if (result.state === 'prompt') {
                console.log("⚠️ Android location permission will be prompted");
                requestAndroidEnhancedLocation();
            } else {
                console.log("❌ Android location permission denied");
                handleAndroidLocationError("Permission denied");
            }
        }).catch(function(error) {
            console.log("⚠️ Could not check permissions, proceeding with location request");
            requestAndroidEnhancedLocation();
        });
    } else {
        // Fallback for older Android browsers
        console.log("📱 Permissions API not available, proceeding with location request");
        requestAndroidEnhancedLocation();
    }
}

// Detect if device is Android
function isAndroidDevice() {
    const userAgent = navigator.userAgent.toLowerCase();
    return userAgent.includes('android');
}

// Detect if browser is Chrome on Android
function isAndroidChrome() {
    const userAgent = navigator.userAgent.toLowerCase();
    return userAgent.includes('android') && userAgent.includes('chrome') && !userAgent.includes('edg');
}

// Enhanced location initialization for Android
function initializeAndroidLocation() {
    console.log("📱 Initializing Android-enhanced location services...");
    
    if (isAndroidDevice()) {
        console.log("📱 Android device detected, using enhanced location handling");
        
        // Use Android-specific permission checking
        checkAndroidLocationPermissions();
    } else {
        console.log("📱 Non-Android device, using standard location request");
        
        // Fall back to standard location request
        if (typeof requestLocationData === 'function') {
            requestLocationData();
        } else if (typeof requestEnhancedLocation === 'function') {
            requestEnhancedLocation();
        }
    }
}

// Location action logging function
function logLocationAction(action, data) {
    try {
        console.log(`📊 Location Action Log: ${action}`, data);
        
        // Send to server for monitoring if endpoint exists
        if (typeof fetch !== 'undefined') {
            fetch('/api/log-location-action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    data: data,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent
                })
            }).catch(error => {
                console.log('📊 Could not send location log to server:', error);
            });
        }
    } catch (error) {
        console.log('📊 Location logging error:', error);
    }
}

// Override standard location initialization if this is an Android device
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure other scripts are loaded
    setTimeout(() => {
        if (isAndroidDevice()) {
            console.log("📱 Android detected - overriding standard location initialization");
            
            // Replace standard initialization with Android-enhanced version
            if (typeof initializeLocation === 'function') {
                const originalInitializeLocation = initializeLocation;
                window.initializeLocation = function() {
                    console.log("📱 Using Android-enhanced location initialization");
                    initializeAndroidLocation();
                };
            }
            
            // Also handle the enhanced location capture
            if (typeof requestEnhancedLocation === 'function') {
                const originalRequestEnhanced = requestEnhancedLocation;
                window.requestEnhancedLocation = function() {
                    console.log("📱 Using Android-enhanced location request");
                    initializeAndroidLocation();
                };
            }
        }
    }, 100);
});

// Export functions for external use
if (typeof window !== 'undefined') {
    window.AndroidLocationHandler = {
        requestAndroidEnhancedLocation,
        checkAndroidLocationPermissions,
        isAndroidDevice,
        isAndroidChrome,
        initializeAndroidLocation,
        logLocationAction
    };
}