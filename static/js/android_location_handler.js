/**
 * Android Location Fix - GPS + IP Geolocation Only
 * File: static/js/android_location_handler.js
 * 
 * This version includes only precise location methods:
 * 1. Progressive GPS fallback (4 attempts)
 * 2. IP-based geolocation (3 services) - 5-50km accuracy
 * No timezone analysis (removed 100km accuracy method)
 */

// Android-specific geolocation configuration
const ANDROID_LOCATION_CONFIG = {
    // Primary attempt - High accuracy with reasonable timeout
    highAccuracy: {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 60000
    },
    
    // Fallback attempt - Network-based location
    networkBased: {
        enableHighAccuracy: false,
        timeout: 20000,
        maximumAge: 300000
    },
    
    // Final attempt - Any available location
    anyLocation: {
        enableHighAccuracy: false,
        timeout: 30000,
        maximumAge: 600000
    }
};

// Global variables for location state
let locationAttemptInProgress = false;
let currentLocationMethod = '';

// Enhanced location request with GPS + IP fallback only
function requestAndroidEnhancedLocation() {
    console.log("📱 Starting Android location request (GPS + IP methods only)...");
    
    if (locationAttemptInProgress) {
        console.log("📍 Location attempt already in progress, skipping");
        return;
    }

    if (typeof locationRequestActive !== 'undefined' && locationRequestActive) {
        console.log("📍 Location request already active, skipping");
        return;
    }

    if (!navigator.geolocation) {
        console.log("❌ Geolocation not supported, trying IP-based location");
        attemptIPBasedLocation();
        return;
    }

    locationAttemptInProgress = true;

    // Set active flags
    if (typeof locationRequestActive !== 'undefined') {
        locationRequestActive = true;
    }
    if (typeof locationCaptureActive !== 'undefined') {
        locationCaptureActive = true;
    }

    console.log("📱 Attempting GPS-based location sequence...");
    attemptAndroidLocationSequence();
}

// GPS-based sequence (Steps 1-4)
function attemptAndroidLocationSequence() {
    console.log("🔄 Step 1/5: High Accuracy GPS");
    currentLocationMethod = 'gps_high_accuracy';
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log("✅ GPS high-accuracy success!");
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
    console.log("🔄 Step 2/5: Network-based GPS");
    currentLocationMethod = 'network';
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log("✅ Network-based GPS success!");
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
    console.log("🔄 Step 3/5: Any available GPS");
    currentLocationMethod = 'any';
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log("✅ Any-location GPS success!");
            handleAndroidLocationSuccess(position, "any");
        },
        (error) => {
            console.log(`❌ Any location failed (${error.message}), trying watchPosition...`);
            attemptWatchPosition();
        },
        ANDROID_LOCATION_CONFIG.anyLocation
    );
}

function attemptWatchPosition() {
    console.log("🔄 Step 4/5: Watch Position (persistent)");
    currentLocationMethod = 'watch';
    
    let watchId = null;
    let watchTimeout = null;
    
    watchTimeout = setTimeout(() => {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
        }
        console.log("❌ Watch position timed out, trying IP-based location...");
        attemptIPBasedLocation();
    }, 25000);
    
    watchId = navigator.geolocation.watchPosition(
        (position) => {
            console.log("✅ Watch position success!");
            navigator.geolocation.clearWatch(watchId);
            clearTimeout(watchTimeout);
            handleAndroidLocationSuccess(position, "watch");
        },
        (error) => {
            console.log(`❌ Watch position error: ${error.message}`);
        },
        {
            enableHighAccuracy: false,
            timeout: 20000,
            maximumAge: 0
        }
    );
}

// IP-based geolocation (Step 5) - Final fallback
function attemptIPBasedLocation() {
    console.log("🔄 Step 5/5: IP-based Geolocation (Final Fallback)");
    currentLocationMethod = 'ip_geolocation';
    
    // Try multiple IP geolocation services for better accuracy
    const ipLocationServices = [
        {
            url: 'https://ipinfo.io/json',
            parseResponse: (data) => {
                if (data.loc) {
                    const [lat, lng] = data.loc.split(',');
                    return {
                        lat: parseFloat(lat),
                        lng: parseFloat(lng),
                        city: data.city,
                        region: data.region,
                        country: data.country,
                        accuracy: data.city ? 15000 : 50000 // Better accuracy if city is available
                    };
                }
                return null;
            }
        },
        { 
            url: 'https://ipapi.co/json/',
            parseResponse: (data) => ({
                lat: data.latitude,
                lng: data.longitude,
                city: data.city,
                region: data.region,
                country: data.country_name,
                accuracy: data.city ? 10000 : 50000 // Better accuracy if city is available
            })
        },
    ];
    
    let serviceIndex = 0;
    
    function tryNextIPService() {
        if (serviceIndex >= ipLocationServices.length) {
            console.log("❌ All IP geolocation services failed - location detection complete");
            handleAndroidLocationError("All GPS and IP geolocation methods failed");
            return;
        }
        
        const service = ipLocationServices[serviceIndex];
        console.log(`🌐 Trying IP geolocation service ${serviceIndex + 1}: ${service.url}`);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        fetch(service.url, {
            method: 'GET',
            signal: controller.signal,
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            clearTimeout(timeoutId);
            console.log(`🌐 IP service ${serviceIndex + 1} response:`, data);
            
            const parsed = service.parseResponse(data);
            
            if (parsed && parsed.lat && parsed.lng && !isNaN(parsed.lat) && !isNaN(parsed.lng)) {
                // Validate coordinates are reasonable
                if (parsed.lat >= -90 && parsed.lat <= 90 && parsed.lng >= -180 && parsed.lng <= 180) {
                    console.log(`✅ IP-based location success: ${parsed.lat}, ${parsed.lng}`);
                    console.log(`📊 Location: ${parsed.city}, ${parsed.region}, ${parsed.country}`);
                    console.log(`📊 Estimated accuracy: ${parsed.accuracy}m (~${Math.round(parsed.accuracy/1000)}km)`);
                    
                    const ipLocationData = {
                        coords: {
                            latitude: parsed.lat,
                            longitude: parsed.lng,
                            accuracy: parsed.accuracy,
                            altitude: null
                        },
                        locationInfo: {
                            city: parsed.city,
                            region: parsed.region,
                            country: parsed.country,
                            source: `IP Service ${serviceIndex + 1}`,
                            serviceUrl: service.url
                        }
                    };
                    
                    handleAndroidLocationSuccess(ipLocationData, "ip_geolocation");
                    return;
                }
            }
            
            console.log(`❌ Invalid or missing coordinates from service ${serviceIndex + 1}, trying next...`);
            serviceIndex++;
            tryNextIPService();
        })
        .catch(error => {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                console.log(`❌ IP service ${serviceIndex + 1} timed out (10s), trying next...`);
            } else {
                console.log(`❌ IP service ${serviceIndex + 1} failed: ${error.message}, trying next...`);
            }
            serviceIndex++;
            tryNextIPService();
        });
    }
    
    tryNextIPService();
}

// Enhanced success handler for GPS and IP location methods
function handleAndroidLocationSuccess(position, source) {
    console.log(`✅ Android location obtained successfully via ${source}`);
    
    let locationData;
    
    if (source === "ip_geolocation") {
        // Handle IP-based location
        locationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            timestamp: new Date(),
            source: source,
            address: null,
            locationInfo: position.locationInfo || null
        };
        
        console.log(`📍 IP-estimated coordinates: ${position.coords.latitude}, ${position.coords.longitude}`);
        console.log(`📊 IP-estimated accuracy: ${position.coords.accuracy}m (~${Math.round(position.coords.accuracy/1000)}km)`);
        if (position.locationInfo) {
            console.log(`🏢 Location info: ${position.locationInfo.city}, ${position.locationInfo.region}`);
        }
    } else {
        // Handle GPS-based location
        locationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            timestamp: new Date(),
            source: source,
            address: null,
        };
        
        console.log(`📍 GPS coordinates: ${position.coords.latitude}, ${position.coords.longitude}`);
        console.log(`📊 GPS accuracy: ${position.coords.accuracy}m`);
    }

    // Update global location variables
    if (typeof userLocation !== 'undefined') {
        Object.assign(userLocation, locationData);
        console.log("📍 Updated userLocation with location data");
        
        // Trigger reverse geocoding if we have coordinates but no address
        if (typeof reverseGeocode === 'function' && locationData.latitude && locationData.longitude && !locationData.address) {
            reverseGeocode(locationData.latitude, locationData.longitude);
        }
    }

    if (typeof currentUserLocation !== 'undefined') {
        Object.assign(currentUserLocation, locationData);
        console.log("📍 Updated currentUserLocation with location data");
        
        // Trigger enhanced reverse geocoding if available
        if (typeof reverseGeocodeEnhanced === 'function' && locationData.latitude && locationData.longitude && !locationData.address) {
            reverseGeocodeEnhanced(locationData.latitude, locationData.longitude);
        }
    }

    // Clear active flags
    if (typeof locationRequestActive !== 'undefined') {
        locationRequestActive = false;
    }
    if (typeof locationCaptureActive !== 'undefined') {
        locationCaptureActive = false;
    }
    locationAttemptInProgress = false;

    // Console logging
    console.log(`📊 LOCATION SUCCESS LOG:`, {
        method: source,
        success: true,
        coordinates: `${locationData.latitude},${locationData.longitude}`,
        accuracy: `${locationData.accuracy}m`,
        accuracyKm: `~${Math.round(locationData.accuracy/1000)}km`,
        locationInfo: locationData.locationInfo,
        timestamp: new Date().toISOString()
    });
}

function handleAndroidLocationError(errorMessage) {
    console.log(`❌ All Android location methods failed: ${errorMessage}`);
    
    // Update global location variables to indicate manual source
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
    locationAttemptInProgress = false;

    console.log(`📊 LOCATION ERROR LOG:`, {
        error: errorMessage,
        method: currentLocationMethod,
        finalResult: 'manual_entry_required',
        gpsAttempts: 4,
        ipAttempts: 3,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString()
    });
}

// Device detection functions
function isAndroidDevice() {
    const userAgent = navigator.userAgent.toLowerCase();
    return userAgent.includes('android');
}

function isAndroidChrome() {
    const userAgent = navigator.userAgent.toLowerCase();
    return userAgent.includes('android') && userAgent.includes('chrome') && !userAgent.includes('edg');
}

// Main initialization function
function initializeAndroidLocation() {
    console.log("📱 Initializing Android location services (GPS + IP only)...");
    
    if (isAndroidDevice()) {
        console.log("📱 Android device detected, using GPS + IP location methods (5 steps)");
        requestAndroidEnhancedLocation();
    } else {
        console.log("📱 Non-Android device, using standard location request");
        
        if (typeof requestLocationData === 'function') {
            requestLocationData();
        } else if (typeof requestEnhancedLocation === 'function') {
            requestEnhancedLocation();
        }
    }
}

// Override standard location initialization for Android devices
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        if (isAndroidDevice()) {
            console.log("📱 Android detected - overriding with GPS + IP location handler");
            
            if (typeof initializeLocation === 'function') {
                window.initializeLocation = function() {
                    console.log("📱 Using GPS + IP Android location initialization");
                    initializeAndroidLocation();
                };
            }
            
            if (typeof requestEnhancedLocation === 'function') {
                window.requestEnhancedLocation = function() {
                    console.log("📱 Using GPS + IP Android location request");
                    initializeAndroidLocation();
                };
            }
        }
    }, 100);
});

// Export functions
if (typeof window !== 'undefined') {
    window.AndroidLocationHandler = {
        requestAndroidEnhancedLocation,
        isAndroidDevice,
        isAndroidChrome,
        initializeAndroidLocation,
        attemptIPBasedLocation
    };
}