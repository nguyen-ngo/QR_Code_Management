/**
 * Main JavaScript functionality for QR Code Management System
 * static/js/script.js
 */

// Global configuration
const QRManager = {
  config: {
    modalCloseDelay: 300,
    searchDelay: 300,
    animationDuration: 300,
    toastDuration: 5000,
  },

  // Utility functions
  utils: {
    // Show toast notification
    showToast(message, type = "info") {
      const toast = document.createElement("div");
      toast.className = `toast toast-${type}`;
      toast.innerHTML = `
        <div class="toast-content">
          <i class="fas ${this.getToastIcon(type)}"></i>
          <span>${message}</span>
          <button onclick="this.parentElement.parentElement.remove()" class="toast-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
      `;

      document.body.appendChild(toast);

      // Auto remove after delay
      setTimeout(() => {
        if (toast.parentElement) {
          toast.remove();
        }
      }, QRManager.config.toastDuration);
    },

    getToastIcon(type) {
      const icons = {
        success: "fa-check-circle",
        error: "fa-exclamation-circle",
        warning: "fa-exclamation-triangle",
        info: "fa-info-circle",
      };
      return icons[type] || icons.info;
    },

    // Debounce function
    debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    // Format date
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    },

    // Format time
    formatTime(dateString) {
      const date = new Date(dateString);
      return date.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      });
    },
  },
};

// Navigation functionality
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

      // Close menu when clicking nav links
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

    // Close dropdowns when clicking outside
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

// Modal management
class ModalManager {
  constructor() {
    this.initModals();
  }

  initModals() {
    const modals = document.querySelectorAll(".modal");

    modals.forEach((modal) => {
      // Close button functionality
      const closeBtn = modal.querySelector(".modal-close");
      if (closeBtn) {
        closeBtn.addEventListener("click", () => this.closeModal(modal));
      }

      // Click outside to close
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          this.closeModal(modal);
        }
      });
    });

    // Escape key to close all modals
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeAllModals();
      }
    });
  }

  closeModal(modal) {
    modal.classList.remove("show");
    setTimeout(() => {
      modal.style.display = "none";
    }, QRManager.config.modalCloseDelay);
  }

  closeAllModals() {
    const openModals = document.querySelectorAll('.modal[style*="flex"]');
    openModals.forEach((modal) => this.closeModal(modal));
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = "flex";
      setTimeout(() => {
        modal.classList.add("show");
      }, 10);
    }
  }
}

// Search functionality
class SearchManager {
  constructor(searchInputId, resultsContainerId) {
    this.searchInput = document.getElementById(searchInputId);
    this.resultsContainer = document.getElementById(resultsContainerId);
    this.originalItems = [];

    if (this.searchInput && this.resultsContainer) {
      this.init();
    }
  }

  init() {
    // Store original items
    this.originalItems = Array.from(this.resultsContainer.children);

    // Add search event listener with debouncing
    this.searchInput.addEventListener(
      "input",
      QRManager.utils.debounce(
        () => this.performSearch(),
        QRManager.config.searchDelay
      )
    );
  }

  performSearch() {
    const searchTerm = this.searchInput.value.toLowerCase().trim();

    this.originalItems.forEach((item) => {
      const searchableText = this.getSearchableText(item);
      const matches = searchableText.includes(searchTerm);

      if (matches || searchTerm === "") {
        this.showItem(item);
      } else {
        this.hideItem(item);
      }
    });

    this.updateResultsCount();
  }

  getSearchableText(item) {
    // Get text content from data attributes or text content
    const name = item.dataset.name || "";
    const location = item.dataset.location || "";
    const textContent = item.textContent || "";

    return (name + " " + location + " " + textContent).toLowerCase();
  }

  showItem(item) {
    item.style.display = "block";
    item.classList.remove("fade-out");
    item.classList.add("fade-in");
  }

  hideItem(item) {
    item.classList.remove("fade-in");
    item.classList.add("fade-out");
    setTimeout(() => {
      if (item.classList.contains("fade-out")) {
        item.style.display = "none";
      }
    }, QRManager.config.animationDuration);
  }

  updateResultsCount() {
    const visibleItems = this.originalItems.filter(
      (item) => item.style.display !== "none"
    );

    const counter = document.querySelector(".results-counter");
    if (counter) {
      counter.textContent = `${visibleItems.length} results`;
    }
  }
}

// Download functionality
class DownloadManager {
  static downloadQR(base64Image, filename) {
    try {
      const link = document.createElement("a");
      link.href = "data:image/png;base64," + base64Image;
      link.download =
        filename.replace(/[^a-z0-9]/gi, "_").toLowerCase() + "_qr_code.png";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      QRManager.utils.showToast("QR code downloaded successfully!", "success");
    } catch (error) {
      console.error("Download error:", error);
      QRManager.utils.showToast("Failed to download QR code", "error");
    }
  }

  static downloadModalQR() {
    if (window.currentModalQR) {
      const base64Data = window.currentModalQR.image.split("base64,")[1];
      this.downloadQR(base64Data, window.currentModalQR.name);
    }
  }
}

// Theme management
class ThemeManager {
  constructor() {
    this.initThemeToggle();
    this.loadSavedTheme();
  }

  initThemeToggle() {
    const themeToggle = document.getElementById("themeToggle");
    if (themeToggle) {
      themeToggle.addEventListener("click", () => {
        this.toggleTheme();
      });
    }
  }

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";

    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);

    this.updateThemeIcon(newTheme);
  }

  loadSavedTheme() {
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    this.updateThemeIcon(savedTheme);
  }

  updateThemeIcon(theme) {
    const themeIcon = document.querySelector("#themeToggle i");
    if (themeIcon) {
      themeIcon.className = theme === "dark" ? "fas fa-sun" : "fas fa-moon";
    }
  }
}

// Form validation
class FormValidator {
  constructor(formId) {
    this.form = document.getElementById(formId);
    if (this.form) {
      this.init();
    }
  }

  init() {
    this.form.addEventListener("submit", (e) => {
      if (!this.validateForm()) {
        e.preventDefault();
      }
    });

    // Real-time validation
    const inputs = this.form.querySelectorAll("input, select, textarea");
    inputs.forEach((input) => {
      input.addEventListener("blur", () => this.validateField(input));
      input.addEventListener("input", () => this.clearFieldError(input));
    });
  }

  validateForm() {
    const inputs = this.form.querySelectorAll(
      "input[required], select[required], textarea[required]"
    );
    let isValid = true;

    inputs.forEach((input) => {
      if (!this.validateField(input)) {
        isValid = false;
      }
    });

    return isValid;
  }

  validateField(field) {
    const value = field.value.trim();
    const isRequired = field.hasAttribute("required");
    const fieldType = field.type;

    // Clear previous errors
    this.clearFieldError(field);

    // Required field validation
    if (isRequired && !value) {
      this.showFieldError(field, "This field is required");
      return false;
    }

    // Email validation
    if (fieldType === "email" && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        this.showFieldError(field, "Please enter a valid email address");
        return false;
      }
    }

    // Password validation
    if (fieldType === "password" && value) {
      if (value.length < 6) {
        this.showFieldError(
          field,
          "Password must be at least 6 characters long"
        );
        return false;
      }
    }

    return true;
  }

  showFieldError(field, message) {
    field.classList.add("error");

    // Remove existing error message
    const existingError = field.parentNode.querySelector(".field-error");
    if (existingError) {
      existingError.remove();
    }

    // Add new error message
    const errorElement = document.createElement("div");
    errorElement.className = "field-error";
    errorElement.textContent = message;
    field.parentNode.appendChild(errorElement);
  }

  clearFieldError(field) {
    field.classList.remove("error");
    const errorElement = field.parentNode.querySelector(".field-error");
    if (errorElement) {
      errorElement.remove();
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Initialize managers
  window.navigationManager = new NavigationManager();
  window.modalManager = new ModalManager();
  window.themeManager = new ThemeManager();

  // Initialize search if search input exists
  const searchInput =
    document.getElementById("searchInput") ||
    document.getElementById("qrSearch") ||
    document.getElementById("searchUsers");

  if (searchInput) {
    const containerId = searchInput.dataset.container || "searchResults";
    window.searchManager = new SearchManager(searchInput.id, containerId);
  }

  // Initialize form validation for forms with validation class
  const forms = document.querySelectorAll(".validate-form");
  forms.forEach((form) => {
    new FormValidator(form.id);
  });

  // Global function assignments for inline event handlers
  window.downloadQR = DownloadManager.downloadQR;
  window.downloadModalQR = DownloadManager.downloadModalQR;
  window.showToast = QRManager.utils.showToast;
});

// Global utility functions
window.QRManager = QRManager;
