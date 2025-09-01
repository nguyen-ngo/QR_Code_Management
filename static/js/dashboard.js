class DashboardManager {
  constructor() {
    this.selectedQRCodes = new Set();
    this.allExpanded = false;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.addScrollAnimations();
  }

  animateOut(element, callback) {
    element.classList.add("fade-out");
    setTimeout(() => {
      if (callback) callback();
      element.style.display = "none";
    }, 300);
  }

  // Setup event listeners
  setupEventListeners() {
    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      // ESC to close modals
      if (e.key === "Escape") {
        this.closeQRModal();
      }

      // Ctrl/Cmd + F to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === "f") {
        e.preventDefault();
        const searchInput = document.getElementById("qrSearch");
        if (searchInput) searchInput.focus();
      }

      // Delete key for bulk delete (when items selected)
      if (e.key === "Delete" && this.selectedQRCodes.size > 0) {
        e.preventDefault();
        this.bulkDeleteQRCodes();
      }
    });

    // Expand/collapse all toggle
    const expandToggle = document.getElementById("expandAllToggle");
    if (expandToggle) {
      expandToggle.addEventListener("click", () => {
        this.toggleExpandAll();
      });
    }
  }

  // Add scroll animations for QR items
  addScrollAnimations() {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("animate-in");
          }
        });
      },
      { threshold: 0.1 }
    );

    const qrItems = document.querySelectorAll(".qr-item");
    qrItems.forEach((item) => observer.observe(item));
  }

  // FIXED: QR Code Toggle Status
  toggleQRCodeStatus(qrId) {
    const qrItem = document.querySelector(`[data-qr-id="${qrId}"]`);
    if (!qrItem) return;

    const currentStatus = qrItem.dataset.status;
    const newStatus = currentStatus === "active" ? "inactive" : "active";

    // Show loading state
    const toggleBtn = document.getElementById(`toggle-btn-${qrId}`);
    const toggleIcon = document.getElementById(`toggle-icon-${qrId}`);

    if (toggleBtn && toggleIcon) {
      toggleBtn.classList.add("status-loading");
      toggleIcon.className = "fas fa-spinner fa-spin";
      toggleBtn.disabled = true;
    }

    // FIXED: Use correct endpoint with POST method for JSON response
    fetch(`/qr-codes/${qrId}/toggle-status`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((result) => {
        if (result.success) {
          // Update UI with new status
          this.updateQRStatus(qrId, result.new_status ? "active" : "inactive");
          window.showToast(result.message, "success");
        } else {
          throw new Error(result.message || "Failed to update status");
        }
      })
      .catch((error) => {
        console.error("Status update error:", error);
        window.showToast("Failed to update QR code status", "error");
      })
      .finally(() => {
        // Remove loading state
        if (toggleBtn && toggleIcon) {
          toggleBtn.classList.remove("status-loading");
          toggleBtn.disabled = false;
          // Restore icon based on current status
          const currentStatus = qrItem.dataset.status;
          toggleIcon.className = `fas ${
            currentStatus === "active" ? "fa-pause" : "fa-play"
          }`;
        }
      });
  }

  // Update QR status in UI
  updateQRStatus(qrId, newStatus) {
    const qrItem = document.querySelector(`[data-qr-id="${qrId}"]`);
    if (!qrItem) return;

    // Update data attribute
    qrItem.dataset.status = newStatus;

    // Update status badge
    const statusBadge = qrItem.querySelector(".qr-status");
    if (statusBadge) {
      statusBadge.className = `qr-status ${newStatus}`;
      statusBadge.innerHTML = `
        <i class="fas ${
          newStatus === "active" ? "fa-check-circle" : "fa-times-circle"
        }"></i>
        ${newStatus === "active" ? "Active" : "Inactive"}
      `;
    }

    // Update toggle buttons
    this.updateToggleButton(qrId, newStatus);
  }

  // Update toggle button appearance
  updateToggleButton(qrId, status) {
    const toggleBtn = document.getElementById(`toggle-btn-${qrId}`);
    const toggleIcon = document.getElementById(`toggle-icon-${qrId}`);
    const detailToggleBtn = document.getElementById(
      `detail-toggle-btn-${qrId}`
    );

    if (toggleBtn && toggleIcon) {
      // Update quick action button
      toggleBtn.className = `action-btn btn-status ${
        status === "active" ? "btn-deactivate" : "btn-activate"
      }`;
      toggleBtn.title = `${
        status === "active" ? "Deactivate" : "Activate"
      } QR Code`;
      toggleIcon.className = `fas ${
        status === "active" ? "fa-pause" : "fa-play"
      }`;
    }

    if (detailToggleBtn) {
      // Update detail action button
      detailToggleBtn.className = `btn ${
        status === "active" ? "btn-warning" : "btn-success"
      }`;
      detailToggleBtn.innerHTML = `
        <i class="fas ${status === "active" ? "fa-pause" : "fa-play"}"></i>
        ${status === "active" ? "Deactivate" : "Activate"} QR Code
      `;
    }
  }

  async deleteQRCode(qrId, qrName) {
    if (!confirm(`Delete "${qrName}"? This cannot be undone.`)) return;

    try {
      // Show loading state
      const deleteBtn = document.querySelector(
        `[onclick*="deleteQRCode(${qrId}"]`
      );
      if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML =
          '<i class="fas fa-spinner fa-spin"></i> Deleting...';
      }

      const response = await fetch(`/qr-codes/${qrId}/delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      // Don't try to parse as JSON - just check if request was successful
      if (response.ok) {
        // Remove QR item from page immediately
        const qrItem = document.querySelector(`[data-qr-id="${qrId}"]`);
        if (qrItem) {
          qrItem.style.transition = "opacity 0.3s";
          qrItem.style.opacity = "0";
          setTimeout(() => {
            qrItem.remove();
            if (this.updateResultsCount) this.updateResultsCount();
          }, 300);
        }

        // Use simple alert instead of problematic showToast
        alert(`QR code "${qrName}" deleted successfully!`);
      } else {
        throw new Error(`Server error: ${response.status}`);
      }
    } catch (error) {
      console.error("Delete error:", error);

      // Restore button if there was an error
      const deleteBtn = document.querySelector(
        `[onclick*="deleteQRCode(${qrId}"]`
      );
      if (deleteBtn) {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
      }

      // Use simple alert instead of problematic showToast
      alert("Failed to delete QR code. Please try again.");
    }
  }

  // Show custom delete confirmation dialog
  showDeleteConfirmation(qrName) {
    return new Promise((resolve) => {
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.style.display = "flex";
      modal.innerHTML = `
        <div class="modal-content confirmation-modal">
          <div class="modal-header">
            <h3><i class="fas fa-exclamation-triangle text-warning"></i> Confirm Deletion</h3>
          </div>
          <div class="modal-body">
            <p><strong>Are you sure you want to permanently delete "${qrName}"?</strong></p>
            <p class="text-muted">This action cannot be undone.</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-danger" onclick="confirmDelete()">
              <i class="fas fa-trash"></i> Delete
            </button>
            <button class="btn btn-secondary" onclick="cancelDelete()">Cancel</button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      window.confirmDelete = () => {
        document.body.removeChild(modal);
        delete window.confirmDelete;
        delete window.cancelDelete;
        resolve(true);
      };

      window.cancelDelete = () => {
        document.body.removeChild(modal);
        delete window.confirmDelete;
        delete window.cancelDelete;
        resolve(false);
      };

      // Close on ESC key
      const escHandler = (e) => {
        if (e.key === "Escape") {
          window.cancelDelete();
          document.removeEventListener("keydown", escHandler);
        }
      };
      document.addEventListener("keydown", escHandler);

      // Close on backdrop click
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          window.cancelDelete();
        }
      });
    });
  }

  // Bulk delete functionality
  async bulkDeleteQRCodes() {
    if (this.selectedQRCodes.size === 0) return;

    const confirmed = await this.showBulkDeleteConfirmation(
      this.selectedQRCodes.size
    );
    if (!confirmed) return;

    const deletePromises = Array.from(this.selectedQRCodes).map((qrId) => {
      const qrItem = document.querySelector(`[data-qr-id="${qrId}"]`);
      const qrName = qrItem
        ? qrItem.querySelector(".qr-name")?.textContent || "Unknown"
        : "Unknown";
      return this.deleteQRCode(qrId, qrName);
    });

    try {
      await Promise.all(deletePromises);
      this.selectedQRCodes.clear();
      window.showToast(
        `Successfully deleted ${deletePromises.length} QR codes`,
        "success"
      );
    } catch (error) {
      console.error("Bulk delete error:", error);
      window.showToast("Some QR codes could not be deleted", "error");
    }
  }

  showBulkDeleteConfirmation(count) {
    return new Promise((resolve) => {
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.style.display = "flex";
      modal.innerHTML = `
        <div class="modal-content confirmation-modal">
          <div class="modal-header">
            <h3><i class="fas fa-exclamation-triangle text-warning"></i> Confirm Bulk Deletion</h3>
          </div>
          <div class="modal-body">
            <p><strong>Are you sure you want to permanently delete ${count} QR codes?</strong></p>
            <p class="text-muted">This action cannot be undone.</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-danger" onclick="confirmBulkDelete()">
              <i class="fas fa-trash"></i> Delete All
            </button>
            <button class="btn btn-secondary" onclick="cancelBulkDelete()">Cancel</button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      window.confirmBulkDelete = () => {
        document.body.removeChild(modal);
        delete window.confirmBulkDelete;
        delete window.cancelBulkDelete;
        resolve(true);
      };

      window.cancelBulkDelete = () => {
        document.body.removeChild(modal);
        delete window.confirmBulkDelete;
        delete window.cancelBulkDelete;
        resolve(false);
      };
    });
  }

  // QR Modal functions
  openQRModal(qrData) {
    const modal = document.getElementById("qrModal");
    const modalImage = document.getElementById("modalQRImage");
    const modalTitle = document.getElementById("modalTitle");

    if (modal && modalImage && modalTitle) {
      modalTitle.textContent = `QR Code: ${qrData.name}`;
      modalImage.src = qrData.image;
      modal.style.display = "flex";
    }
  }

  closeQRModal() {
    const modal = document.getElementById("qrModal");
    if (modal) {
      modal.style.display = "none";
    }
  }

  // Expand/collapse functionality
  toggleExpandAll() {
    const qrItems = document.querySelectorAll(".qr-item");
    const expandToggle = document.getElementById("expandAllToggle");

    this.allExpanded = !this.allExpanded;

    qrItems.forEach((item) => {
      if (this.allExpanded) {
        item.classList.add("expanded");
      } else {
        item.classList.remove("expanded");
      }
    });

    if (expandToggle) {
      expandToggle.innerHTML = this.allExpanded
        ? '<i class="fas fa-compress-alt"></i> Collapse All'
        : '<i class="fas fa-expand-alt"></i> Expand All';
    }
  }

  toggleQRItem(element) {
    element.classList.toggle("expanded");
  }

  // Copy QR data to clipboard
  copyQRData(name, location, address, event) {
    const data = `QR Code: ${name}\nLocation: ${location}\nAddress: ${address}\nEvent: ${event}`;

    navigator.clipboard
      .writeText(data)
      .then(() => {
        window.showToast("QR code information copied to clipboard!", "success");
      })
      .catch(() => {
        window.showToast("Failed to copy to clipboard", "error");
      });
  }

  // Update results display
  updateResultsDisplay(count) {
    const resultsDisplay = document.getElementById("resultsDisplay");
    if (resultsDisplay) {
      resultsDisplay.textContent = `${count} QR codes found`;
    }
  }

  updateResultsCount() {
    const qrItems = document.querySelectorAll(
      '.qr-item[style*="block"], .qr-item:not([style*="none"])'
    );
    const counter = document.querySelector(".results-counter");

    if (counter) {
      counter.textContent = `${qrItems.length} results`;
    }
  }

  showToast(message, type = "info") {
    // Create toast if showToast doesn't exist globally
    if (typeof window.showToast === "function") {
      window.showToast(message, type);
    } else {
      // Fallback to console or simple alert
      console.log(`${type.toUpperCase()}: ${message}`);
      // Or use a simple notification
      const toast = document.createElement("div");
      toast.className = `toast toast-${type}`;
      toast.textContent = message;
      toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${
          type === "success"
            ? "#10b981"
            : type === "error"
            ? "#ef4444"
            : "#3b82f6"
        };
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        z-index: 9999;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      `;

      document.body.appendChild(toast);

      setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    }
  }

  // Copy QR Code URL
  async copyQRUrl(qrId) {
    try {
      const response = await fetch(`/qr-codes/${qrId}/copy-url`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (data.success && data.url) {
        // Copy to clipboard
        await navigator.clipboard.writeText(data.url);
        this.showToast("QR code URL copied to clipboard!", "success");
      } else {
        this.showToast("Failed to copy URL", "error");
      }
    } catch (error) {
      console.error("Copy URL error:", error);
      this.showToast("Failed to copy URL", "error");
    }
  }

  // Open QR Code Link
  async openQRLink(qrId) {
    try {
      const response = await fetch(`/qr-codes/${qrId}/open-link`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (data.success && data.url) {
        // Open in new tab
        window.open(data.url, "_blank");
        this.showToast("QR code link opened!", "success");
      } else {
        this.showToast("Failed to open link", "error");
      }
    } catch (error) {
      console.error("Open link error:", error);
      this.showToast("Failed to open link", "error");
    }
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  window.dashboardManager = new DashboardManager();

  // Global functions for inline event handlers
  window.toggleQRCodeStatus = (qrId) =>
    window.dashboardManager.toggleQRCodeStatus(qrId);
  window.deleteQRCode = (qrId, qrName) =>
    window.dashboardManager.deleteQRCode(qrId, qrName);
  window.openQRModal = (qrData) => window.dashboardManager.openQRModal(qrData);
  window.closeQRModal = () => window.dashboardManager.closeQRModal();
  window.toggleQRItem = (element) =>
    window.dashboardManager.toggleQRItem(element);
  window.copyQRData = (name, location, address, event) =>
    window.dashboardManager.copyQRData(name, location, address, event);
});

// Global functions for new features
function copyQRUrl(qrId) {
  window.dashboardManager?.copyQRUrl(qrId);
}

function openQRLink(qrId) {
  window.dashboardManager?.openQRLink(qrId);
}
