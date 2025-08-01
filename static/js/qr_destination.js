/**
 * QR Code Destination Page JavaScript
 * Handles staff check-in functionality and form interactions
 */

// Global variables
let isSubmitting = false;
let currentTime = new Date();

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('QR Destination page initialized');
    
    initializePage();
    setupEventListeners();
    startTimeUpdater();
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

function handleFormSubmit(e) {
    e.preventDefault();
    
    if (isSubmitting) {
        return false;
    }
    
    const employeeId = document.getElementById('employee_id').value.trim();
    
    if (!validateEmployeeId()) {
        return false;
    }
    
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
        showValidationError(employeeInput, 'Employee ID must be less than 20 characters');
        return false;
    }
    
    if (!isValidEmployeeId(employeeId)) {
        showValidationError(employeeInput, 'Employee ID can only contain letters and numbers');
        return false;
    }
    
    // Clear validation error
    employeeInput.classList.remove('error');
    employeeInput.classList.add('success');
    hideStatusMessage();
    
    return true;
}

function isValidEmployeeId(id) {
    return /^[A-Za-z0-9]{3,20}$/.test(id);
}

function showValidationError(input, message) {
    input.classList.add('error');
    input.classList.remove('success');
    showStatusMessage(message, 'error');
    shakeInput(input);
    input.focus();
}

function shakeInput(input) {
    input.classList.add('shake');
    setTimeout(() => {
        input.classList.remove('shake');
    }, 500);
}

function submitCheckin(employeeId) {
    if (isSubmitting) return;
    
    isSubmitting = true;
    showLoadingState();
    showLoadingOverlay();
    
    // Prepare form data
    const formData = new FormData();
    formData.append('employee_id', employeeId);
    
    // Submit to server
    fetch(`/qr/${window.qrUrl}/checkin`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        handleCheckinResponse(data);
    })
    .catch(error => {
        console.error('Check-in error:', error);
        handleCheckinError('Network error. Please check your connection and try again.');
    })
    .finally(() => {
        isSubmitting = false;
        hideLoadingState();
        hideLoadingOverlay();
    });
}

function handleCheckinResponse(data) {
    if (data.success) {
        showSuccessCard(data.data);
        logSuccessfulCheckin(data.data);
        
        // Optional: Analytics tracking
        if (typeof gtag !== 'undefined') {
            gtag('event', 'checkin_success', {
                'location': window.locationName,
                'event_name': window.eventName
            });
        }
    } else {
        handleCheckinError(data.message);
    }
}

function handleCheckinError(message) {
    showStatusMessage(message, 'error');
    
    // Shake the form to draw attention
    const form = document.getElementById('checkinForm');
    if (form) {
        form.classList.add('shake');
        setTimeout(() => {
            form.classList.remove('shake');
        }, 500);
    }
    
    // Re-focus on input
    const employeeInput = document.getElementById('employee_id');
    if (employeeInput) {
        employeeInput.focus();
        employeeInput.select();
    }
}

function showSuccessCard(data) {
    // Hide the check-in form
    const checkinCard = document.querySelector('.checkin-card');
    if (checkinCard) {
        checkinCard.style.display = 'none';
    }
    
    // Populate and show success card
    const successCard = document.getElementById('successCard');
    if (successCard) {
        document.getElementById('successEmployeeId').textContent = data.employee_id || '-';
        document.getElementById('successLocation').textContent = data.location || '-';
        document.getElementById('successEvent').textContent = data.event || '-';
        document.getElementById('successTime').textContent = data.time || '-';
        document.getElementById('successDate').textContent = data.date || '-';
        
        successCard.style.display = 'block';
        successCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // Optional: Auto-hide success card after some time
    setTimeout(() => {
        showAutoHideOption();
    }, 10000); // 10 seconds
}

function showAutoHideOption() {
    const successCard = document.getElementById('successCard');
    if (successCard && successCard.style.display !== 'none') {
        const actions = successCard.querySelector('.success-actions');
        if (actions && !actions.querySelector('.auto-hide-btn')) {
            const autoHideBtn = document.createElement('button');
            autoHideBtn.className = 'btn btn-outline auto-hide-btn';
            autoHideBtn.innerHTML = '<i class="fas fa-clock"></i> Auto-hide in <span id="countdown">30</span>s';
            actions.appendChild(autoHideBtn);
            
            startCountdown(30, () => {
                checkInAnother();
            });
        }
    }
}

function startCountdown(seconds, callback) {
    const countdownElement = document.getElementById('countdown');
    let remaining = seconds;
    
    const interval = setInterval(() => {
        remaining--;
        if (countdownElement) {
            countdownElement.textContent = remaining;
        }
        
        if (remaining <= 0) {
            clearInterval(interval);
            callback();
        }
    }, 1000);
}

function checkInAnother() {
    // Show the check-in form again
    const checkinCard = document.querySelector('.checkin-card');
    const successCard = document.getElementById('successCard');
    
    if (checkinCard) {
        checkinCard.style.display = 'block';
    }
    
    if (successCard) {
        successCard.style.display = 'none';
    }
    
    // Reset form
    const form = document.getElementById('checkinForm');
    if (form) {
        form.reset();
    }
    
    // Clear validation states
    const employeeInput = document.getElementById('employee_id');
    if (employeeInput) {
        employeeInput.classList.remove('error', 'success');
        employeeInput.focus();
    }
    
    hideStatusMessage();
    
    // Scroll back to form
    checkinCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showLoadingState() {
    const btn = document.querySelector('.btn-primary');
    if (btn) {
        const content = btn.querySelector('.btn-content');
        const loader = btn.querySelector('.btn-loader');
        
        if (content) content.style.display = 'none';
        if (loader) loader.style.display = 'flex';
        
        btn.disabled = true;
    }
}

function hideLoadingState() {
    const btn = document.querySelector('.btn-primary');
    if (btn) {
        const content = btn.querySelector('.btn-content');
        const loader = btn.querySelector('.btn-loader');
        
        if (content) content.style.display = 'flex';
        if (loader) loader.style.display = 'none';
        
        btn.disabled = false;
    }
}

function showLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        setTimeout(() => {
            overlay.classList.add('show');
        }, 10);
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('show');
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 200);
    }
}

function showStatusMessage(message, type = 'info') {
    const statusDiv = document.getElementById('statusMessage');
    if (statusDiv) {
        statusDiv.textContent = message;
        statusDiv.className = `status-message ${type}`;
        statusDiv.style.display = 'block';
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                hideStatusMessage();
            }, 5000);
        }
        
        // Scroll to message
        statusDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function hideStatusMessage() {
    const statusDiv = document.getElementById('statusMessage');
    if (statusDiv) {
        statusDiv.style.display = 'none';
    }
}

function updateCurrentTime() {
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        const now = new Date();
        const options = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        };
        
        timeElement.textContent = now.toLocaleDateString('en-US', options);
    }
}

function startTimeUpdater() {
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
}

function handleVisibilityChange() {
    if (document.hidden) {
        // Page is hidden - pause operations
        console.log('Page hidden - pausing operations');
    } else {
        // Page is visible - resume operations
        console.log('Page visible - resuming operations');
        updateCurrentTime();
        
        // Re-focus on input if form is visible
        const checkinCard = document.querySelector('.checkin-card');
        const employeeInput = document.getElementById('employee_id');
        
        if (checkinCard && checkinCard.style.display !== 'none' && employeeInput) {
            setTimeout(() => {
                employeeInput.focus();
            }, 100);
        }
    }
}

function logSuccessfulCheckin(data) {
    console.log('Successful check-in:', {
        employee_id: data.employee_id,
        location: data.location,
        event: data.event,
        time: data.time,
        date: data.date
    });
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Export functions for global access
window.checkInAnother = checkInAnother;
window.validateEmployeeId = validateEmployeeId;

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// Error handling for unhandled promises
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    handleCheckinError('An unexpected error occurred. Please try again.');
    event.preventDefault();
});

// Handle online/offline status
window.addEventListener('online', function() {
    showStatusMessage('Connection restored', 'success');
});

window.addEventListener('offline', function() {
    showStatusMessage('No internet connection. Please check your network.', 'warning');
});

// Performance monitoring
if ('performance' in window) {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log('Page load time:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
        }, 0);
    });
}

// Accessibility enhancements
document.addEventListener('keydown', function(e) {
    // Escape key to reset form
    if (e.key === 'Escape') {
        const successCard = document.getElementById('successCard');
        if (successCard && successCard.style.display !== 'none') {
            checkInAnother();
        } else {
            // Reset form
            const form = document.getElementById('checkinForm');
            if (form) {
                form.reset();
                hideStatusMessage();
                
                const employeeInput = document.getElementById('employee_id');
                if (employeeInput) {
                    employeeInput.classList.remove('error', 'success');
                    employeeInput.focus();
                }
            }
        }
    }
    
    // Ctrl+R to refresh (prevent default and reload page cleanly)
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        window.location.reload();
    }
});

// Touch device optimizations
if ('ontouchstart' in window) {
    // Add touch-friendly classes
    document.body.classList.add('touch-device');
    
    // Prevent zoom on input focus for iOS
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            const viewport = document.querySelector('meta[name="viewport"]');
            if (viewport) {
                viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
            }
        });
        
        input.addEventListener('blur', function() {
            const viewport = document.querySelector('meta[name="viewport"]');
            if (viewport) {
                viewport.setAttribute('content', 'width=device-width, initial-scale=1.0');
            }
        });
    });
}

// Auto-refresh page if idle for too long (optional)
let idleTimer;
const IDLE_TIME = 30 * 60 * 1000; // 30 minutes

function resetIdleTimer() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
        if (confirm('This page has been idle for 30 minutes. Would you like to refresh it?')) {
            window.location.reload();
        } else {
            resetIdleTimer(); // Reset timer if user chooses not to refresh
        }
    }, IDLE_TIME);
}

// Track user activity
['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
    document.addEventListener(event, resetIdleTimer, true);
});

// Initialize idle timer
resetIdleTimer();