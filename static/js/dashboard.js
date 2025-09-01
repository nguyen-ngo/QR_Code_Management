/**
 * Unified Dashboard JavaScript for QR Code Management
 * static/js/dashboard.js
 */

class ProjectDashboardManager {
  constructor() {
    this.expandedProjects = new Set();
    this.currentModalQR = null;
    this.selectedQRCodes = new Set();
    this.allExpanded = false;
    this.initialize();
  }

  initialize() {
    const saved = localStorage.getItem("expandedProjects");
    if (saved) {
      this.expandedProjects = new Set(JSON.parse(saved));
      this.restoreProjectStates();
    }

    this.setupEventListeners();
    this.addScrollAnimations();
  }

  restoreProjectStates() {
    this.expandedProjects.forEach((projectId) => {
      this.expandProject(projectId, false);
    });
  }

  // Setup event listeners
  setupEventListeners() {
    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      // ESC to close modals
      if (e.key === "Escape") {
        this.closeQRModal();
        this.closeImageLightbox();
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

    const qrItems = document.querySelectorAll(".qr-item, .qr-card");
    qrItems.forEach((item) => observer.observe(item));
  }

  // Project Management Functions
  toggleProject(projectId) {
    const isExpanded = this.expandedProjects.has(projectId);

    if (isExpanded) {
      this.collapseProject(projectId);
    } else {
      this.expandProject(projectId);
    }

    this.saveExpandedState();
  }

  expandProject(projectId, animate = true) {
    const projectQR = document.getElementById(`project-qr-${projectId}`);
    const toggle = document.getElementById(`toggle-${projectId}`);
    const header = toggle?.closest(".project-header");

    if (projectQR && toggle) {
      projectQR.classList.add("expanded");
      toggle.classList.add("expanded");
      header?.classList.add("expanded");
      this.expandedProjects.add(projectId);

      if (animate) {
        setTimeout(() => {
          projectQR.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
        }, 200);
      }
    }
  }

  collapseProject(projectId) {
    const projectQR = document.getElementById(`project-qr-${projectId}`);
    const toggle = document.getElementById(`toggle-${projectId}`);
    const header = toggle?.closest(".project-header");

    if (projectQR && toggle) {
      projectQR.classList.remove("expanded");
      toggle.classList.remove("expanded");
      header?.classList.remove("expanded");
      this.expandedProjects.delete(projectId);
    }
  }

  saveExpandedState() {
    localStorage.setItem(
      "expandedProjects",
      JSON.stringify([...this.expandedProjects])
    );
  }

  // QR Code Status Toggle
  async toggleQRCodeStatus(qrId) {
    try {
      const response = await fetch(`/qr-codes/${qrId}/toggle-status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          this.showToast(result.message, "success");

          // Reload page after short delay to show updated status
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          throw new Error(result.message || "Failed to toggle QR code status");
        }
      } else {
        throw new Error("Failed to toggle QR code status");
      }
    } catch (error) {
      console.error("Toggle status failed:", error);
      this.showToast("Failed to update QR code status", "error");
    }
  }

  // QR Modal Functions
  openQRModalFromData(element) {
    const qrData = {
      name: element.dataset.qrName,
      image: element.querySelector("img").src,
      location: element.dataset.qrLocation,
      address: element.dataset.qrAddress,
      event: element.dataset.qrEvent,
      qr_url: element.dataset.qrUrl,
    };

    this.openQRModal(qrData);
  }

  openQRModal(qrData) {
    const modal = document.getElementById("qrModal");
    const modalImage = document.getElementById("modalQRImage");
    const modalTitle = document.getElementById("modalTitle");
    const modalQRName = document.getElementById("modalQRName");
    const modalQRLocation = document.getElementById("modalQRLocation");
    const modalQRAddress = document.getElementById("modalQRAddress");
    const modalQREvent = document.getElementById("modalQREvent");
    const modalQRDestination = document.getElementById("modalQRDestination");

    if (modal && modalImage && modalTitle) {
      modalTitle.textContent = `QR Code: ${qrData.name}`;
      modalImage.src = qrData.image;
      modalImage.alt = `QR Code for ${qrData.name}`;

      if (modalQRName) modalQRName.textContent = qrData.name || "-";
      if (modalQRLocation) modalQRLocation.textContent = qrData.location || "-";
      if (modalQRAddress) modalQRAddress.textContent = qrData.address || "-";
      if (modalQREvent)
        modalQREvent.textContent = qrData.event || "No event specified";

      if (modalQRDestination && qrData.qr_url) {
        const destinationUrl = `${window.location.origin}/qr/${qrData.qr_url}`;
        const linkElement = modalQRDestination.querySelector("a");
        if (linkElement) {
          linkElement.href = destinationUrl;
          linkElement.innerHTML = `
            <i class="fas fa-external-link-alt"></i>
            ${destinationUrl}
          `;
        }
      } else if (modalQRDestination) {
        modalQRDestination.innerHTML =
          '<span style="color: var(--gray-500); font-style: italic;">No destination URL available</span>';
      }

      this.currentModalQR = {
        name: qrData.name,
        image: qrData.image,
        location: qrData.location,
        address: qrData.address,
        event: qrData.event,
        qr_url: qrData.qr_url,
        destination_url: qrData.qr_url
          ? `${window.location.origin}/qr/${qrData.qr_url}`
          : null,
      };

      modal.style.display = "flex";

      document.addEventListener("keydown", this.handleModalKeydown.bind(this));
    }
  }

  closeQRModal() {
    const modal = document.getElementById("qrModal");
    if (modal) {
      modal.style.display = "none";
      this.currentModalQR = null;

      document.removeEventListener(
        "keydown",
        this.handleModalKeydown.bind(this)
      );
    }
  }

  handleModalKeydown(event) {
    if (event.key === "Escape") {
      this.closeQRModal();
    }
  }

  // Download Functions
  downloadModalQR() {
    if (this.currentModalQR) {
      const base64Data = this.currentModalQR.image.includes("base64,")
        ? this.currentModalQR.image.split("base64,")[1]
        : this.currentModalQR.image;
      this.downloadQR(base64Data, this.currentModalQR.name);
    }
  }

  downloadQRFromCard(button) {
    const qrCard = button.closest(".qr-card") || button.closest(".qr-item");
    const img = qrCard.querySelector("img");
    const qrName =
      qrCard.dataset.qrName ||
      qrCard.querySelector(".qr-name")?.textContent ||
      "qr_code";

    if (img && img.src) {
      const base64Data = img.src.includes("base64,")
        ? img.src.split("base64,")[1]
        : img.src;
      this.downloadQR(base64Data, qrName);
    }
  }

  downloadQR(base64Image, filename) {
    try {
      const base64Data = base64Image.includes("base64,")
        ? base64Image.split("base64,")[1]
        : base64Image;

      const link = document.createElement("a");
      link.href = `data:image/png;base64,${base64Data}`;
      link.download = `${filename
        .replace(/[^a-z0-9]/gi, "_")
        .toLowerCase()}_qr_code.png`;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      this.showToast("QR code downloaded successfully!", "success");
    } catch (error) {
      console.error("Download error:", error);
      this.showToast("Failed to download QR code", "error");
    }
  }

  // Copy Functions
  copyModalQRData() {
    if (this.currentModalQR) {
      const data = `QR Code: ${this.currentModalQR.name}\nLocation: ${
        this.currentModalQR.location
      }\nAddress: ${this.currentModalQR.address}\nEvent: ${
        this.currentModalQR.event
      }${
        this.currentModalQR.destination_url
          ? `\nQR Link: ${this.currentModalQR.destination_url}`
          : ""
      }`;

      navigator.clipboard
        .writeText(data)
        .then(() => {
          this.showToast("QR code information copied to clipboard!", "success");
        })
        .catch(() => {
          this.fallbackCopyText(data);
        });
    }
  }

  copyQRDestination() {
    if (this.currentModalQR && this.currentModalQR.destination_url) {
      navigator.clipboard
        .writeText(this.currentModalQR.destination_url)
        .then(() => {
          this.showToast("QR destination link copied to clipboard!", "success");
        })
        .catch(() => {
          this.showToast("Failed to copy QR link", "error");
        });
    } else {
      this.showToast("No QR destination link available", "warning");
    }
  }

  // FIXED: Copy QR Code URL
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

        // Log the action
        console.log(`QR URL copied for ID: ${qrId}`);
      } else {
        this.showToast("Failed to copy URL", "error");
      }
    } catch (error) {
      console.error("Copy URL error:", error);
      this.showToast("Failed to copy URL", "error");
    }
  }

  // FIXED: Open QR Code Link
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

        // Log the action
        console.log(`QR link opened for ID: ${qrId}`);
      } else {
        this.showToast("Failed to open link", "error");
      }
    } catch (error) {
      console.error("Open link error:", error);
      this.showToast("Failed to open link", "error");
    }
  }

  fallbackCopyText(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand("copy");
      this.showToast("QR code information copied to clipboard!", "success");
    } catch (err) {
      this.showToast("Failed to copy to clipboard", "error");
    }
    document.body.removeChild(textArea);
  }

  // Image Lightbox Functions
  openImageLightbox(previewElement, qrName) {
    console.log("Opening lightbox for:", qrName); // Debug log

    const img = previewElement.querySelector("img");

    if (img && img.src) {
      const lightbox = document.getElementById("imageLightbox");
      const lightboxImage = document.getElementById("lightboxImage");
      const lightboxInfo = document.getElementById("lightboxInfo");

      console.log(
        "Lightbox elements found:",
        !!lightbox,
        !!lightboxImage,
        !!lightboxInfo
      ); // Debug log

      if (lightbox && lightboxImage && lightboxInfo) {
        lightboxImage.src = img.src;
        lightboxImage.alt = img.alt;
        lightboxInfo.textContent = `QR Code: ${qrName}`;

        lightbox.style.display = "flex";
        console.log("Lightbox should be visible now"); // Debug log

        // Add keyboard listener for ESC key
        document.addEventListener(
          "keydown",
          this.handleLightboxKeydown.bind(this)
        );
      } else {
        console.error("Lightbox elements not found");
      }
    } else {
      console.error("Image element not found or no src");
    }
  }

  closeImageLightbox() {
    console.log("Closing lightbox"); // Debug log
    const lightbox = document.getElementById("imageLightbox");
    if (lightbox) {
      lightbox.style.display = "none";

      // Remove keyboard listener
      document.removeEventListener(
        "keydown",
        this.handleLightboxKeydown.bind(this)
      );
    }
  }

  handleLightboxKeydown(event) {
    if (event.key === "Escape") {
      this.closeImageLightbox();
    }
  }

  // QR Item Toggle functionality (for selection)
  toggleQRItem(element) {
    const qrId = element.dataset.qrId;
    if (this.selectedQRCodes.has(qrId)) {
      this.selectedQRCodes.delete(qrId);
      element.classList.remove("selected");
    } else {
      this.selectedQRCodes.add(qrId);
      element.classList.add("selected");
    }

    // Update bulk action buttons if they exist
    this.updateBulkActionButtons();
  }

  updateBulkActionButtons() {
    const bulkActions = document.querySelector(".bulk-actions");
    if (bulkActions) {
      bulkActions.style.display =
        this.selectedQRCodes.size > 0 ? "flex" : "none";
    }
  }

  // Copy QR data functionality
  copyQRData(name, location, address, event) {
    const data = `QR Code: ${name}\nLocation: ${location}\nAddress: ${address}\nEvent: ${event}`;

    if (navigator.clipboard) {
      navigator.clipboard
        .writeText(data)
        .then(() =>
          this.showToast("QR code information copied to clipboard!", "success")
        )
        .catch(() => this.fallbackCopyText(data));
    } else {
      this.fallbackCopyText(data);
    }
  }

  // Delete QR Code
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

      if (response.ok) {
        // Remove QR item from page immediately
        const qrItem = document.querySelector(`[data-qr-id="${qrId}"]`);
        if (qrItem) {
          qrItem.style.transition = "opacity 0.3s";
          qrItem.style.opacity = "0";
          setTimeout(() => {
            qrItem.remove();
          }, 300);
        }

        // Show success message
        this.showToast(`QR code "${qrName}" deleted successfully!`, "success");
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

      // Show error message
      this.showToast("Failed to delete QR code. Please try again.", "error");
    }
  }

  // Toast notification system
  showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${
        type === "success"
          ? "#10b981"
          : type === "error"
          ? "#ef4444"
          : type === "warning"
          ? "#f59e0b"
          : "#3b82f6"
      };
      color: white;
      padding: 12px 16px;
      border-radius: 8px;
      z-index: 9999;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      transition: all 0.3s ease;
      opacity: 0;
      transform: translateX(100%);
    `;

    toast.textContent = message;
    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
      toast.style.opacity = "1";
      toast.style.transform = "translateX(0)";
    }, 100);

    // Animate out
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => {
        if (document.body.contains(toast)) {
          toast.remove();
        }
      }, 300);
    }, 3000);
  }

  // Expand/collapse functionality
  toggleExpandAll() {
    this.allExpanded = !this.allExpanded;
    const qrItems = document.querySelectorAll(".qr-item");
    const expandToggle = document.getElementById("expandAllToggle");

    qrItems.forEach((item) => {
      const details = item.querySelector(".qr-details");
      if (details) {
        if (this.allExpanded) {
          details.style.display = "block";
          item.classList.add("expanded");
        } else {
          details.style.display = "none";
          item.classList.remove("expanded");
        }
      }
    });

    if (expandToggle) {
      expandToggle.innerHTML = this.allExpanded
        ? '<i class="fas fa-compress-alt"></i> Collapse All'
        : '<i class="fas fa-expand-alt"></i> Expand All';
    }
  }
}

// Global variable to hold dashboard manager instance
let dashboardManager;

// Initialize dashboard when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  dashboardManager = new ProjectDashboardManager();

  // Register all global functions for template compatibility
  window.toggleProject = (projectId) =>
    dashboardManager.toggleProject(projectId);
  window.toggleQRCodeStatus = (qrId) =>
    dashboardManager.toggleQRCodeStatus(qrId);
  window.openQRModalFromData = (element) =>
    dashboardManager.openQRModalFromData(element);
  window.openQRModal = (qrData) => dashboardManager.openQRModal(qrData);
  window.closeQRModal = () => dashboardManager.closeQRModal();
  window.downloadModalQR = () => dashboardManager.downloadModalQR();
  window.copyModalQRData = () => dashboardManager.copyModalQRData();
  window.copyQRDestination = () => dashboardManager.copyQRDestination();
  window.downloadQRFromCard = (button) =>
    dashboardManager.downloadQRFromCard(button);
  window.openImageLightbox = (element, qrName) =>
    dashboardManager.openImageLightbox(element, qrName);
  window.closeImageLightbox = () => dashboardManager.closeImageLightbox();
  window.toggleQRItem = (element) => dashboardManager.toggleQRItem(element);
  window.copyQRData = (name, location, address, event) =>
    dashboardManager.copyQRData(name, location, address, event);
  window.deleteQRCode = (qrId, qrName) =>
    dashboardManager.deleteQRCode(qrId, qrName);

  // FIXED: Global functions for copy/open link functionality
  window.copyQRUrl = function (qrId) {
    if (dashboardManager && dashboardManager.copyQRUrl) {
      dashboardManager.copyQRUrl(qrId);
    } else {
      console.error(
        "ProjectDashboardManager not initialized or copyQRUrl method missing"
      );
    }
  };

  window.openQRLink = function (qrId) {
    if (dashboardManager && dashboardManager.openQRLink) {
      dashboardManager.openQRLink(qrId);
    } else {
      console.error(
        "ProjectDashboardManager not initialized or openQRLink method missing"
      );
    }
  };

  console.log(
    "Project Dashboard initialized successfully with copy/open link functionality"
  );
  console.log("Dashboard keyboard shortcuts:");
  console.log("Ctrl/Cmd + F: Focus search");
  console.log("Escape: Close modal");
});
