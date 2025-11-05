/**
 * Attendance Fullscreen JavaScript
 * Handles fullscreen toggle and optimization for iPad viewing
 * static/js/attendance_fullscreen.js
 */

// Fullscreen state management
let isFullscreen = false;

/**
 * Toggle fullscreen mode for attendance report
 */
function toggleFullscreen() {
  const container = document.getElementById('attendanceReportContainer');
  const icon = document.getElementById('fullscreenIcon');
  const body = document.body;

  if (!container || !icon) {
    console.error('Fullscreen elements not found');
    return;
  }

  isFullscreen = !isFullscreen;

  if (isFullscreen) {
    enterFullscreen(container, icon, body);
  } else {
    exitFullscreen(container, icon, body);
  }

  // Log fullscreen action
  logFullscreenAction(isFullscreen ? 'enter' : 'exit');
}

/**
 * Enter fullscreen mode
 */
function enterFullscreen(container, icon, body) {
  // Add fullscreen classes
  container.classList.add('fullscreen-mode');
  body.classList.add('fullscreen-active');

  // Change icon
  icon.classList.remove('fa-expand');
  icon.classList.add('fa-compress');

  // Update button title
  const button = document.getElementById('fullscreenToggle');
  if (button) {
    button.setAttribute('title', 'Exit Fullscreen');
  }

  // Try to use native fullscreen API if available
  if (container.requestFullscreen) {
    container.requestFullscreen().catch(err => {
      console.log('Native fullscreen not available, using CSS fullscreen');
    });
  } else if (container.webkitRequestFullscreen) {
    container.webkitRequestFullscreen().catch(err => {
      console.log('Native fullscreen not available, using CSS fullscreen');
    });
  } else if (container.mozRequestFullScreen) {
    container.mozRequestFullScreen().catch(err => {
      console.log('Native fullscreen not available, using CSS fullscreen');
    });
  } else if (container.msRequestFullscreen) {
    container.msRequestFullscreen().catch(err => {
      console.log('Native fullscreen not available, using CSS fullscreen');
    });
  }

  // Adjust table layout for better viewing
  adjustTableForFullscreen(true);

  // Save fullscreen preference
  saveFullscreenPreference(true);
}

/**
 * Exit fullscreen mode
 */
function exitFullscreen(container, icon, body) {
  // Remove fullscreen classes
  container.classList.remove('fullscreen-mode');
  body.classList.remove('fullscreen-active');

  // Change icon back
  icon.classList.remove('fa-compress');
  icon.classList.add('fa-expand');

  // Update button title
  const button = document.getElementById('fullscreenToggle');
  if (button) {
    button.setAttribute('title', 'Toggle Fullscreen');
  }

  // Exit native fullscreen if active
  if (document.exitFullscreen) {
    document.exitFullscreen().catch(err => {
      console.log('Native fullscreen exit not needed');
    });
  } else if (document.webkitExitFullscreen) {
    document.webkitExitFullscreen().catch(err => {
      console.log('Native fullscreen exit not needed');
    });
  } else if (document.mozCancelFullScreen) {
    document.mozCancelFullScreen().catch(err => {
      console.log('Native fullscreen exit not needed');
    });
  } else if (document.msExitFullscreen) {
    document.msExitFullscreen().catch(err => {
      console.log('Native fullscreen exit not needed');
    });
  }

  // Restore table layout
  adjustTableForFullscreen(false);

  // Save fullscreen preference
  saveFullscreenPreference(false);
}

/**
 * Adjust table columns visibility based on fullscreen and device
 */
function adjustTableForFullscreen(isFullscreen) {
  const table = document.getElementById('attendanceTable');
  if (!table) return;

  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight,
    orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
  };

  // Log viewport info for debugging
  console.log('Adjusting table for fullscreen:', {
    isFullscreen,
    viewport
  });

  // Additional optimizations can be added here
  // The CSS already handles most responsive adjustments
}

/**
 * Save fullscreen preference to localStorage
 */
function saveFullscreenPreference(isFullscreen) {
  try {
    localStorage.setItem('attendance_fullscreen_preference', isFullscreen ? 'true' : 'false');
  } catch (e) {
    console.warn('Could not save fullscreen preference:', e);
  }
}

/**
 * Load fullscreen preference from localStorage
 */
function loadFullscreenPreference() {
  try {
    const preference = localStorage.getItem('attendance_fullscreen_preference');
    return preference === 'true';
  } catch (e) {
    console.warn('Could not load fullscreen preference:', e);
    return false;
  }
}

/**
 * Log fullscreen action for analytics
 */
function logFullscreenAction(action) {
  const logData = {
    action: action,
    timestamp: new Date().toISOString(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
    },
    userAgent: navigator.userAgent,
    isIPad: /iPad/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  };

  console.log('Fullscreen action logged:', logData);

  // You can send this to your backend for analytics if needed
  // fetch('/api/log-fullscreen', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(logData)
  // });
}

/**
 * Handle native fullscreen change events
 */
function handleFullscreenChange() {
  const isNativeFullscreen = !!(
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.mozFullScreenElement ||
    document.msFullscreenElement
  );

  // Sync our state with native fullscreen
  if (!isNativeFullscreen && isFullscreen) {
    // User exited native fullscreen, update our state
    const container = document.getElementById('attendanceReportContainer');
    const icon = document.getElementById('fullscreenIcon');
    const body = document.body;

    if (container && icon) {
      isFullscreen = false;
      exitFullscreen(container, icon, body);
    }
  }
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(event) {
  // F11 or F for fullscreen toggle
  if (event.key === 'F11' || (event.key === 'f' && event.ctrlKey)) {
    event.preventDefault();
    toggleFullscreen();
  }

  // Escape to exit fullscreen
  if (event.key === 'Escape' && isFullscreen) {
    toggleFullscreen();
  }
}

/**
 * Detect iPad and adjust UI accordingly
 */
function detectAndOptimizeForIPad() {
  const isIPad = /iPad/.test(navigator.userAgent) || 
                 (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  if (isIPad) {
    console.log('iPad detected - optimizing UI');
    document.body.classList.add('ipad-device');

    // Add iPad-specific optimizations
    const container = document.getElementById('attendanceReportContainer');
    if (container) {
      container.classList.add('ipad-optimized');
    }
  }
}

/**
 * Initialize fullscreen functionality
 */
function initializeFullscreen() {
  console.log('Initializing fullscreen functionality');

  // Detect iPad
  detectAndOptimizeForIPad();

  // Add event listeners for native fullscreen changes
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.addEventListener('mozfullscreenchange', handleFullscreenChange);
  document.addEventListener('MSFullscreenChange', handleFullscreenChange);

  // Add keyboard shortcuts
  document.addEventListener('keydown', handleKeyboardShortcuts);

  // Load saved preference
  const savedPreference = loadFullscreenPreference();
  if (savedPreference) {
    console.log('Restoring fullscreen preference');
    // Optional: Auto-enter fullscreen if user had it enabled last time
    // toggleFullscreen();
  }

  // Handle orientation changes
  window.addEventListener('orientationchange', function() {
    console.log('Orientation changed');
    if (isFullscreen) {
      adjustTableForFullscreen(true);
    }
  });

  // Handle window resize
  let resizeTimeout;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function() {
      if (isFullscreen) {
        adjustTableForFullscreen(true);
      }
    }, 250);
  });

  console.log('Fullscreen functionality initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeFullscreen);
} else {
  initializeFullscreen();
}

// Export functions for external use
window.toggleFullscreen = toggleFullscreen;
window.isAttendanceFullscreen = function() { return isFullscreen; };