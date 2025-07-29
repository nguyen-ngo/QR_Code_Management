/**
 * Dashboard-specific JavaScript functionality with QR Toggle
 * static/js/dashboard.js
 */

// Dashboard QR Management Class
class DashboardManager {
  constructor() {
    this.allExpanded = false;
    this.currentModalQR = null;
    this.init();
  }

  init() {
    this.initializeSearch();
    this.initializeFilters();
    this.setupEventListeners();
    this.addScrollAnimations();
    this.updateResultsCount();
  }

  // Initialize search functionality with debouncing
  initializeSearch() {
    const searchInput = document.getElementById("qrSearch");
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        this.filterQRCodes();
      }, 300);
    });
  }

  // Initialize filter functionality
  initializeFilters() {
    const statusFilter = document.getElementById("statusFilter");
    if (!statusFilter) return;

    statusFilter.addEventListener("change", () => {
      this.filterQRCodes();
    });
  }

  // Enhanced QR code filtering with animation
  filterQRCodes() {
    const searchTerm = document.getElementById("qrSearch").value.toLowerCase();
    const statusFilter = document.getElementById("statusFilter").value;
    const qrItems = document.querySelectorAll(".qr-item");

    let visibleCount = 0;

    qrItems.forEach((item) => {
      const name = item.dataset.name || "";
      const location = item.dataset.location || "";
      const status = item.dataset.status || "";

      const matchesSearch =
        !searchTerm ||
        name.includes(searchTerm) ||
        location.includes(searchTerm);
      const matchesStatus = !statusFilter || status === statusFilter;

      if (matchesSearch && matchesStatus) {
        this.showQRItem(item);
        visibleCount++;
      } else {
        this.hideQRItem(item);
      }
    });

    this.updateResultsDisplay(visibleCount);
    this.updateResultsCount();
  }

  // Show QR item with animation
  showQRItem(item) {
    item.style.display = "block";
    setTimeout(() => {
      item.classList.add("fade-in");
      item.classList.remove("fade-out");
    }, 10);
  }

  // Hide QR item with animation
  hideQRItem(item) {
    item.classList.add("fade-out");
    item.classList.remove("fade-in");
    setTimeout(() => {
      item.style.display = "none";
    }, 300);
  }

  // Update results display and empty state
  updateResultsDisplay(count) {
    const qrList = document.getElementById("qrList");
    let existingEmpty = document.querySelector(".search-empty-state");

    if (
      count === 0 &&
      (document.getElementById("qrSearch").value ||
        document.getElementById("statusFilter").value)
    ) {
      if (!existingEmpty) {
        const emptyState = document.createElement("div");
        emptyState.className = "search-empty-state";
        emptyState.innerHTML = `
          <div class="empty-icon">
            <i class="fas fa-search"></i>
          </div>
          <h3>No QR Codes Found</h3>
          <p>Try adjusting your search or filter criteria</p>
          <button onclick="dashboardManager.clearFilters()" class="btn btn-outline">
            <i class="fas fa-refresh"></i>
            Clear Filters
          </button>
        `;
        qrList.parentNode.appendChild(emptyState);
      }
    } else {
      if (existingEmpty) {
        existingEmpty.remove();
      }
    }
  }

  // Clear all filters
  clearFilters() {
    document.getElementById("qrSearch").value = "";
    document.getElementById("statusFilter").value = "";
    this.filterQRCodes();
  }

  // Update results counter
  updateResultsCount() {
    const qrItems = document.querySelectorAll(
      '.qr-item[style*="block"], .qr-item:not([style*="none"])'
    );
    const totalItems = document.querySelectorAll(".qr-item").length;
    const visibleCount = qrItems.length;

    let counter = document.querySelector(".results-counter");
    if (!counter) {
      counter = document.createElement("div");
      counter.className = "results-counter";
      const searchContainer = document.querySelector(".search-container");
      if (searchContainer) {
        searchContainer.appendChild(counter);
      }
    }

    if (visibleCount !== totalItems) {
      counter.textContent = `Showing ${visibleCount} of ${totalItems} QR codes`;
      counter.style.display = "block";
    } else {
      counter.style.display = "none";
    }
  }

  // Setup additional event listeners
  setupEventListeners() {
    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "f":
            e.preventDefault();
            document.getElementById("qrSearch")?.focus();
            break;
        }
      }
    });

    // Enhanced modal functionality
    this.setupModalHandling();
  }

  // Enhanced modal handling
  setupModalHandling() {
    const modal = document.getElementById("qrModal");
    if (!modal) return;

    // Close modal with better animation
    const closeButtons = modal.querySelectorAll("[onclick*='closeQRModal']");
    closeButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.closeQRModal();
      });
    });

    // Click outside to close
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        this.closeQRModal();
      }
    });

    // Escape key to close
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.style.display === "flex") {
        this.closeQRModal();
      }
    });
  }

  // Close QR modal with improved animation
  closeQRModal() {
    const modal = document.getElementById("qrModal");
    if (modal) {
      modal.classList.remove("show");
      setTimeout(() => {
        modal.style.display = "none";
      }, 200);
    }
    this.currentModalQR = null;
  }

  // Add scroll animations for better UX
  addScrollAnimations() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px",
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";
        }
      });
    }, observerOptions);

    // Observe QR items
    document.querySelectorAll(".qr-item").forEach((item) => {
      item.style.opacity = "0";
      item.style.transform = "translateY(20px)";
      item.style.transition = "opacity 0.6s ease, transform 0.6s ease";
      observer.observe(item);
    });
  }

  // Toggle QR details with smooth animation
  toggleQRDetails(qrId) {
    const details = document.getElementById(`qr-details-${qrId}`);
    const chevron = document.querySelector(
      `[onclick="toggleQRDetails(${qrId})"] .chevron`
    );

    if (!details) return;

    if (details.classList.contains("expanded")) {
      details.classList.remove("expanded");
      if (chevron) chevron.style.transform = "rotate(0deg)";
    } else {
      // Close other expanded items first
      document
        .querySelectorAll(".qr-item-details.expanded")
        .forEach((detail) => {
          if (detail !== details) {
            detail.classList.remove("expanded");
          }
        });

      details.classList.add("expanded");
      if (chevron) chevron.style.transform = "rotate(180deg)";
    }
  }

  // Toggle all QR codes expand/collapse
  toggleAllQRs() {
    const details = document.querySelectorAll(".qr-item-details");
    const expandIcon = document.getElementById("expandIcon");
    const expandText = document.getElementById("expandText");

    this.allExpanded = !this.allExpanded;

    details.forEach((detail) => {
      if (this.allExpanded) {
        detail.classList.add("expanded");
      } else {
        detail.classList.remove("expanded");
      }
    });

    // Update button text and icon
    if (expandIcon && expandText) {
      if (this.allExpanded) {
        expandIcon.className = "fas fa-compress-alt";
        expandText.textContent = "Collapse All";
      } else {
        expandIcon.className = "fas fa-expand-alt";
        expandText.textContent = "Expand All";
      }
    }

    // Update chevron icons
    document.querySelectorAll(".chevron").forEach((chevron) => {
      chevron.style.transform = this.allExpanded
        ? "rotate(180deg)"
        : "rotate(0deg)";
    });
  }

  // Enhanced QR preview functionality
  previewQR(qrData, qrName) {
    const modal = document.getElementById("qrModal");
    const modalTitle = document.getElementById("modalTitle");
    const modalImage = document.getElementById("modalQRImage");

    if (modal && modalTitle && modalImage) {
      modalTitle.textContent = `${qrName} - QR Code`;
      modalImage.src = `data:image/png;base64,${qrData}`;
      modalImage.alt = `QR Code for ${qrName}`;

      this.currentModalQR = {
        name: qrName,
        image: `data:image/png;base64,${qrData}`,
      };

      modal.style.display = "flex";
      setTimeout(() => modal.classList.add("show"), 10);
    }
  }

  // Enhanced download functionality
  downloadQR(base64Image, filename) {
    try {
      const link = document.createElement("a");
      link.href = `data:image/png;base64,${base64Image}`;
      link.download = `${filename
        .replace(/[^a-z0-9]/gi, "_")
        .toLowerCase()}_qr_code.png`;

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
    if (this.currentModalQR) {
      const base64Data = this.currentModalQR.image.split("base64,")[1];
      this.downloadQR(base64Data, this.currentModalQR.name);
    }
  }

  // NEW: Toggle QR Code Status (Activate/Deactivate)
  async toggleQRCodeStatus(qrId) {
    const qrItem = document.querySelector(`[data-qr-id="${qrId}"]`);
    const statusElement = document.getElementById(`status-${qrId}`);
    const statusIcon = document.getElementById(`status-icon-${qrId}`);
    const statusText = document.getElementById(`status-text-${qrId}`);
    const toggleBtn = document.getElementById(`toggle-btn-${qrId}`);
    const toggleIcon = document.getElementById(`toggle-icon-${qrId}`);
    const detailToggleBtn = document.getElementById(
      `detail-toggle-btn-${qrId}`
    );

    if (!statusElement || !qrItem) return;

    // Add loading state
    statusElement.classList.add("status-loading");
    if (toggleBtn) toggleBtn.disabled = true;
    if (detailToggleBtn) detailToggleBtn.disabled = true;

    try {
      const response = await fetch(`/qr-codes/${qrId}/toggle-status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (data.success) {
        // Update UI elements
        const newStatus = data.new_status;
        const newStatusClass = newStatus ? "active" : "inactive";
        const newIconClass = newStatus ? "fa-check-circle" : "fa-times-circle";
        const newToggleIcon = newStatus ? "fa-pause" : "fa-play";
        const newToggleBtnClass = newStatus ? "btn-deactivate" : "btn-activate";
        const newDetailBtnClass = newStatus ? "btn-warning" : "btn-success";
        const newDetailBtnText = newStatus ? "Deactivate" : "Activate";

        // Update status badge
        statusElement.className = `qr-status ${newStatusClass}`;
        if (statusIcon) statusIcon.className = `fas ${newIconClass}`;
        if (statusText) statusText.textContent = data.status_text;

        // Update QR item data attribute and styling
        qrItem.setAttribute("data-status", newStatusClass);

        // Update toggle button (collapsed view)
        if (toggleBtn) {
          toggleBtn.className = `action-btn btn-status ${newToggleBtnClass}`;
          toggleBtn.title = `${newDetailBtnText} QR Code`;
        }
        if (toggleIcon) {
          toggleIcon.className = `fas ${newToggleIcon}`;
        }

        // Update detail toggle button (expanded view)
        if (detailToggleBtn) {
          detailToggleBtn.className = `btn ${newDetailBtnClass}`;
          detailToggleBtn.innerHTML = `<i class="fas ${newToggleIcon}"></i> ${newDetailBtnText} QR Code`;
        }

        // Update status badges in expanded view
        const detailStatusBadges = qrItem.querySelectorAll(".status-badge");
        detailStatusBadges.forEach((badge) => {
          badge.className = `status-badge ${newStatusClass}`;
          const icon = badge.querySelector("i");
          if (icon) icon.className = `fas ${newIconClass}`;
          const text = badge.textContent.trim();
          if (text === "Active" || text === "Inactive") {
            badge.innerHTML = `<i class="fas ${newIconClass}"></i> ${data.status_text}`;
          }
        });

        // Show success message
        this.showToast(data.message, "success");

        // Update statistics if needed
        this.updateStatistics();
      } else {
        this.showToast(
          data.message || "Failed to update QR code status",
          "error"
        );
      }
    } catch (error) {
      console.error("Error toggling QR status:", error);
      this.showToast("Network error. Please try again.", "error");
    } finally {
      // Remove loading state
      statusElement.classList.remove("status-loading");
      if (toggleBtn) toggleBtn.disabled = false;
      if (detailToggleBtn) detailToggleBtn.disabled = false;
    }
  }

  // Update statistics after status change
  updateStatistics() {
    const activeCount = document.querySelectorAll(
      '[data-status="active"]'
    ).length;
    const inactiveCount = document.querySelectorAll(
      '[data-status="inactive"]'
    ).length;
    const totalCount = activeCount + inactiveCount;

    // Update active count
    const activeStatElement = document.querySelector(".stat-card.success h3");
    if (activeStatElement) {
      activeStatElement.textContent = activeCount;
    }

    // Update active percentage
    const activePercentElement = document.querySelector(
      ".stat-card.success .stat-trend"
    );
    if (activePercentElement && totalCount > 0) {
      const percentage = ((activeCount / totalCount) * 100).toFixed(1);
      activePercentElement.textContent = `${percentage}% active`;
    }

    // Update inactive count if there's a specific stat card for it
    const inactiveStatElement = document.querySelector(".stat-card.warning h3");
    if (inactiveStatElement) {
      inactiveStatElement.textContent = inactiveCount;
    }

    // Update inactive percentage
    const inactivePercentElement = document.querySelector(
      ".stat-card.warning .stat-trend"
    );
    if (inactivePercentElement && totalCount > 0) {
      const percentage = ((inactiveCount / totalCount) * 100).toFixed(1);
      inactivePercentElement.textContent = `${percentage}% inactive`;
    }
  }

  // Toast notification system
  showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-content">
        <i class="fas ${this.getToastIcon(type)}"></i>
        <span>${message}</span>
      </div>
    `;

    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add("show"), 100);

    // Auto remove
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => {
        if (document.body.contains(toast)) {
          document.body.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }

  // Get toast icon based on type
  getToastIcon(type) {
    const icons = {
      success: "fa-check-circle",
      error: "fa-exclamation-circle",
      warning: "fa-exclamation-triangle",
      info: "fa-info-circle",
    };
    return icons[type] || icons.info;
  }
}

// Global functions for compatibility with existing onclick handlers
let dashboardManager;

function toggleQRDetails(qrId) {
  dashboardManager?.toggleQRDetails(qrId);
}

function toggleAllQRs() {
  dashboardManager?.toggleAllQRs();
}

function previewQR(qrData, qrName) {
  dashboardManager?.previewQR(qrData, qrName);
}

function downloadQR(base64Image, filename) {
  dashboardManager?.downloadQR(base64Image, filename);
}

function closeQRModal() {
  dashboardManager?.closeQRModal();
}

function downloadModalQR() {
  dashboardManager?.downloadModalQR();
}

// NEW: Global function for QR status toggle
function toggleQRCodeStatus(qrId) {
  dashboardManager?.toggleQRCodeStatus(qrId);
}

// Initialize dashboard when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  dashboardManager = new DashboardManager();

  // Add helpful keyboard shortcuts tooltip
  console.log("Dashboard keyboard shortcuts:");
  console.log("Ctrl/Cmd + F: Focus search");
  console.log("Escape: Close modal");
});
