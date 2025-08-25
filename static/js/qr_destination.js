/**
 * QR Code Destination Page JavaScript - Enhanced with Multiple Check-ins Support
 * Handles staff check-in functionality with GPS location support, language switching, and 30-minute interval validation
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

// BILINGUAL FUNCTIONALITY
let currentLanguage = "en";
const translations = {
  en: {
    languageText: "ES",
    statusMessages: {
      processing: "Processing check-in...",
      success: "Check-in successful!",
      error: "Check-in failed. Please try again.",
      duplicate: "You have already checked in today.",
      tooSoon: "Please wait before checking in again.",
      multipleSuccess: "Submitted successfully!",
      invalidId: "Please enter a valid Employee ID.",
      locationError: "Unable to get location data.",
      networkError: "Network error. Please check your connection.",
    },
  },
  es: {
    languageText: "EN",
    statusMessages: {
      processing: "Procesando registro...",
      success: "¡Registro exitoso!",
      error: "Error en el registro. Por favor intente de nuevo.",
      duplicate: "Ya se ha registrado hoy.",
      tooSoon: "Por favor espere antes de registrarse nuevamente.",
      multipleSuccess: "Submitted successfully!!",
      invalidId: "Por favor ingrese un ID de empleado válido.",
      locationError: "No se pudo obtener datos de ubicación.",
      networkError: "Error de red. Verifique su conexión.",
    },
  },
};

// DOM Content Loaded Event (PRESERVED FROM ORIGINAL)
document.addEventListener("DOMContentLoaded", function () {
  console.log("🎯 QR Destination page loaded");

  // CRITICAL: Initialize systems in correct order
  initializeLanguage();
  initializeLocationServicesCheck();
  initializeStaffIdPersistence();
  initializeForm();
  initializeLocation();
  startClock();

  // Add fade-in animation to elements
  setTimeout(() => {
    document.querySelectorAll(".fade-transition").forEach((el) => {
      el.classList.add("active");
    });
  }, 100);
});

// ENHANCED STAFF ID PERSISTENCE FUNCTIONALITY
function initializeStaffIdPersistence() {
  console.log("👤 Initializing staff ID persistence functionality");
  
  // Load last staff ID from localStorage
  lastStaffId = loadLastStaffId();
  if (lastStaffId) {
    console.log(`📱 Found last staff ID: ${lastStaffId}`);
    
    // Automatically fill the last staff ID
    const employeeIdInput = document.getElementById("employee_id");
    if (employeeIdInput) {
      employeeIdInput.value = lastStaffId;
      validateEmployeeId();
      console.log(`✅ Auto-filled staff ID: ${lastStaffId}`);
    }
  } else {
    console.log("📱 No previous staff ID found");
  }
}

function loadLastStaffId() {
  try {
    const saved = localStorage.getItem('qr_last_staff_id');
    if (saved && saved.trim().length >= 2) {
      return saved.trim().toUpperCase();
    }
    console.log("📱 No valid last staff ID found");
    return null;
  } catch (error) {
    console.error("❌ Error loading last staff ID from localStorage:", error);
    return null;
  }
}

function saveLastStaffId(staffId) {
  try {
    if (!staffId || typeof staffId !== 'string' || staffId.trim().length < 2) {
      console.log("⚠️ Invalid staff ID, not saving");
      return false;
    }
    
    const cleanId = staffId.trim().toUpperCase();
    lastStaffId = cleanId;
    
    // Save to localStorage
    localStorage.setItem('qr_last_staff_id', cleanId);
    console.log(`💾 Last staff ID saved: ${cleanId}`);
    
    return true;
  } catch (error) {
    console.error("❌ Error saving last staff ID to localStorage:", error);
    return false;
  }
}

// ENHANCED FORM HANDLING FOR MULTIPLE CHECK-INS
function initializeForm() {
  const form = document.getElementById("checkinForm");
  const submitButton = document.getElementById("submitCheckin");

  if (form && submitButton) {
    form.addEventListener("submit", handleFormSubmit);

    // Add real-time Employee ID validation
    const employeeIdInput = document.getElementById("employee_id");
    if (employeeIdInput) {
      employeeIdInput.addEventListener("input", validateEmployeeId);
      employeeIdInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          handleFormSubmit(e);
        }
      });
    }
  }
}

function handleFormSubmit(event) {
  event.preventDefault();

  if (isSubmitting) {
    console.log(
      "⏳ Check-in already in progress, ignoring duplicate submission"
    );
    return;
  }

  console.log("🎯 Form submission triggered");

  const employeeId = document.getElementById("employee_id")?.value?.trim();

  if (!employeeId) {
    showLocalizedStatusMessage("invalidId", "error");
    return;
  }

  if (employeeId.length < 2) {
    showLocalizedStatusMessage("invalidId", "error");
    return;
  }

  // Save the staff ID for future use
  saveLastStaffId(employeeId);

  // Show processing status
  showLocalizedStatusMessage("processing", "info");

  // Submit the check-in
  submitCheckin();
}

// ENHANCED CHECK-IN SUBMISSION WITH MULTIPLE CHECK-IN SUPPORT
function submitCheckin() {
  console.log("🚀 Starting check-in submission process");

  if (isSubmitting) {
    console.log("⏳ Already submitting, aborting");
    return;
  }

  isSubmitting = true;
  updateSubmitButton(true);

  const employeeId = document.getElementById("employee_id").value.trim();

  if (!employeeId) {
    showLocalizedStatusMessage("invalidId", "error");
    isSubmitting = false;
    updateSubmitButton(false);
    return;
  }

  console.log(`👤 Employee ID: ${employeeId}`);
  console.log(`📍 User location:`, userLocation);

  // Prepare form data
  const formData = new FormData();
  formData.append("employee_id", employeeId);
  formData.append(
    "latitude",
    userLocation.latitude ? userLocation.latitude.toFixed(10) : ""
  );
  formData.append(
    "longitude",
    userLocation.longitude ? userLocation.longitude.toFixed(10) : ""
  );
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

// ENHANCED RESPONSE HANDLING FOR MULTIPLE CHECK-INS
function handleCheckinResponse(data) {
  if (data.success) {
    handleCheckinSuccess(data);
  } else {
    const errorMsg = data.message || "Submission failed";
    console.log("❌ Submission failed:", errorMsg);

    // NEW: Handle different types of check-in failures
    if (errorMsg.toLowerCase().includes("already submitted")) {
      showLocalizedStatusMessage("duplicate", "warning");
    } else if (
      errorMsg.toLowerCase().includes("submit again in") ||
      errorMsg.toLowerCase().includes("minutes")
    ) {
      // Handle 30-minute interval message
      showCustomStatusMessage(errorMsg, "warning");
    } else {
      showLocalizedStatusMessage("error", "error");
    }
  }
}

// ENHANCED SUCCESS HANDLING WITH MULTIPLE CHECK-IN INFO
function handleCheckinSuccess(data) {
  console.log("✅ Submitted successfully!");

  const responseData = data.data || data || {};
  const checkinCount = responseData.checkin_count_today || 1;
  const checkinSequence = responseData.checkin_sequence || "Check-in";

  // Show appropriate success message based on check-in count
  if (checkinCount > 1) {
    showLocalizedStatusMessage("multipleSuccess", "success");
  } else {
    showLocalizedStatusMessage("success", "success");
  }

  // Hide form (PRESERVED FROM ORIGINAL)
  const form = document.getElementById("checkinForm");
  if (form) {
    form.style.display = "none";
  }

  // Update success card with enhanced information
  const successCard = document.getElementById("successCard");
  if (successCard) {
    successCard.style.display = "block";
    successCard.classList.add("active");

    const updateElement = (id, value) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = value || "N/A";
      }
    };

    const employeeId = responseData.employee_id || "Unknown";
    const location = responseData.location || "Unknown Location";
    const event =
      responseData.event || responseData.location_event || "Check-in";
    const checkInTime =
      responseData.check_in_time || new Date().toLocaleTimeString();
    const checkInDate =
      responseData.check_in_date || new Date().toLocaleDateString();

    updateElement("successEmployeeId", employeeId);
    updateElement("successLocation", location);
    updateElement("successEvent", event);
    updateElement("successCheckInTime", checkInTime);
    updateElement("successCheckInDate", checkInDate);

    // NEW: Add check-in sequence information
    updateElement("successCheckinSequence", checkinSequence);

    // Update additional info if available
    if (responseData.device_info) {
      updateElement("successDeviceInfo", responseData.device_info);
    }

    if (responseData.coordinates) {
      updateElement("successCoordinates", responseData.coordinates);
    }

    if (responseData.address) {
      updateElement("successAddress", responseData.address);
    }

    if (responseData.location_accuracy) {
      updateElement(
        "successLocationAccuracy",
        `${responseData.location_accuracy} miles`
      );
    }
  }

  // NEW: Add option to check in again after success
  //setTimeout(() => {
  //  addCheckInAgainOption();
  //}, 3000);
}

// NEW: Add option to check in again
function addCheckInAgainOption() {
  const successCard = document.getElementById("successCard");
  if (successCard && !document.getElementById("checkInAgainButton")) {
    const checkInAgainHtml = `
      <div class="check-in-again-section" style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e0e4e7;">
        <p class="check-in-again-text" style="margin-bottom: 1rem; color: #64748b; font-size: 0.9rem;">
          <span data-en="Need to check in again? You can do so after 30 minutes." 
                data-es="¿Necesita registrarse nuevamente? Puede hacerlo después de 30 minutos.">
            Need to check in again? You can do so after 30 minutes.
          </span>
        </p>
        <button id="checkInAgainButton" class="btn btn-outline" style="width: 100%;" onclick="resetForNewCheckin()">
          <i class="fas fa-redo"></i>
          <span data-en="Check In Again" data-es="Registrarse Nuevamente">Check In Again</span>
        </button>
      </div>
    `;
    successCard.insertAdjacentHTML("beforeend", checkInAgainHtml);

    // Apply current language translations
    applyTranslations();
  }
}

// NEW: Reset form for new check-in
function resetForNewCheckin() {
  console.log("🔄 Resetting for new check-in");

  // Show form again
  const form = document.getElementById("checkinForm");
  if (form) {
    form.style.display = "block";
  }

  // Hide success card
  const successCard = document.getElementById("successCard");
  if (successCard) {
    successCard.style.display = "none";
    successCard.classList.remove("active");
  }

  // Clear previous employee ID
  const employeeIdInput = document.getElementById("employee_id");
  if (employeeIdInput) {
    employeeIdInput.value = "";
    employeeIdInput.focus();
  }

  // Clear status messages
  clearStatusMessages();

  // Reset location if needed
  if (!userLocation.latitude || !userLocation.longitude) {
    requestLocationData();
  }
}

// NEW: Show custom status message (for interval warnings)
function showCustomStatusMessage(message, type = "info") {
  const statusContainer = document.getElementById("statusMessage");
  if (statusContainer) {
    statusContainer.className = `status-message ${type}`;
    statusContainer.innerHTML = `
      <div class="status-content">
        <i class="fas ${getStatusIcon(type)}"></i>
        <span>${message}</span>
      </div>
    `;
    statusContainer.style.display = "block";

    // Auto-hide after 5 seconds
    setTimeout(() => {
      statusContainer.style.display = "none";
    }, 5000);
  }
}

// Helper function to get appropriate icon for status type
function getStatusIcon(type) {
  switch (type) {
    case "success":
      return "fa-check-circle";
    case "error":
      return "fa-exclamation-circle";
    case "warning":
      return "fa-clock";
    case "info":
    default:
      return "fa-info-circle";
  }
}

// PRESERVED: All other existing functions remain unchanged
function showLocalizedStatusMessage(messageKey, type = "info") {
  const message =
    translations[currentLanguage].statusMessages[messageKey] ||
    translations["en"].statusMessages[messageKey] ||
    "Status update";

  showCustomStatusMessage(message, type);
}

function clearStatusMessages() {
  const statusContainer = document.getElementById("statusMessage");
  if (statusContainer) {
    statusContainer.style.display = "none";
  }
}

function handleCheckinError(error) {
  console.error("❌ Check-in submission error:", error);
  showLocalizedStatusMessage("networkError", "error");
}

function updateSubmitButton(isLoading) {
  const submitButton = document.getElementById("submitCheckin");
  if (submitButton) {
    if (isLoading) {
      submitButton.disabled = true;
      submitButton.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> <span data-en="Processing..." data-es="Procesando...">Processing...</span>';
    } else {
      submitButton.disabled = false;
      submitButton.innerHTML =
        '<i class="fas fa-user-check"></i> <span data-en="Submit" data-es="Someter">Submit</span>';
    }
    applyTranslations();
  }
}

function validateEmployeeId() {
  const employeeIdInput = document.getElementById("employee_id");
  const submitButton = document.getElementById("submitCheckin");

  if (employeeIdInput && submitButton) {
    const isValid = employeeIdInput.value.trim().length >= 2;
    submitButton.disabled = !isValid || isSubmitting;

    if (isValid) {
      employeeIdInput.classList.remove("invalid");
      employeeIdInput.classList.add("valid");
    } else {
      employeeIdInput.classList.remove("valid");
      if (employeeIdInput.value.length > 0) {
        employeeIdInput.classList.add("invalid");
      }
    }
  }
}

// All location and language functions remain unchanged from original
function initializeLocation() {
  console.log("📍 Initializing location services");
  requestLocationData();
}

function requestLocationData() {
  if (locationRequestActive) {
    console.log("📍 Location request already active, skipping");
    return;
  }

  if (!navigator.geolocation) {
    console.log("❌ Geolocation not supported");
    userLocation.source = "manual";
    return;
  }

  locationRequestActive = true;
  console.log("📍 Requesting location data...");

  const options = {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 300000,
  };

  navigator.geolocation.getCurrentPosition(
    handleLocationSuccess,
    handleLocationError,
    options
  );
}

function handleLocationSuccess(position) {
  console.log("✅ Location obtained successfully");

  userLocation = {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy,
    altitude: position.coords.altitude,
    timestamp: new Date(),
    source: "gps",
    address: null,
  };

  console.log("📍 Location data:", userLocation);

  // Reverse geocode to get address
  reverseGeocode(userLocation.latitude, userLocation.longitude);

  locationRequestActive = false;
}

function handleLocationError(error) {
  console.log("❌ Location error:", error.message);
  userLocation.source = "manual";
  locationRequestActive = false;
}

function reverseGeocode(lat, lng) {
  console.log(`🌍 Reverse geocoding for: ${lat}, ${lng}`);

  // The server will use Google Maps API first, then fall back to OpenStreetMap
  // This provides better accuracy and address formatting
  const url = '/api/reverse-geocode'; // You may want to create this endpoint
  
  // For now, using direct OpenStreetMap as fallback
  // In production, this should go through your server API
  const osmUrl = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&addressdetails=1&zoom=18`;

  fetch(osmUrl, {
    method: "GET",
    headers: {
      "User-Agent": "QR-Attendance-System/1.0",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data && data.display_name) {
        userLocation.address = data.display_name;
        console.log(`✅ Reverse geocoded address: ${userLocation.address}`);
      } else {
        console.log(`⚠️ No address found, using coordinates as fallback`);
        userLocation.address = `${lat.toFixed(10)}, ${lng.toFixed(10)}`;
      }
    })
    .catch((error) => {
      console.error(`❌ Reverse geocoding error:`, error);
      // Fallback to coordinates if reverse geocoding fails
      userLocation.address = `${lat.toFixed(10)}, ${lng.toFixed(10)}`;
    });
}

// ENHANCED LANGUAGE FUNCTIONALITY WITH PERSISTENCE
function initializeLanguage() {
  console.log("🌐 Initializing language functionality with persistence");
  
  // Load saved language preference from localStorage
  const savedLanguage = loadLanguagePreference();
  if (savedLanguage && savedLanguage !== currentLanguage) {
    currentLanguage = savedLanguage;
    console.log(`📱 Restored saved language preference: ${currentLanguage}`);
  }

  // Set up language toggle button event listener
  const languageToggle = document.getElementById("languageToggle");
  if (languageToggle) {
    languageToggle.addEventListener("click", toggleLanguage);
  }

  // Apply initial translations based on loaded language
  applyTranslations();
  console.log(`✅ Language system initialized with: ${currentLanguage}`);
}

function toggleLanguage() {
  // Switch between languages
  const newLanguage = currentLanguage === "en" ? "es" : "en";
  currentLanguage = newLanguage;
  
  // Save new language preference to localStorage
  saveLanguagePreference(currentLanguage);
  
  // Apply translations immediately
  applyTranslations();
  
  console.log(`🌐 Language switched to: ${currentLanguage} (saved to localStorage)`);
  
  // Optional: Show brief confirmation message
  showLanguageChangeConfirmation();
}

function loadLanguagePreference() {
  try {
    // Retrieve language preference from localStorage
    const savedLanguage = localStorage.getItem('qr_staff_language');
    
    // Validate saved language is supported
    if (savedLanguage && translations.hasOwnProperty(savedLanguage)) {
      console.log(`📱 Found saved language preference: ${savedLanguage}`);
      return savedLanguage;
    } else if (savedLanguage) {
      console.log(`⚠️ Invalid saved language preference: ${savedLanguage}, using default`);
      // Clean up invalid preference
      localStorage.removeItem('qr_staff_language');
    } else {
      console.log("📱 No saved language preference found, using default");
    }
    
    return null;
  } catch (error) {
    console.error("❌ Error loading language preference from localStorage:", error);
    return null;
  }
}

function saveLanguagePreference(language) {
  try {
    // Validate language before saving
    if (!translations.hasOwnProperty(language)) {
      console.error(`❌ Invalid language code: ${language}`);
      return false;
    }
    
    // Save to localStorage
    localStorage.setItem('qr_staff_language', language);
    console.log(`💾 Language preference saved: ${language}`);
    return true;
  } catch (error) {
    console.error("❌ Error saving language preference to localStorage:", error);
    return false;
  }
}

function showLanguageChangeConfirmation() {
  // Brief visual feedback for language change
  const languageToggle = document.getElementById("languageToggle");
  if (languageToggle) {
    // Add temporary visual feedback
    languageToggle.style.transform = "scale(1.05)";
    languageToggle.style.background = "rgba(255, 255, 255, 0.4)";
    
    setTimeout(() => {
      languageToggle.style.transform = "";
      languageToggle.style.background = "";
    }, 200);
  }
}

function applyTranslations() {
  // Update language toggle button text
  const languageText = document.getElementById("languageText");
  if (languageText) {
    languageText.textContent = translations[currentLanguage].languageText;
  }

  // Apply translations to all elements with data attributes
  document.querySelectorAll(`[data-${currentLanguage}]`).forEach((element) => {
    element.textContent = element.getAttribute(`data-${currentLanguage}`);
  });
  
  // Update any dynamic content that might have been generated after initial load
  updateDynamicTranslations();
}

function updateDynamicTranslations() {
  // Update submit button text if it exists and has been modified
  const submitButton = document.getElementById("submitCheckin");
  if (submitButton && submitButton.innerHTML.includes('data-')) {
    // Re-apply translations to submit button content
    const spans = submitButton.querySelectorAll(`[data-${currentLanguage}]`);
    spans.forEach((span) => {
      span.textContent = span.getAttribute(`data-${currentLanguage}`);
    });
  }
}

function startClock() {
  function updateClock() {
    currentTime = new Date();
    const timeElements = document.querySelectorAll(".current-time");
    timeElements.forEach((el) => {
      el.textContent = currentTime.toLocaleTimeString();
    });
  }

  updateClock();
  setInterval(updateClock, 1000);
}

function checkLocationServicesStatus() {
  console.log("📱 Checking location services status...");
  
  // Check if geolocation is supported
  if (!navigator.geolocation) {
    console.log("❌ Geolocation not supported by this browser");
    showLocationServicesWarning("not_supported");
    return;
  }

  // Test location access with a quick check
  const timeoutId = setTimeout(() => {
    console.log("⏰ Location permission check timed out");
    showLocationServicesWarning("timeout");
  }, 3000); // 3 second timeout

  navigator.geolocation.getCurrentPosition(
    (position) => {
      // Success - location services are working
      clearTimeout(timeoutId);
      console.log("✅ Location services are available and enabled");
      hideLocationServicesWarning();
    },
    (error) => {
      // Error - location services may be disabled
      clearTimeout(timeoutId);
      console.log("❌ Location services error:", error.message);
      
      switch (error.code) {
        case error.PERMISSION_DENIED:
          showLocationServicesWarning("permission_denied");
          break;
        case error.POSITION_UNAVAILABLE:
          showLocationServicesWarning("position_unavailable");
          break;
        case error.TIMEOUT:
          showLocationServicesWarning("timeout");
          break;
        default:
          showLocationServicesWarning("unknown_error");
          break;
      }
    },
    {
      enableHighAccuracy: false,
      timeout: 2500,
      maximumAge: 60000
    }
  );
}

/**
 * Show location services warning banner
 */
function showLocationServicesWarning(errorType) {
  // Remove existing warning if present
  hideLocationServicesWarning();
  
  const warningMessages = {
    en: {
      not_supported: "Location services are not supported by your browser.<br>Los servicios de ubicación no son compatibles con su navegador.",
      permission_denied: "Location access has been denied. Please enable location services for accurate check-in.<br>Se ha denegado el acceso a la ubicación. Habilite los servicios de ubicación para un registro preciso.",
      position_unavailable: "Location services appear to be disabled. Please turn on location services for accurate check-in.<br>Los servicios de ubicación parecen estar deshabilitados. Active los servicios de ubicación para un registro preciso.",
      timeout: "Location services may be disabled. Please check your location settings for accurate check-in.<br>Los servicios de ubicación pueden estar deshabilitados. Verifique su configuración de ubicación para un registro preciso.",
      unknown_error: "Unable to access location services. Please check your location settings.<br>No se puede acceder a los servicios de ubicación. Verifique su configuración de ubicación."
    },
    es: {
      not_supported: "Los servicios de ubicación no son compatibles con su navegador.",
      permission_denied: "Se ha denegado el acceso a la ubicación. Habilite los servicios de ubicación para un registro preciso.",
      position_unavailable: "Los servicios de ubicación parecen estar deshabilitados. Active los servicios de ubicación para un registro preciso.",
      timeout: "Los servicios de ubicación pueden estar deshabilitados. Verifique su configuración de ubicación para un registro preciso.",
      unknown_error: "No se puede acceder a los servicios de ubicación. Verifique su configuración de ubicación."
    }
  };

  const currentLang = currentLanguage || 'en';
  const message = warningMessages[currentLang][errorType] || warningMessages['en'][errorType];
  
  // Create warning banner
  const warningBanner = document.createElement('div');
  warningBanner.id = 'locationServicesWarning';
  warningBanner.className = 'location-warning-banner';
  warningBanner.innerHTML = `
    <div class="warning-content">
      <i class="fas fa-exclamation-triangle warning-icon"></i>
      <div class="warning-text">
        <span class="warning-message">${message}</span>
        <div class="warning-actions">
          <button type="button" class="warning-retry-btn" onclick="checkLocationServicesStatus()">
            <i class="fas fa-redo"></i>
            <span class="english-text">Retry</span>
            <span class="language-separator">/</span>
            <span class="spanish-text">Reintentar</span>
          </button>
          <button type="button" class="warning-dismiss-btn" onclick="hideLocationServicesWarning()">
            <i class="fas fa-times"></i>
            <span class="english-text">Dismiss</span>
            <span class="language-separator">/</span>
            <span class="spanish-text">Descartar</span>
          </button>
        </div>
      </div>
    </div>
  `;

  // Insert warning at the top of the page
  const container = document.querySelector('.destination-container');
  if (container) {
    container.insertBefore(warningBanner, container.firstChild);
  }

  // Log warning event
  console.log(`⚠️ Location services warning displayed: ${errorType}`);
}

/**
 * Hide location services warning banner
 */
function hideLocationServicesWarning() {
  const existingWarning = document.getElementById('locationServicesWarning');
  if (existingWarning) {
    existingWarning.remove();
    console.log("✅ Location services warning hidden");
  }
}

/**
 * Modified DOMContentLoaded event handler
 * Add this to your existing initialization
 */
function initializeLocationServicesCheck() {
  // Check location services status when page loads
  setTimeout(() => {
    checkLocationServicesStatus();
  }, 1000); // Small delay to ensure page is fully loaded
  
  // Also check before form submission
  const originalHandleFormSubmit = handleFormSubmit;
  window.handleFormSubmit = function(event) {
    // Quick location check before submission
    checkLocationServicesStatus();
    
    // Continue with original form submission after brief delay
    setTimeout(() => {
      originalHandleFormSubmit.call(this, event);
    }, 500);
  };
}
