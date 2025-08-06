/**
 * QR Code Destination Page JavaScript - Enhanced with Bilingual Support
 * Handles staff check-in functionality with GPS location support and language switching
 */

// Global variables (PRESERVED FROM ORIGINAL)
let isSubmitting = false;
let currentTime = new Date();

// Location tracking variables (PRESERVED FROM ORIGINAL)
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

// BILINGUAL FUNCTIONALITY - NEW FEATURE
let currentLanguage = 'en';
const translations = {
  en: {
    languageText: 'EN',
    statusMessages: {
      processing: 'Processing check-in...',
      success: 'Check-in successful!',
      error: 'Check-in failed. Please try again.',
      duplicate: 'You have already checked in today.',
      invalidId: 'Please enter a valid Employee ID.',
      locationError: 'Unable to get location data.',
      networkError: 'Network error. Please check your connection.'
    }
  },
  es: {
    languageText: 'ES',
    statusMessages: {
      processing: 'Procesando registro...',
      success: '¡Registro exitoso!',
      error: 'Error en el registro. Por favor intente de nuevo.',
      duplicate: 'Ya se ha registrado hoy.',
      invalidId: 'Por favor ingrese un ID de empleado válido.',
      locationError: 'No se pudo obtener datos de ubicación.',
      networkError: 'Error de red. Verifique su conexión.'
    }
  }
};

// Initialize page when DOM is loaded (ENHANCED VERSION)
document.addEventListener("DOMContentLoaded", function () {
  console.log(
    "🚀 QR Destination page initialized with enhanced location tracking and bilingual support"
  );

  // Initialize the page
  initializePage();
  setupEventListeners();
  startTimeUpdater();

  // Initialize geolocation
  initializeGeolocation();

  // Add hidden form fields for location data
  ensureLocationFormFields();

  // Initialize language system
  initializeLanguageSystem();

  // NEW: Start location watching for continuous updates
  startLocationWatching();
});

// BILINGUAL FUNCTIONS - NEW FEATURE
function initializeLanguageSystem() {
  console.log("🌐 Initializing bilingual system...");
  
  // Check for stored language preference
  const storedLanguage = localStorage.getItem('preferredLanguage');
  if (storedLanguage && ['en', 'es'].includes(storedLanguage)) {
    currentLanguage = storedLanguage;
  }
  
  // Apply initial language immediately
  setTimeout(() => {
    updateLanguage();
    // Initialize transitions after language is set
    const elements = document.querySelectorAll('.fade-transition');
    elements.forEach(el => el.classList.add('active'));
  }, 100);
}

// Language toggle function - FIXED VERSION
window.toggleLanguage = function() {
  console.log("🌐 Language toggle clicked");
  
  // Switch language
  currentLanguage = currentLanguage === 'en' ? 'es' : 'en';
  console.log("🌐 Switching to:", currentLanguage);
  
  // Store preference
  localStorage.setItem('preferredLanguage', currentLanguage);
  
  // Update language immediately without animations interfering
  updateLanguage();
  
  console.log("✅ Language switched successfully to:", currentLanguage);
};

// Update all text content based on current language - FIXED VERSION
function updateLanguage() {
  console.log("🔄 Updating language to:", currentLanguage);
  
  // Update all translatable elements
  const langAttr = currentLanguage === 'en' ? 'data-en' : 'data-es';
  const elements = document.querySelectorAll(`[${langAttr}]`);
  
  elements.forEach(element => {
    const text = element.getAttribute(langAttr);
    if (text) {
      element.textContent = text;
    }
  });

  // Update placeholder text
  const employeeInput = document.getElementById('employee_id');
  if (employeeInput) {
    const placeholderAttr = currentLanguage === 'en' ? 'data-placeholder-en' : 'data-placeholder-es';
    const placeholder = employeeInput.getAttribute(placeholderAttr);
    if (placeholder) {
      employeeInput.placeholder = placeholder;
    }
  }

  // Update language toggle button text
  const languageText = document.getElementById('languageText');
  if (languageText) {
    languageText.textContent = translations[currentLanguage].languageText;
  }

  // Update HTML lang attribute
  document.documentElement.lang = currentLanguage;
  
  // Force a repaint to ensure changes are visible
  document.body.style.display = 'none';
  document.body.offsetHeight; // Trigger reflow
  document.body.style.display = '';
}

// Enhanced status message function with translation support
function showLocalizedStatusMessage(messageKey, type = 'info') {
  const message = translations[currentLanguage].statusMessages[messageKey] || messageKey;
  const statusElement = document.getElementById('statusMessage');
  
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;
    statusElement.style.display = 'block';
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
      setTimeout(() => {
        statusElement.style.display = 'none';
      }, 5000);
    }
  }
}

// Initialize basic page functionality (PRESERVED FROM ORIGINAL)
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

// Set up event listeners (ENHANCED VERSION)
function setupEventListeners() {
  console.log("🎧 Setting up event listeners...");

  const form = document.getElementById("checkinForm");
  const employeeInput = document.getElementById("employee_id");
  const languageToggle = document.getElementById("languageToggle");

  if (form) {
    form.addEventListener("submit", handleFormSubmit);
  }

  if (employeeInput) {
    employeeInput.addEventListener("input", handleInputChange);
    employeeInput.addEventListener("keypress", handleKeyPress);
  }

  // Set up language toggle button
  if (languageToggle) {
    languageToggle.addEventListener("click", function(e) {
      e.preventDefault();
      e.stopPropagation();
      window.toggleLanguage();
    });
    console.log("✅ Language toggle button event listener attached");
  }
}

// Start time updater (PRESERVED FROM ORIGINAL)
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

// Handle form submission (PRESERVED FROM ORIGINAL)
function handleFormSubmit(e) {
  e.preventDefault();

  if (isSubmitting) {
    return false;
  }

  const employeeId = document.getElementById("employee_id").value.trim();

  if (!validateEmployeeId(employeeId)) {
    return false;
  }

  submitCheckin(employeeId);
  return false;
}

// Validate employee ID (ENHANCED WITH TRANSLATION)
function validateEmployeeId(employeeId) {
  if (!employeeId) {
    showLocalizedStatusMessage('invalidId', 'error');
    return false;
  }

  if (employeeId.length < 3 || employeeId.length > 20) {
    showLocalizedStatusMessage('invalidId', 'error');
    return false;
  }

  return true;
}

// Handle input change (PRESERVED FROM ORIGINAL)
function handleInputChange(e) {
  const value = e.target.value.trim();
  
  // Clear any existing error messages
  hideStatusMessage();
}

// Handle key press (PRESERVED FROM ORIGINAL)
function handleKeyPress(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    const form = document.getElementById('checkinForm');
    if (form) {
      form.dispatchEvent(new Event('submit'));
    }
  }
}

// Update submit button state (ENHANCED WITH TRANSLATION)
function updateSubmitButton(loading) {
  const button = document.querySelector('button[type="submit"]');
  const content = button?.querySelector('.btn-content');
  const loader = button?.querySelector('.btn-loader');

  if (!button) return;

  if (loading) {
    button.disabled = true;
    if (content) content.style.display = 'none';
    if (loader) loader.style.display = 'flex';
    showLocalizedStatusMessage('processing', 'info');
  } else {
    button.disabled = false;
    if (content) content.style.display = 'flex';
    if (loader) loader.style.display = 'none';
  }
}

// Hide status message (PRESERVED FROM ORIGINAL)
function hideStatusMessage() {
  const statusElement = document.getElementById('statusMessage');
  if (statusElement) {
    statusElement.style.display = 'none';
  }
}

// Enhanced showStatusMessage with translation support
window.showStatusMessage = function(message, type) {
  // Try to find translation key, fallback to original message
  const messageKeys = Object.keys(translations.en.statusMessages);
  const foundKey = messageKeys.find(key => 
    translations.en.statusMessages[key].toLowerCase().includes(message.toLowerCase()) ||
    message.toLowerCase().includes(translations.en.statusMessages[key].toLowerCase())
  );
  
  if (foundKey) {
    showLocalizedStatusMessage(foundKey, type);
  } else {
    // Fallback to original functionality
    const statusElement = document.getElementById('statusMessage');
    if (statusElement) {
      statusElement.textContent = message;
      statusElement.className = `status-message ${type}`;
      statusElement.style.display = 'block';
    }
  }
};

// GEOLOCATION FUNCTIONS (PRESERVED FROM ORIGINAL)
function initializeGeolocation() {
  console.log("📍 Initializing geolocation...");
  
  if (!navigator.geolocation) {
    console.log("❌ Geolocation not supported");
    showLocalizedStatusMessage('locationError', 'warning');
    return;
  }

  requestLocationPermission();
}

// NEW: Reverse geocode coordinates to get address
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

        console.log("🏠 Address found:", address);
      } else {
        console.log("🏠 No address found");
        userLocation.address = "Address not available";
        updateLocationFormFields();
      }
    })
    .catch((error) => {
      console.log("⚠️ Geocoding error:", error);
      userLocation.address = "Address lookup failed";
      updateLocationFormFields();
    });
}

function requestLocationPermission() {
  if (locationRequestActive) {
    console.log("⏭️ Location request already active, skipping...");
    return;
  }

  locationRequestActive = true;
  console.log("📍 Requesting location permission...");

  const options = {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 300000 // 5 minutes
  };

  navigator.geolocation.getCurrentPosition(
    handleLocationSuccess,
    handleLocationError,
    options
  );
}

function handleLocationSuccess(position) {
  console.log("✅ Location acquired successfully!");
  
  userLocation = {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy,
    altitude: position.coords.altitude,
    timestamp: new Date().toISOString(),
    source: "gps"
  };

  locationRequestActive = false;
  updateLocationFormFields();
  
  // NEW: Convert coordinates to address
  reverseGeocodeLocation(userLocation.latitude, userLocation.longitude);
  
  console.log("📍 Location data:", userLocation);
}

function handleLocationError(error) {
  console.log("❌ Location error:", error.message);
  locationRequestActive = false;
  
  // Don't show error message - just continue without location
  userLocation.source = "manual";
  userLocation.timestamp = new Date().toISOString();
}

// REST OF YOUR ORIGINAL FUNCTIONS (PRESERVED)
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

function updateLocationFormFields() {
  const fields = {
    latitude: userLocation.latitude ? userLocation.latitude.toFixed(8) : "",
    longitude: userLocation.longitude ? userLocation.longitude.toFixed(8) : "",
    accuracy: userLocation.accuracy || "",
    altitude: userLocation.altitude || "",
    locationSource: userLocation.source || "manual",
    address: userLocation.address || ""  // RESTORED: Address field population
  };

  Object.keys(fields).forEach(fieldName => {
    const field = document.getElementById(fieldName);
    if (field) {
      field.value = fields[fieldName];
      console.log(`📝 Updated field ${fieldName}: ${fields[fieldName]}`);
    }
  });
}

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

  updateLocationFormFields();

  const formData = new FormData();
  formData.append("employee_id", employeeId);
  formData.append("latitude", userLocation.latitude ? userLocation.latitude.toFixed(8) : "");
  formData.append("longitude", userLocation.longitude ? userLocation.longitude.toFixed(8) : "");
  formData.append("accuracy", userLocation.accuracy || "");
  formData.append("altitude", userLocation.altitude || "");
  formData.append("location_source", userLocation.source || "manual");
  formData.append("address", userLocation.address || "");

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
      return response.json();
    })
    .then((data) => {
      console.log("📊 Server response data:", data);
      handleCheckinResponse(data);
    })
    .catch((error) => {
      console.error("❌ Check-in error:", error);
      handleCheckinError(error);
    })
    .finally(() => {
      isSubmitting = false;
      updateSubmitButton(false);
    });
}

function handleCheckinResponse(data) {
  if (data.success) {
    handleCheckinSuccess(data);
  } else {
    const errorMsg = data.message || 'Check-in failed';
    if (errorMsg.toLowerCase().includes('already checked in')) {
      showLocalizedStatusMessage('duplicate', 'warning');
    } else {
      showLocalizedStatusMessage('error', 'error');
    }
  }
}

function handleCheckinSuccess(data) {
  console.log("✅ Check-in successful!");
  
  const form = document.getElementById("checkinForm");
  if (form) {
    form.style.display = "none";
  }

  const responseData = data.data || data || {};
  const employeeId = responseData.employee_id || "Unknown";
  const location = responseData.location || "Unknown Location";
  const event = responseData.event || responseData.location_event || "Check-in";
  const checkInTime = responseData.check_in_time || new Date().toLocaleTimeString();
  const checkInDate = responseData.check_in_date || new Date().toLocaleDateString();

  showLocalizedStatusMessage('success', 'success');

  const successCard = document.getElementById("successCard");
  if (successCard) {
    successCard.style.display = "block";
    successCard.classList.add('active');

    const updateElement = (id, value) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = value || "N/A";
      }
    };

    updateElement("successEmployeeId", employeeId);
    updateElement("successLocation", location);
    updateElement("successEvent", event);
    updateElement("successTime", checkInTime);
    updateElement("successDate", checkInDate);
  }
}

function handleCheckinError(error) {
  console.error("❌ Check-in submission failed:", error);
  showLocalizedStatusMessage('networkError', 'error');
}

// Check in another employee function (PRESERVED WITH TRANSLATION)
window.checkInAnother = function() {
  const form = document.getElementById("checkinForm");
  const successCard = document.getElementById("successCard");
  const employeeInput = document.getElementById("employee_id");

  if (form) form.style.display = "block";
  if (successCard) successCard.style.display = "none";
  if (employeeInput) {
    employeeInput.value = "";
    employeeInput.focus();
  }

  hideStatusMessage();
  console.log("🔄 Ready for another check-in");
};

// NEW: Start continuous location watching
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

// NEW: Stop location watching
function stopLocationWatching() {
  if (locationWatchId !== null) {
    navigator.geolocation.clearWatch(locationWatchId);
    locationWatchId = null;
    console.log("⏹️ Stopped location watching");
  }
}

// NEW: Show location status with translations
function showLocationStatus(type, messageKey) {
  const message = translations[currentLanguage].statusMessages[messageKey] || messageKey;
  
  let icon = '📡';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '⚠️';
  
  console.log(`${icon} Location Status: ${message}`);
  
  // You can enhance this to show a visual status indicator if needed
  showLocalizedStatusMessage(messageKey, type);
}

console.log("📍 QR Destination JavaScript loaded successfully with location tracking and bilingual support!");