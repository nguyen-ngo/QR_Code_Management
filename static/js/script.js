// Enhanced JavaScript for Left Sidebar Navigation
class QRManager {
  constructor() {
    this.initializeApp();
  }

  initializeApp() {
    this.initSidebar();
    this.initModals();
    this.initDropdowns();
    this.initActiveNavigation();
    this.initFlashMessages();
  }

  // Sidebar Management
  initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    if (!sidebar) return;

    // Desktop sidebar toggle
    if (sidebarToggle) {
      sidebarToggle.addEventListener('click', () => {
        this.toggleSidebar();
      });
    }

    // Mobile menu toggle
    if (mobileMenuBtn) {
      mobileMenuBtn.addEventListener('click', () => {
        this.toggleMobileSidebar();
      });
    }

    // Close mobile sidebar when clicking overlay
    if (sidebarOverlay) {
      sidebarOverlay.addEventListener('click', () => {
        this.closeMobileSidebar();
      });
    }

    // Close mobile sidebar when clicking menu items
    const menuItems = sidebar.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
      item.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
          this.closeMobileSidebar();
        }
      });
    });

    // Handle window resize
    window.addEventListener('resize', () => {
      this.handleResize();
    });

    // Initialize sidebar state based on screen size
    this.handleResize();
  }

  toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.toggle('collapsed');
      this.saveSidebarState();
    }
  }

  toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    if (sidebar && overlay && mobileBtn) {
      const isOpen = sidebar.classList.contains('mobile-open');
      
      if (isOpen) {
        this.closeMobileSidebar();
      } else {
        this.openMobileSidebar();
      }
    }
  }

  openMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    if (sidebar && overlay && mobileBtn) {
      sidebar.classList.add('mobile-open');
      overlay.classList.add('active');
      mobileBtn.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    if (sidebar && overlay && mobileBtn) {
      sidebar.classList.remove('mobile-open');
      overlay.classList.remove('active');
      mobileBtn.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  handleResize() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    if (window.innerWidth <= 768) {
      // Mobile: ensure sidebar is hidden and mobile menu is available
      this.closeMobileSidebar();
    } else if (window.innerWidth <= 1024) {
      // Tablet: auto-collapse sidebar
      sidebar.classList.add('collapsed');
      this.closeMobileSidebar();
    } else {
      // Desktop: restore saved state
      this.restoreSidebarState();
      this.closeMobileSidebar();
    }
  }

  saveSidebarState() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && window.innerWidth > 1024) {
      const isCollapsed = sidebar.classList.contains('collapsed');
      localStorage.setItem('sidebarCollapsed', isCollapsed);
    }
  }

  restoreSidebarState() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && window.innerWidth > 1024) {
      const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
      sidebar.classList.toggle('collapsed', isCollapsed);
    }
  }

  // Active Navigation Highlighting
  initActiveNavigation() {
    const menuItems = document.querySelectorAll('.menu-item[href]');
    const currentPath = window.location.pathname;

    menuItems.forEach(item => {
      const href = item.getAttribute('href');
      if (href === currentPath || (currentPath.startsWith(href) && href !== '/')) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }

  // Theme Management
  initTheme() {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) return;

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.setTheme(savedTheme);

    themeToggle.addEventListener('click', () => {
      const currentTheme = document.body.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      this.setTheme(newTheme);
      localStorage.setItem('theme', newTheme);
    });
  }

  setTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    const themeToggle = document.getElementById('themeToggle');
    
    if (themeToggle) {
      const icon = themeToggle.querySelector('i');
      const text = themeToggle.querySelector('.menu-text');
      
      if (theme === 'dark') {
        icon.className = 'fas fa-sun';
        if (text) text.textContent = 'Light Mode';
      } else {
        icon.className = 'fas fa-moon';
        if (text) text.textContent = 'Dark Mode';
      }
    }
  }

  // Modal Management
  initModals() {
    // Close modal when clicking outside
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal')) {
        this.closeModal(e.target);
      }
    });

    // Close modal with close button
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-close') || 
          e.target.closest('.modal-close')) {
        const modal = e.target.closest('.modal');
        if (modal) {
          this.closeModal(modal);
        }
      }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
          this.closeModal(openModal);
        }
      }
    });
  }

  showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
      
      // Focus first focusable element
      const focusableElement = modal.querySelector('input, textarea, select, button, [tabindex]:not([tabindex="-1"])');
      if (focusableElement) {
        setTimeout(() => focusableElement.focus(), 100);
      }
    }
  }

  closeModal(modal) {
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  }

  // Dropdown Management
  initDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown');

    dropdowns.forEach(dropdown => {
      const trigger = dropdown.querySelector('.dropdown-trigger');
      const menu = dropdown.querySelector('.dropdown-menu');

      if (trigger && menu) {
        trigger.addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleDropdown(dropdown);
        });
      }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
      this.closeAllDropdowns();
    });

    // Close dropdowns with Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAllDropdowns();
      }
    });
  }

  toggleDropdown(dropdown) {
    const menu = dropdown.querySelector('.dropdown-menu');
    const isOpen = menu.classList.contains('show');

    this.closeAllDropdowns();

    if (!isOpen) {
      menu.classList.add('show');
    }
  }

  closeAllDropdowns() {
    const openMenus = document.querySelectorAll('.dropdown-menu.show');
    openMenus.forEach(menu => {
      menu.classList.remove('show');
    });
  }

  // Flash Messages
  initFlashMessages() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        this.dismissAlert(alert);
      }, 5000);

      // Manual dismiss
      const closeBtn = alert.querySelector('.alert-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => {
          this.dismissAlert(alert);
        });
      }
    });
  }

  dismissAlert(alert) {
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(100%)';
    
    setTimeout(() => {
      if (alert.parentNode) {
        alert.parentNode.removeChild(alert);
      }
    }, 300);
  }

  // Download QR Code functionality
  downloadQR(base64Image, filename) {
    try {
      const link = document.createElement("a");
      link.href = `data:image/png;base64,${base64Image}`;
      link.download = `${filename.replace(/[^a-z0-9]/gi, "_").toLowerCase()}_qr_code.png`;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Show success toast
      this.showToast("QR code downloaded successfully!", "success");
    } catch (error) {
      this.showToast("Failed to download QR code", "error");
      console.error("Download error:", error);
    }
  }

  // Download from modal
  downloadModalQR() {
    if (window.currentModalQR) {
      const base64Data = window.currentModalQR.image.split("base64,")[1];
      this.downloadQR(base64Data, window.currentModalQR.name);
    }
  }

  // QR Modal functionality
  openQRModal(qrData, qrName) {
    const modal = document.getElementById("qrModal");
    const modalTitle = document.getElementById("modalTitle");
    const modalImage = document.getElementById("modalQRImage");

    if (modal && modalTitle && modalImage) {
      modalTitle.textContent = `${qrName} - QR Code`;
      modalImage.src = `data:image/png;base64,${qrData}`;
      modalImage.alt = `QR Code for ${qrName}`;

      // Store current modal QR for download
      window.currentModalQR = {
        name: qrName,
        image: `data:image/png;base64,${qrData}`,
      };

      modal.classList.add('show');
    }
  }

  closeQRModal() {
    const modal = document.getElementById("qrModal");
    if (modal) {
      modal.classList.remove('show');
      window.currentModalQR = null;
    }
  }

  // Utility Methods
  showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.innerHTML = `
      <i class="fas fa-info-circle"></i>
      ${message}
      <button class="alert-close">
        <i class="fas fa-times"></i>
      </button>
    `;

    const container = document.querySelector('.flash-messages') || document.body;
    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    // Auto dismiss
    setTimeout(() => {
      this.dismissAlert(toast);
    }, duration);

    return toast;
  }

  // Form Validation Helper
  validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        this.showFieldError(field, 'This field is required');
        isValid = false;
      } else {
        this.clearFieldError(field);
      }
    });

    return isValid;
  }

  showFieldError(field, message) {
    this.clearFieldError(field);
    
    field.classList.add('error');
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    
    field.parentNode.appendChild(errorElement);
  }

  clearFieldError(field) {
    field.classList.remove('error');
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
      existingError.remove();
    }
  }

  // AJAX Helper
  async makeRequest(url, options = {}) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      ...options
    };

    try {
      const response = await fetch(url, defaultOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Request failed:', error);
      this.showToast('An error occurred. Please try again.', 'error');
      throw error;
    }
  }
}

// Keep existing date/time utilities
const DateTimeUtils = {
  formatDate: (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  },

  formatDateTime: (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },

  formatTime: (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  },
};

// Legacy Navigation Manager for backward compatibility
class NavigationManager {
  constructor() {
    this.initMobileMenu();
    this.initDropdowns();
  }

  initMobileMenu() {
    const mobileMenuBtn = document.getElementById("mobile-menu");
    const navMenu = document.getElementById("navMenu");

    if (mobileMenuBtn && navMenu) {
      mobileMenuBtn.addEventListener("click", () => {
        mobileMenuBtn.classList.toggle("active");
        navMenu.classList.toggle("active");
      });

      const navLinks = navMenu.querySelectorAll(".nav-link");
      navLinks.forEach((link) => {
        link.addEventListener("click", () => {
          mobileMenuBtn.classList.remove("active");
          navMenu.classList.remove("active");
        });
      });
    }
  }

  initDropdowns() {
    const dropdowns = document.querySelectorAll(".dropdown");

    dropdowns.forEach((dropdown) => {
      const trigger = dropdown.querySelector(".dropdown-trigger");
      const menu = dropdown.querySelector(".dropdown-menu");

      if (trigger && menu) {
        trigger.addEventListener("click", (e) => {
          e.stopPropagation();
          this.toggleDropdown(dropdown);
        });
      }
    });

    document.addEventListener("click", () => {
      this.closeAllDropdowns();
    });
  }

  toggleDropdown(dropdown) {
    const menu = dropdown.querySelector(".dropdown-menu");
    const isOpen = menu.classList.contains("show");

    this.closeAllDropdowns();

    if (!isOpen) {
      menu.classList.add("show");
    }
  }

  closeAllDropdowns() {
    const openMenus = document.querySelectorAll(".dropdown-menu.show");
    openMenus.forEach((menu) => {
      menu.classList.remove("show");
    });
  }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  // Initialize main app if sidebar exists (authenticated users)
  if (document.getElementById('sidebar')) {
    window.qrManager = new QRManager();
    
    // Make functions globally available for inline event handlers
    window.downloadQR = (base64Image, filename) => {
      window.qrManager.downloadQR(base64Image, filename);
    };
    
    window.downloadModalQR = () => {
      window.qrManager.downloadModalQR();
    };
    
    window.openQRModal = (qrData, qrName) => {
      window.qrManager.openQRModal(qrData, qrName);
    };
    
    window.closeQRModal = () => {
      window.qrManager.closeQRModal();
    };
  } else {
    // Initialize legacy navigation for non-authenticated pages
    window.navigationManager = new NavigationManager();
  }
});

// Export for use in other scripts
window.DateTimeUtils = DateTimeUtils;

// Keep any existing global functions for backward compatibility
if (typeof showConfirmation === 'undefined') {
  window.showConfirmation = async function(title, message, description = '') {
    return new Promise((resolve) => {
      const confirmed = confirm(`${title}\n\n${message}\n${description}`);
      resolve(confirmed);
    });
  };
}