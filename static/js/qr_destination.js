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
  // CRITICAL: Disable form FIRST before anything else
  window.locationServicesBlocked = true;
  disableFormImmediately();
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
  // Load last staff ID from localStorage
  lastStaffId = loadLastStaffId();
  if (lastStaffId) {
    // Automatically fill the last staff ID
    const employeeIdInput = document.getElementById("employee_id");
    if (employeeIdInput) {
      employeeIdInput.value = lastStaffId;
      validateEmployeeId();
    }
  }
}

function loadLastStaffId() {
  try {
    const saved = localStorage.getItem("qr_last_staff_id");
    if (saved && saved.trim().length >= 2) {
      return saved.trim().toUpperCase();
    }
    return null;
  } catch (error) {
    return null;
  }
}

function saveLastStaffId(staffId) {
  try {
    if (!staffId || typeof staffId !== "string" || staffId.trim().length < 2) {
      return false;
    }

    const cleanId = staffId.trim().toUpperCase();
    lastStaffId = cleanId;

    // Save to localStorage
    localStorage.setItem("qr_last_staff_id", cleanId);

    return true;
  } catch (error) {
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

function disableFormImmediately() {
  // Find and disable submit button immediately
  const submitButton =
    document.getElementById("submitCheckin") ||
    document.getElementById("submitButton") ||
    document.querySelector('button[type="submit"]') ||
    document.querySelector(".btn-primary");

  const employeeIdInput = document.getElementById("employee_id");
  const form = document.getElementById("checkinForm");

  if (submitButton) {
    submitButton.disabled = true;
    submitButton.style.opacity = "0.5";
    submitButton.style.cursor = "not-allowed";
    submitButton.style.pointerEvents = "none";
    submitButton.setAttribute("data-location-blocked", "true");

    // Store original content
    if (!submitButton.getAttribute("data-original-content")) {
      submitButton.setAttribute(
        "data-original-content",
        submitButton.innerHTML
      );
    }

    // Show loading/checking state
    submitButton.innerHTML = `
      <i class="fas fa-spinner fa-spin"></i>
      <span>Checking Location Services...</span>
    `;
  }

  if (employeeIdInput) {
    employeeIdInput.disabled = true;
    employeeIdInput.style.opacity = "0.7";
    employeeIdInput.setAttribute("data-location-blocked", "true");
    employeeIdInput.placeholder = "Checking location services...";
  }

  if (form) {
    form.classList.add("location-blocked");
    form.style.pointerEvents = "none";
  }

  console.log("🚫 Form DISABLED by default - Checking Location Services...");
}

function handleFormSubmit(event) {
  event.preventDefault();
  event.stopPropagation();

  // CRITICAL: Check if location services are blocked
  if (window.locationServicesBlocked === true) {
    console.log("🚫 Form submission blocked - Location Services not enabled");
    showLocationServicesBlockedMessage();
    return false;
  }

  if (isSubmitting) {
    return false;
  }

  // STEP 1: Check Location Services FIRST
  console.log("🔍 Step 1: Validating Location Services...");

  checkLocationServicesStatus()
    .then(() => {
      // Location services are working, proceed with check-in
      console.log("✅ Location Services validated successfully");
      proceedWithCheckin();
    })
    .catch((error) => {
      // Location services are not working, block check-in
      console.log("❌ Location Services validation failed:", error);
      showLocationServicesBlockedMessage();
      return false;
    });

  return false;
}

/**
 * Proceed with the actual check-in process after location validation
 */
function proceedWithCheckin() {
  // Double-check location services are not blocked
  if (window.locationServicesBlocked === true) {
    console.log("🚫 Check-in blocked - Location Services not enabled");
    showLocationServicesBlockedMessage();
    return;
  }

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

/**
 * Show message when check-in is blocked due to location services
 */
function showLocationServicesBlockedMessage() {
  const messages = {
    en: "Check-in blocked: Location Services must be enabled to continue.",
    es: "Registro bloqueado: Los Servicios de Ubicación deben estar habilitados para continuar.",
  };

  const currentLang = currentLanguage || "en";
  const message = messages[currentLang];

  showCustomStatusMessage(message, "error");
}

// ENHANCED CHECK-IN SUBMISSION WITH MULTIPLE CHECK-IN SUPPORT
function submitCheckin() {
  if (isSubmitting) {
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

  fetch(checkinUrl, {
    method: "POST",
    body: formData,
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      handleCheckinResponse(data);
    })
    .catch((error) => {
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
  console.log("✅ Success data received:", data);

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

    // Get employee ID from form input if not in response data
    const employeeIdInput = document.getElementById("employee_id");
    const employeeId =
      responseData.employee_id ||
      (employeeIdInput
        ? employeeIdInput.value.trim().toUpperCase()
        : "Unknown");

    const location = responseData.location || "Unknown Location";
    const event =
      responseData.event || responseData.location_event || "Check-in";

    // Format current date and time if not provided in response
    const now = new Date();
    const checkInTime =
      responseData.check_in_time ||
      now.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    const checkInDate =
      responseData.check_in_date ||
      now.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });

    // Update success card elements
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

    // Log successful check-in with details
    console.log(
      `✅ Check-in successful for Employee ID: ${employeeId}, Location: ${location}, Time: ${checkInTime}, Date: ${checkInDate}, Action: ${event}`
    );
  }
}

// NEW: Reset form for new check-in
function resetForNewCheckin() {
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
  // Check if Android enhanced location handler is available
  if (
    typeof AndroidLocationHandler !== "undefined" &&
    AndroidLocationHandler.isAndroidDevice()
  ) {
    console.log("📱 Using Android-enhanced location initialization");
    AndroidLocationHandler.initializeAndroidLocation();
  } else {
    console.log("📍 Using standard location initialization");
    requestLocationData();
  }
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
    (error) => {
      console.log("❌ High accuracy failed, trying low accuracy...");

      // Simple fallback with low accuracy
      const lowAccuracyOptions = {
        enableHighAccuracy: false,
        timeout: 15000,
        maximumAge: 600000,
      };

      navigator.geolocation.getCurrentPosition(
        handleLocationSuccess,
        handleLocationError,
        lowAccuracyOptions
      );
    },
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

  // Reverse geocode to get address
  reverseGeocode(userLocation.latitude, userLocation.longitude);

  locationRequestActive = false;
}

function handleLocationError(error) {
  userLocation.source = "manual";
  locationRequestActive = false;
}

function reverseGeocode(lat, lng) {
  // The server will use Google Maps API first, then fall back to OpenStreetMap
  // This provides better accuracy and address formatting
  const url = "/api/reverse-geocode"; // You may want to create this endpoint

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
      } else {
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
  // Load saved language preference from localStorage
  const savedLanguage = loadLanguagePreference();
  if (savedLanguage && savedLanguage !== currentLanguage) {
    currentLanguage = savedLanguage;
  }

  // Set up language toggle button event listener
  const languageToggle = document.getElementById("languageToggle");
  if (languageToggle) {
    languageToggle.addEventListener("click", toggleLanguage);
  }

  // Apply initial translations based on loaded language
  applyTranslations();
}

function toggleLanguage() {
  // Switch between languages
  const newLanguage = currentLanguage === "en" ? "es" : "en";
  currentLanguage = newLanguage;

  // Save new language preference to localStorage
  saveLanguagePreference(currentLanguage);

  // Apply translations immediately
  applyTranslations();

  // Optional: Show brief confirmation message
  showLanguageChangeConfirmation();
}

function loadLanguagePreference() {
  try {
    // Retrieve language preference from localStorage
    const savedLanguage = localStorage.getItem("qr_staff_language");

    // Validate saved language is supported
    if (savedLanguage && translations.hasOwnProperty(savedLanguage)) {
      return savedLanguage;
    } else if (savedLanguage) {
      // Clean up invalid preference
      localStorage.removeItem("qr_staff_language");
    }

    return null;
  } catch (error) {
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
    localStorage.setItem("qr_staff_language", language);
    return true;
  } catch (error) {
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
  if (submitButton && submitButton.innerHTML.includes("data-")) {
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
  // Check if geolocation is supported
  if (!navigator.geolocation) {
    showLocationServicesWarning("not_supported");
    blockCheckInProcess(true);
    return Promise.reject("Location services not supported");
  }

  return new Promise((resolve, reject) => {
    // Test location access with a quick check
    const timeoutId = setTimeout(() => {
      showLocationServicesWarning("timeout");
      blockCheckInProcess(true);
      reject("Location services timeout");
    }, 5000); // 5 second timeout

    navigator.geolocation.getCurrentPosition(
      (position) => {
        // Success - location services are working
        clearTimeout(timeoutId);
        hideLocationServicesWarning();
        blockCheckInProcess(false);

        // Log successful location access
        console.log("✅ Location Services: ENABLED and working");

        resolve(position);
      },
      (error) => {
        // Error - location services may be disabled
        clearTimeout(timeoutId);
        blockCheckInProcess(true);

        switch (error.code) {
          case error.PERMISSION_DENIED:
            showLocationServicesWarning("permission_denied");
            console.log("❌ Location Services: PERMISSION DENIED");
            break;
          case error.POSITION_UNAVAILABLE:
            showLocationServicesWarning("position_unavailable");
            console.log("❌ Location Services: POSITION UNAVAILABLE");
            break;
          case error.TIMEOUT:
            showLocationServicesWarning("timeout");
            console.log("❌ Location Services: TIMEOUT");
            break;
          default:
            showLocationServicesWarning("unknown_error");
            console.log("❌ Location Services: UNKNOWN ERROR");
            break;
        }

        reject(error);
      },
      {
        enableHighAccuracy: false,
        timeout: 4000,
        maximumAge: 30000,
      }
    );
  });
}

function blockCheckInProcess(shouldBlock) {
  // Try multiple possible submit button IDs from your codebase
  const submitButton =
    document.getElementById("submitCheckin") ||
    document.getElementById("submitButton") ||
    document.querySelector('button[type="submit"]') ||
    document.querySelector(".btn-primary");

  const employeeIdInput = document.getElementById("employee_id");
  const form = document.getElementById("checkinForm");

  if (shouldBlock) {
    // Set global blocking flag FIRST
    window.locationServicesBlocked = true;

    // Block check-in process
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.style.opacity = "0.5";
      submitButton.style.cursor = "not-allowed";
      submitButton.style.pointerEvents = "none";

      // Add data attribute to track blocking state
      submitButton.setAttribute("data-location-blocked", "true");

      // Store original button content
      if (!submitButton.getAttribute("data-original-content")) {
        submitButton.setAttribute(
          "data-original-content",
          submitButton.innerHTML
        );
      }

      // Update button text to show it's blocked
      submitButton.innerHTML = `
        <i class="fas fa-lock"></i>
        <span>Location Required / Ubicación Requerida</span>
      `;

      // Remove all event listeners by cloning
      const newButton = submitButton.cloneNode(true);
      submitButton.parentNode.replaceChild(newButton, submitButton);

      // Add blocking event listener
      newButton.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showLocationServicesBlockedMessage();
        return false;
      });
    }

    if (employeeIdInput) {
      employeeIdInput.disabled = true;
      employeeIdInput.style.opacity = "0.7";
      employeeIdInput.setAttribute("data-location-blocked", "true");
    }

    if (form) {
      form.classList.add("location-blocked");
      form.style.pointerEvents = "none";

      // Override form submission completely
      form.onsubmit = function (e) {
        e.preventDefault();
        e.stopPropagation();
        showLocationServicesBlockedMessage();
        return false;
      };
    }

    console.log("🚫 Check-in process BLOCKED - Location Services required");
  } else {
    // Clear global blocking flag FIRST
    window.locationServicesBlocked = false;

    // Unblock check-in process
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.style.opacity = "1";
      submitButton.style.cursor = "pointer";
      submitButton.style.pointerEvents = "auto";

      // Remove blocking data attribute
      submitButton.removeAttribute("data-location-blocked");

      // Restore original button content
      const originalContent = submitButton.getAttribute(
        "data-original-content"
      );
      if (originalContent) {
        submitButton.innerHTML = originalContent;
      }

      // Re-attach proper event listeners
      submitButton.onclick = function (e) {
        e.preventDefault();
        handleFormSubmit(e);
        return false;
      };
    }

    if (employeeIdInput) {
      employeeIdInput.disabled = false;
      employeeIdInput.style.opacity = "1";
      employeeIdInput.removeAttribute("data-location-blocked");
    }

    if (form) {
      form.classList.remove("location-blocked");
      form.style.pointerEvents = "auto";

      // Restore proper form submission handler
      form.onsubmit = function (e) {
        e.preventDefault();
        handleFormSubmit(e);
        return false;
      };
    }

    console.log("✅ Check-in process UNBLOCKED - Location Services working");
  }
}

/**
 * Show location services warning banner
 */
function showLocationServicesWarning(errorType) {
  // Remove existing warning if present
  hideLocationServicesWarning();

  const warningMessages = {
    en: {
      not_supported:
        "⚠️ Location Services Not Supported<br><strong>Check-in is currently blocked.</strong><br>Your browser does not support location services required for check-in.<br><br>Los servicios de ubicación no son compatibles. El registro está bloqueado.",
      permission_denied:
        "⚠️ Location Access Denied<br><strong>Check-in is currently blocked.</strong><br>Please enable location access in your browser settings to continue with check-in.<br><br>Acceso a ubicación denegado. Habilite el acceso para continuar.",
      position_unavailable:
        "⚠️ Location Services Disabled<br><strong>Check-in is currently blocked.</strong><br>Please turn on Location Services in your device settings and refresh the page.<br><br>Servicios de ubicación deshabilitados. Active los servicios y actualice la página.",
      timeout:
        "⚠️ Location Services Not Responding<br><strong>Check-in is currently blocked.</strong><br>Location services may be disabled. Please check your device settings.<br><br>Los servicios de ubicación no responden. Verifique la configuración.",
      unknown_error:
        "⚠️ Location Services Error<br><strong>Check-in is currently blocked.</strong><br>Unable to access location services. Please check your settings and try again.<br><br>Error de servicios de ubicación. Verifique la configuración.",
    },
    es: {
      not_supported:
        "⚠️ Servicios de Ubicación No Compatibles<br><strong>El registro está bloqueado.</strong><br>Su navegador no es compatible con los servicios de ubicación requeridos.",
      permission_denied:
        "⚠️ Acceso a Ubicación Denegado<br><strong>El registro está bloqueado.</strong><br>Habilite el acceso a la ubicación en la configuración de su navegador.",
      position_unavailable:
        "⚠️ Servicios de Ubicación Deshabilitados<br><strong>El registro está bloqueado.</strong><br>Active los Servicios de Ubicación en la configuración y actualice la página.",
      timeout:
        "⚠️ Servicios de Ubicación No Responden<br><strong>El registro está bloqueado.</strong><br>Los servicios pueden estar deshabilitados. Verifique la configuración.",
      unknown_error:
        "⚠️ Error de Servicios de Ubicación<br><strong>El registro está bloqueado.</strong><br>No se puede acceder a los servicios. Verifique la configuración.",
    },
  };

  const currentLang = currentLanguage || "en";
  const message =
    warningMessages[currentLang][errorType] || warningMessages["en"][errorType];

  // Create warning banner
  const warningBanner = document.createElement("div");
  warningBanner.id = "locationServicesWarning";
  warningBanner.className = "location-warning-banner";
  warningBanner.innerHTML = `
    <div class="warning-content">
      <i class="fas fa-exclamation-triangle warning-icon"></i>
      <div class="warning-text">
        <span class="warning-message">${message}</span>
        <div class="warning-actions">
          <button type="button" class="warning-retry-btn" onclick="location.reload()">
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
  const container = document.querySelector(".destination-container");
  if (container) {
    container.insertBefore(warningBanner, container.firstChild);
  }
}

/**
 * Hide location services warning banner
 */
function hideLocationServicesWarning() {
  const existingWarning = document.getElementById("locationServicesWarning");
  if (existingWarning) {
    existingWarning.remove();
  }
}

function initializeLocationServicesCheck() {
  // Initialize global blocking flag
  window.locationServicesBlocked = false;

  // Check location services status when page loads and block if necessary
  setTimeout(() => {
    console.log("🔍 Initializing Location Services check...");
    checkLocationServicesStatus()
      .then(() => {
        console.log("✅ Initial Location Services check passed");
      })
      .catch(() => {
        console.log(
          "❌ Initial Location Services check failed - Check-in blocked"
        );
      });
  }, 1000);

  // Override form initialization to ensure our handlers are used
  setTimeout(() => {
    const form = document.getElementById("checkinForm");
    const submitButton =
      document.getElementById("submitCheckin") ||
      document.querySelector('button[type="submit"]');

    if (form) {
      // Remove existing event listeners by cloning
      const newForm = form.cloneNode(true);
      form.parentNode.replaceChild(newForm, form);

      // Add our controlled event listener
      newForm.addEventListener("submit", handleFormSubmit);
    }

    if (submitButton) {
      // Find the new submit button after form cloning
      const newSubmitButton =
        document.getElementById("submitCheckin") ||
        document.querySelector('button[type="submit"]');

      if (newSubmitButton) {
        newSubmitButton.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          handleFormSubmit(e);
          return false;
        });
      }
    }
  }, 1500);
}
