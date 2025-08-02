/**
 * QR Code Destination Page JavaScript - Complete with Location Tracking
 * Handles staff check-in functionality with GPS location support
 */

// Global variables
let isSubmitting = false;
let currentTime = new Date();

// Location tracking variables
let userLocation = {
  latitude: null,
  longitude: null,
  accuracy: null,
  altitude: null,
  timestamp: null,
  source: "manual",
  address: null,
};
let locationRequestActive = false;
let locationWatchId = null;

// Initialize page when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  console.log(
    "🚀 QR Destination page initialized with enhanced location tracking"
  );

  // Initialize the page
  initializePage();
  setupEventListeners();
  startTimeUpdater();

  // Initialize geolocation
  initializeGeolocation();

  // Add hidden form fields for location data
  ensureLocationFormFields();
});

// Initialize basic page functionality
function initializePage() {
  console.log("🚀 Initializing page...");

  // Focus on employee ID input
  const employeeInput = document.getElementById("employee_id");
  if (employeeInput) {
    employeeInput.focus();
  }

  // Add page load animation
  document.body.classList.add("page-loaded");
}

// Set up event listeners
function setupEventListeners() {
  console.log("🎧 Setting up event listeners...");

  const form = document.getElementById("checkinForm");
  const employeeInput = document.getElementById("employee_id");

  if (form) {
    form.addEventListener("submit", handleFormSubmit);
  }

  if (employeeInput) {
    employeeInput.addEventListener("input", handleInputChange);
    employeeInput.addEventListener("keypress", handleKeyPress);
  }
}

// Start time updater
function startTimeUpdater() {
  console.log("⏰ Starting time updater...");

  // Update current time display
  setInterval(() => {
    const timeElement = document.getElementById("currentTime");
    if (timeElement) {
      timeElement.textContent = new Date().toLocaleTimeString();
    }
    currentTime = new Date();
  }, 1000);
}

// Handle form submission
function handleFormSubmit(e) {
  e.preventDefault();

  if (isSubmitting) {
    return false;
  }

  const employeeId = document.getElementById("employee_id").value.trim();

  if (!validateEmployeeId(employeeId)) {
    return false;
  }

  // Ensure location data is up to date before submission
  updateLocationFormFields();

  submitCheckin(employeeId);
}

// Handle input changes
function handleInputChange(e) {
  const input = e.target;
  const value = input.value.trim();

  // Clear previous validation states
  input.classList.remove("error", "success");
  hideStatusMessage();

  // Real-time validation feedback
  if (value.length >= 3) {
    if (isValidEmployeeId(value)) {
      input.classList.add("success");
    } else {
      input.classList.add("error");
    }
  }
}

// Handle key press
function handleKeyPress(e) {
  // Allow only alphanumeric characters
  const char = String.fromCharCode(e.which);
  if (!/[A-Za-z0-9]/.test(char)) {
    e.preventDefault();
    shakeInput(e.target);
  }

  // Submit on Enter key
  if (e.key === "Enter") {
    e.preventDefault();
    handleFormSubmit(e);
  }
}

// Validate employee ID
function validateEmployeeId(employeeId) {
  if (!employeeId) {
    showStatusMessage("Please enter your Employee ID", "error");
    return false;
  }

  if (!employeeId.match(/^[A-Za-z0-9]{3,20}$/)) {
    showStatusMessage(
      "Invalid Employee ID format. Use 3-20 alphanumeric characters.",
      "error"
    );
    return false;
  }

  return true;
}

// Check if employee ID is valid format
function isValidEmployeeId(employeeId) {
  return /^[A-Za-z0-9]{3,20}$/.test(employeeId);
}

// Shake input on invalid character
function shakeInput(input) {
  input.classList.add("shake");
  setTimeout(() => {
    input.classList.remove("shake");
  }, 300);
}

// GEOLOCATION FUNCTIONS

// Initialize geolocation with better error handling
function initializeGeolocation() {
  console.log("📍 Initializing geolocation system...");

  if (!navigator.geolocation) {
    console.log("⚠️ Geolocation not supported by this browser");
    showLocationStatus("error", "Location services not supported");
    return;
  }

  console.log("✅ Geolocation API available");

  // Request location immediately
  requestUserLocation();

  // Set up continuous watching for better accuracy
  if ("permissions" in navigator) {
    navigator.permissions
      .query({ name: "geolocation" })
      .then(function (result) {
        console.log("📍 Geolocation permission status:", result.state);

        if (result.state === "granted") {
          startLocationWatching();
        }

        result.onchange = function () {
          console.log("📍 Geolocation permission changed to:", result.state);
          if (result.state === "granted") {
            requestUserLocation();
            startLocationWatching();
          } else {
            stopLocationWatching();
          }
        };
      });
  }
}

// Request user location
function requestUserLocation() {
  if (locationRequestActive) {
    console.log("⏭️ Location request already active");
    return;
  }

  locationRequestActive = true;
  showLocationStatus("loading", "Getting your location...");

  const options = {
    enableHighAccuracy: true, // Use GPS for better accuracy
    timeout: 15000, // Wait up to 15 seconds
    maximumAge: 300000, // Accept cached location up to 5 minutes old
  };

  console.log("📡 Requesting location with options:", options);

  navigator.geolocation.getCurrentPosition(
    handleLocationSuccess,
    handleLocationError,
    options
  );

  // Set backup timeout
  setTimeout(() => {
    if (locationRequestActive && !userLocation.latitude) {
      console.log("⏰ Location request backup timeout");
      handleLocationError({ code: 3, message: "Request timed out" });
    }
  }, 16000);
}

// Handle successful location retrieval
function handleLocationSuccess(position) {
  locationRequestActive = false;

  const coords = position.coords;
  console.log("✅ Location obtained:", {
    latitude: coords.latitude,
    longitude: coords.longitude,
    accuracy: coords.accuracy,
    altitude: coords.altitude,
    timestamp: position.timestamp,
  });

  // Validate coordinates
  if (!coords.latitude || !coords.longitude) {
    console.log("⚠️ Invalid coordinates received");
    handleLocationError({ code: 2, message: "Invalid coordinates" });
    return;
  }

  // Store location data (keep as numbers for calculations)
  userLocation = {
    latitude: Number(coords.latitude),
    longitude: Number(coords.longitude),
    accuracy: coords.accuracy ? Math.round(coords.accuracy) : null,
    altitude: coords.altitude ? Math.round(coords.altitude) : null,
    timestamp: position.timestamp,
    source: "gps",
    address: null,
  };

  console.log("💾 Stored location data:", userLocation);

  // Update form fields immediately
  updateLocationFormFields();

  // Update display
  updateLocationDisplay();

  // Show success status
  const accuracyText = coords.accuracy
    ? `±${Math.round(coords.accuracy)}m`
    : "unknown";
  showLocationStatus("success", `Location captured (${accuracyText} accuracy)`);

  // Try to get address
  reverseGeocodeLocation(coords.latitude, coords.longitude);
}

// Handle location errors
function handleLocationError(error) {
  locationRequestActive = false;

  let message = "Unable to get location";

  console.log("❌ Location error:", error);

  switch (error.code) {
    case error.PERMISSION_DENIED:
      message = "Location access denied - please enable in browser settings";
      break;
    case error.POSITION_UNAVAILABLE:
      message = "Location unavailable - GPS signal weak";
      break;
    case error.TIMEOUT:
      message = "Location request timed out";
      break;
    default:
      message = "Location error occurred";
  }

  showLocationStatus(
    "error",
    `${message} - check-in will continue without location`
  );
  userLocation.source = "manual";
  updateLocationFormFields();
}

// Update form fields with location data
function updateLocationFormFields() {
  const fields = {
    latitude: userLocation.latitude ? userLocation.latitude.toFixed(6) : "",
    longitude: userLocation.longitude ? userLocation.longitude.toFixed(6) : "",
    accuracy: userLocation.accuracy || "",
    altitude: userLocation.altitude || "",
    location_source: userLocation.source || "manual",
    address: userLocation.address || "",
  };

  // Update hidden form fields
  Object.keys(fields).forEach((fieldId) => {
    let field = document.getElementById(fieldId);
    if (!field) {
      // Create hidden input if it doesn't exist
      field = document.createElement("input");
      field.type = "hidden";
      field.id = fieldId;
      field.name = fieldId;
      document.getElementById("checkinForm").appendChild(field);
    }
    field.value = fields[fieldId];
  });

  console.log("📝 Updated form fields with location data:", fields);
}

// Update location display
function updateLocationDisplay() {
  if (userLocation.latitude && userLocation.longitude) {
    const elements = {
      displayLatitude: userLocation.latitude.toFixed(6),
      displayLongitude: userLocation.longitude.toFixed(6),
      displayAccuracy: userLocation.accuracy
        ? `±${Math.round(userLocation.accuracy)}m`
        : "Unknown",
      displayAddress: userLocation.address || "Loading...",
    };

    Object.keys(elements).forEach((elementId) => {
      const element = document.getElementById(elementId);
      if (element) {
        element.textContent = elements[elementId];
      }
    });

    console.log("🖥️ Updated location display");
  }
}

// Start continuous location watching
function startLocationWatching() {
  if (!navigator.geolocation || locationWatchId !== null) {
    return;
  }

  const watchOptions = {
    enableHighAccuracy: true,
    timeout: 30000,
    maximumAge: 600000, // 10 minutes
  };

  locationWatchId = navigator.geolocation.watchPosition(
    handleLocationSuccess,
    (error) => {
      console.log("⚠️ Location watch error:", error);
      // Don't show error for watch failures, just log them
    },
    watchOptions
  );

  console.log("👁️ Started location watching");
}

// Stop location watching
function stopLocationWatching() {
  if (locationWatchId !== null) {
    navigator.geolocation.clearWatch(locationWatchId);
    locationWatchId = null;
    console.log("⏹️ Stopped location watching");
  }
}

// Reverse geocode coordinates to get address
function reverseGeocodeLocation(lat, lng) {
  console.log("🏠 Getting address from coordinates...");

  // Use a free geocoding service
  const geocodeUrl = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`;

  fetch(geocodeUrl)
    .then((response) => response.json())
    .then((data) => {
      if (data && (data.locality || data.city || data.principalSubdivision)) {
        const address = [
          data.locality || data.city,
          data.principalSubdivision,
          data.countryName,
        ]
          .filter(Boolean)
          .join(", ");

        userLocation.address = address;
        updateLocationFormFields();
        updateLocationDisplay();

        console.log("🏠 Address found:", address);
      } else {
        console.log("🏠 No address found");
        userLocation.address = "Address not available";
        updateLocationFormFields();
        updateLocationDisplay();
      }
    })
    .catch((error) => {
      console.log("⚠️ Geocoding error:", error);
      userLocation.address = "Address lookup failed";
      updateLocationFormFields();
      updateLocationDisplay();
    });
}

// Ensure location form fields exist
function ensureLocationFormFields() {
  const form = document.getElementById("checkinForm");
  if (!form) {
    console.log("⚠️ Check-in form not found");
    return;
  }

  const locationFields = [
    "latitude",
    "longitude",
    "accuracy",
    "altitude",
    "location_source",
    "address",
  ];

  locationFields.forEach((fieldName) => {
    if (!document.getElementById(fieldName)) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.id = fieldName;
      input.name = fieldName;
      input.value = "";
      form.appendChild(input);
      console.log(`✅ Created hidden field: ${fieldName}`);
    }
  });
}

// FORM SUBMISSION

// Submit check-in with location data
function submitCheckin(employeeId) {
  if (isSubmitting) {
    console.log("⏭️ Already submitting, ignoring duplicate request");
    return false;
  }

  isSubmitting = true;
  updateSubmitButton(true);
  hideStatusMessage();

  console.log("📤 Starting check-in submission for:", employeeId);
  console.log("📍 Current location data:", userLocation);

  // Ensure location data is in the form
  updateLocationFormFields();

  // Prepare form data
  const formData = new FormData();
  formData.append("employee_id", employeeId);

  // Add location data
  formData.append(
    "latitude",
    userLocation.latitude ? userLocation.latitude.toFixed(6) : ""
  );
  formData.append(
    "longitude",
    userLocation.longitude ? userLocation.longitude.toFixed(6) : ""
  );
  formData.append("accuracy", userLocation.accuracy || "");
  formData.append("altitude", userLocation.altitude || "");
  formData.append("location_source", userLocation.source || "manual");
  formData.append("address", userLocation.address || "");

  // Debug: Log exactly what we're sending
  console.log("📤 Form data being submitted:");
  for (let [key, value] of formData.entries()) {
    console.log(`   ${key}: "${value}"`);
  }

  // Get the current URL for the check-in endpoint
  const currentUrl = window.location.pathname;
  const checkinUrl = `${currentUrl}/checkin`;

  console.log("🎯 Submitting to URL:", checkinUrl);

  fetch(checkinUrl, {
    method: "POST",
    body: formData,
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((response) => {
      console.log("📡 Server response status:", response.status);
      console.log("📡 Server response headers:", response.headers);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return response.json();
    })
    .then((data) => {
      isSubmitting = false;
      updateSubmitButton(false);

      console.log(
        "📥 Complete server response:",
        JSON.stringify(data, null, 2)
      );

      if (data.success) {
        showSuccessPage(data);
        console.log(
          "✅ Check-in successful with location:",
          data.data?.has_location || false
        );

        // Stop location watching after successful check-in
        stopLocationWatching();
      } else {
        const errorMessage = data.message || data.error || "Check-in failed";
        showStatusMessage(errorMessage, "error");
        console.log("❌ Check-in failed:", errorMessage);
        console.log("❌ Full error response:", data);
      }
    })
    .catch((error) => {
      isSubmitting = false;
      updateSubmitButton(false);

      console.error("❌ Network/Parse error details:", error);
      console.error("❌ Error name:", error.name);
      console.error("❌ Error message:", error.message);
      console.error("❌ Error stack:", error.stack);

      let errorMessage =
        "Network error. Please check your connection and try again.";
      if (error.message.includes("JSON")) {
        errorMessage = "Server response error. Please try again.";
      } else if (error.message.includes("HTTP error")) {
        errorMessage =
          "Server error. Please contact support if this continues.";
      }

      showStatusMessage(errorMessage, "error");
    });
}

// UTILITY FUNCTIONS

// Update submit button state
function updateSubmitButton(isLoading) {
  const submitBtn = document.querySelector(
    '#checkinForm button[type="submit"]'
  );
  if (submitBtn) {
    if (isLoading) {
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Processing...';
    } else {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-check"></i> Check In';
    }
  }
}

// Show status messages
function showStatusMessage(message, type = "info") {
  console.log(`Status: ${type} - ${message}`);

  // Try to find existing status display element
  let statusEl = document.getElementById("statusMessage");
  if (!statusEl) {
    statusEl = document.createElement("div");
    statusEl.id = "statusMessage";
    statusEl.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 1000;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
    document.body.appendChild(statusEl);
  }

  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;

  // Style based on type
  if (type === "error") {
    statusEl.style.backgroundColor = "#fee2e2";
    statusEl.style.color = "#dc2626";
    statusEl.style.border = "1px solid #fecaca";
  } else if (type === "success") {
    statusEl.style.backgroundColor = "#dcfce7";
    statusEl.style.color = "#16a34a";
    statusEl.style.border = "1px solid #bbf7d0";
  } else {
    statusEl.style.backgroundColor = "#dbeafe";
    statusEl.style.color = "#2563eb";
    statusEl.style.border = "1px solid #bfdbfe";
  }

  statusEl.style.display = "block";

  // Auto-hide after 5 seconds
  setTimeout(() => {
    statusEl.style.display = "none";
  }, 5000);
}

// Hide status messages
function hideStatusMessage() {
  const statusEl = document.getElementById("statusMessage");
  if (statusEl) {
    statusEl.style.display = "none";
  }
}

// Enhanced location status display
function showLocationStatus(type, message) {
  const statusElement = document.getElementById("locationStatus");
  const messageElement = document.getElementById("locationMessage");

  if (statusElement && messageElement) {
    statusElement.className = `location-status ${type}`;
    messageElement.textContent = message;

    // Auto-hide success messages after 3 seconds
    if (type === "success") {
      setTimeout(() => {
        statusElement.style.display = "none";
      }, 3000);
    } else {
      statusElement.style.display = "block";
    }
  }

  console.log(`📍 Location status: ${type} - ${message}`);
}

// Show success page with safe data handling
function showSuccessPage(data) {
  console.log("🎉 Showing success page with data:", data);

  // Hide the form
  const form = document.getElementById("checkinForm");
  if (form) {
    form.style.display = "none";
  }

  // Safely extract data with fallbacks
  const responseData = data.data || data || {};
  const employeeId = responseData.employee_id || "Unknown";
  const location = responseData.location || "Unknown Location";
  const event = responseData.event || responseData.location_event || "Check-in";
  const checkInTime =
    responseData.check_in_time || new Date().toLocaleTimeString();
  const checkInDate =
    responseData.check_in_date || new Date().toLocaleDateString();
  const hasLocation = responseData.has_location || false;
  const locationInfo = responseData.location_info || null;

  console.log("📊 Processed success data:", {
    employeeId,
    location,
    event,
    checkInTime,
    checkInDate,
    hasLocation,
    locationInfo,
  });

  // Show success message
  showStatusMessage(`Check-in successful for ${employeeId}!`, "success");

  // Update success card if it exists
  const successCard = document.getElementById("successCard");
  if (successCard) {
    successCard.style.display = "block";

    // Update success details safely
    const updateElement = (id, value) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = value || "N/A";
        console.log(`✅ Updated ${id}: ${value}`);
      } else {
        console.log(`⚠️ Element not found: ${id}`);
      }
    };

    updateElement("successEmployeeId", employeeId);
    updateElement("successLocation", location);
    updateElement("successEvent", event);
    updateElement("successTime", checkInTime);
    updateElement("successDate", checkInDate);

    // Show location info if available
    if (hasLocation && locationInfo) {
      const locationInfoEl = document.getElementById("successLocationInfo");
      const gpsInfo = document.getElementById("successGpsInfo");
      if (locationInfoEl && gpsInfo) {
        const coordinates = locationInfo.coordinates || "Unknown coordinates";
        const accuracy = locationInfo.accuracy || "Unknown accuracy";
        gpsInfo.textContent = `${coordinates} (${accuracy})`;
        locationInfoEl.style.display = "block";
        console.log("✅ Updated GPS info display");
      }
    } else {
      console.log("📍 No location data to display");
    }
  } else {
    console.log("⚠️ Success card element not found, using fallback");

    // Create a simple success display
    const successMessage = document.createElement("div");
    successMessage.innerHTML = `
            <div style="
                background: #dcfce7;
                border: 1px solid #bbf7d0;
                color: #16a34a;
                padding: 20px;
                border-radius: 8px;
                margin: 20px;
                text-align: center;
            ">
                <h3>✅ Check-in Successful!</h3>
                <p><strong>Employee:</strong> ${employeeId}</p>
                <p><strong>Location:</strong> ${location}</p>
                <p><strong>Time:</strong> ${checkInTime}</p>
                ${hasLocation ? "<p>📍 Location data captured</p>" : ""}
                <button onclick="checkInAnother()" style="
                    background: #16a34a;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 10px;
                ">Check In Another Employee</button>
            </div>
        `;

    // Insert after the form
    if (form && form.parentNode) {
      form.parentNode.insertBefore(successMessage, form.nextSibling);
    } else {
      document.body.appendChild(successMessage);
    }

    // Auto-reload after 10 seconds as fallback
    setTimeout(() => {
      location.reload();
    }, 10000);
  }
}

// INTERACTIVE FUNCTIONS (called from HTML)

// Retry location request
function retryLocationRequest() {
  console.log("🔄 Retrying location request...");

  // Stop any existing watch
  stopLocationWatching();

  // Reset location data
  userLocation = {
    latitude: null,
    longitude: null,
    accuracy: null,
    altitude: null,
    timestamp: null,
    source: "manual",
    address: null,
  };

  // Clear form fields
  updateLocationFormFields();

  // Request location again
  requestUserLocation();
}

// Toggle location info display
function toggleLocationInfo() {
  const locationInfo = document.getElementById("locationInfo");
  if (!locationInfo) return;

  if (locationInfo.style.display === "none" || !locationInfo.style.display) {
    updateLocationDisplay();
    locationInfo.style.display = "block";
  } else {
    locationInfo.style.display = "none";
  }
}

// Check in another employee (reset form)
function checkInAnother() {
  // Reset form
  const form = document.getElementById("checkinForm");
  const successCard = document.getElementById("successCard");

  if (form) {
    form.style.display = "block";
    form.reset();
  }

  if (successCard) {
    successCard.style.display = "none";
  }

  // Reset location data and restart tracking
  userLocation = {
    latitude: null,
    longitude: null,
    accuracy: null,
    altitude: null,
    timestamp: null,
    source: "manual",
    address: null,
  };

  // Restart location tracking
  initializeGeolocation();

  // Focus on employee input
  const employeeInput = document.getElementById("employee_id");
  if (employeeInput) {
    employeeInput.focus();
  }

  hideStatusMessage();
}

// Get current location data (for external use)
function getCurrentLocationData() {
  return {
    hasLocation: !!(userLocation.latitude && userLocation.longitude),
    latitude: userLocation.latitude,
    longitude: userLocation.longitude,
    accuracy: userLocation.accuracy,
    altitude: userLocation.altitude,
    source: userLocation.source,
    timestamp: userLocation.timestamp,
    address: userLocation.address,
  };
}

console.log(
  "📍 QR Destination JavaScript loaded successfully with location tracking!"
);
