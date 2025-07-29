/**
 * Users management JavaScript functionality
 * static/js/users.js
 */

class UsersManager {
  constructor() {
    this.selectedUsers = new Set();
    this.init();
  }

  init() {
    this.initializeSearch();
    this.initializeFilters();
    this.initializeBulkActions();
    this.setupEventListeners();
    this.initializeModals();
  }

  // Initialize search functionality
  initializeSearch() {
    const searchInput = document.getElementById("searchUsers");
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        this.filterUsers();
      }, 300);
    });
  }

  // Initialize filter functionality
  initializeFilters() {
    const filters = ["roleFilter", "statusFilter"];

    filters.forEach((filterId) => {
      const filter = document.getElementById(filterId);
      if (filter) {
        filter.addEventListener("change", () => {
          this.filterUsers();
        });
      }
    });
  }

  // Initialize bulk actions
  initializeBulkActions() {
    const selectAllCheckbox = document.getElementById("selectAllUsers");
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", (e) => {
        this.toggleSelectAll(e.target.checked);
      });
    }

    // Individual checkbox handlers
    const userCheckboxes = document.querySelectorAll(".user-checkbox");
    userCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", (e) => {
        this.handleUserSelection(e.target);
      });
    });

    // Bulk action buttons
    this.setupBulkActionButtons();
  }

  setupBulkActionButtons() {
    const bulkDeactivateBtn = document.getElementById("bulkDeactivateBtn");
    const bulkActivateBtn = document.getElementById("bulkActivateBtn");
    const bulkDeleteBtn = document.getElementById("bulkDeleteBtn");

    if (bulkDeactivateBtn) {
      bulkDeactivateBtn.addEventListener("click", () => {
        this.bulkDeactivateUsers();
      });
    }

    if (bulkActivateBtn) {
      bulkActivateBtn.addEventListener("click", () => {
        this.bulkActivateUsers();
      });
    }

    if (bulkDeleteBtn) {
      bulkDeleteBtn.addEventListener("click", () => {
        this.bulkDeleteUsers();
      });
    }
  }

  // Setup event listeners
  setupEventListeners() {
    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      // ESC to close modals
      if (e.key === "Escape") {
        this.closeAllModals();
      }

      // Ctrl/Cmd + F to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === "f") {
        e.preventDefault();
        const searchInput = document.getElementById("searchUsers");
        if (searchInput) searchInput.focus();
      }
    });

    // Click outside dropdowns to close
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".dropdown")) {
        this.closeAllDropdowns();
      }
    });
  }

  // Initialize modal functionality
  initializeModals() {
    const modals = document.querySelectorAll(".modal");
    modals.forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          this.closeModal(modal);
        }
      });
    });
  }

  // Filter users based on search and filters
  filterUsers() {
    const searchTerm =
      document.getElementById("searchUsers")?.value.toLowerCase() || "";
    const roleFilter = document.getElementById("roleFilter")?.value || "";
    const statusFilter = document.getElementById("statusFilter")?.value || "";

    const userRows = document.querySelectorAll(".user-row");
    let visibleCount = 0;

    userRows.forEach((row) => {
      const name = row.dataset.name?.toLowerCase() || "";
      const email = row.dataset.email?.toLowerCase() || "";
      const username = row.dataset.username?.toLowerCase() || "";
      const role = row.dataset.role || "";
      const status = row.dataset.status || "";

      const matchesSearch =
        !searchTerm ||
        name.includes(searchTerm) ||
        email.includes(searchTerm) ||
        username.includes(searchTerm);

      const matchesRole = !roleFilter || role === roleFilter;
      const matchesStatus = !statusFilter || status === statusFilter;

      if (matchesSearch && matchesRole && matchesStatus) {
        this.showUserRow(row);
        visibleCount++;
      } else {
        this.hideUserRow(row);
      }
    });

    this.updateResultsCount(visibleCount);
  }

  showUserRow(row) {
    row.style.display = "table-row";
    row.classList.remove("fade-out");
    row.classList.add("fade-in");
  }

  hideUserRow(row) {
    row.classList.remove("fade-in");
    row.classList.add("fade-out");
    setTimeout(() => {
      if (row.classList.contains("fade-out")) {
        row.style.display = "none";
      }
    }, 300);
  }

  updateResultsCount(count) {
    const counter = document.querySelector(".results-counter");
    if (counter) {
      counter.textContent = `${count} users found`;
    }
  }

  // Dropdown management
  toggleDropdown(event, button) {
    event.stopPropagation();

    const dropdown = button.closest(".dropdown");
    const menu = dropdown.querySelector(".dropdown-menu");

    // Close all other dropdowns
    this.closeAllDropdowns();

    // Toggle current dropdown
    menu.classList.toggle("show");
  }

  closeAllDropdowns() {
    const openMenus = document.querySelectorAll(".dropdown-menu.show");
    openMenus.forEach((menu) => {
      menu.classList.remove("show");
    });
  }

  // User Actions
  async deactivateUser(userId, userName) {
    const confirmed = await this.showConfirmation(
      "Deactivate User",
      `Are you sure you want to deactivate ${userName}?`,
      "This will disable their login access but preserve their data."
    );

    if (!confirmed) return;

    try {
      const response = await fetch(`/users/${userId}/delete`, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        // Update UI
        this.updateUserStatus(userId, "inactive");
        window.showToast(
          `User ${userName} deactivated successfully`,
          "success"
        );
      } else {
        throw new Error("Failed to deactivate user");
      }
    } catch (error) {
      console.error("Deactivation error:", error);
      window.showToast("Failed to deactivate user", "error");
    }
  }

  async reactivateUser(userId, userName) {
    try {
      const response = await fetch(`/users/${userId}/reactivate`, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        this.updateUserStatus(userId, "active");
        window.showToast(
          `User ${userName} reactivated successfully`,
          "success"
        );
      } else {
        throw new Error("Failed to reactivate user");
      }
    } catch (error) {
      console.error("Reactivation error:", error);
      window.showToast("Failed to reactivate user", "error");
    }
  }

  async promoteUser(userId, userName) {
    const confirmed = await this.showConfirmation(
      "Promote to Admin",
      `Promote ${userName} to admin?`,
      "This will give them full system access including user management and system settings."
    );

    if (!confirmed) return;

    try {
      const response = await fetch(`/users/${userId}/promote`, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        this.updateUserRole(userId, "admin");
        window.showToast(
          `${userName} promoted to admin successfully`,
          "success"
        );
      } else {
        throw new Error("Failed to promote user");
      }
    } catch (error) {
      console.error("Promotion error:", error);
      window.showToast("Failed to promote user", "error");
    }
  }

  async demoteUser(userId, userName) {
    const confirmed = await this.showConfirmation(
      "Demote from Admin",
      `Demote ${userName} from admin to staff?`,
      "This will remove their admin privileges and limit access to QR code management only."
    );

    if (!confirmed) return;

    try {
      const response = await fetch(`/users/${userId}/demote`, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        this.updateUserRole(userId, "staff");
        window.showToast(
          `${userName} demoted to staff successfully`,
          "success"
        );
      } else {
        throw new Error("Failed to demote user");
      }
    } catch (error) {
      console.error("Demotion error:", error);
      window.showToast("Failed to demote user", "error");
    }
  }

  async permanentlyDeleteUser(userId, userName) {
    const confirmed = await this.showConfirmation(
      "Permanently Delete User",
      `⚠️ PERMANENTLY DELETE ${userName}?`,
      "This action CANNOT be undone and will permanently remove the user account and all associated QR codes.",
      "danger"
    );

    if (!confirmed) return;

    try {
      const response = await fetch(`/users/${userId}/permanently-delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        // Remove user row from table
        const userRow = document.querySelector(`[data-user-id="${userId}"]`);
        if (userRow) {
          userRow.classList.add("fade-out");
          setTimeout(() => userRow.remove(), 300);
        }

        window.showToast(`User ${userName} permanently deleted`, "success");
      } else {
        throw new Error("Failed to delete user");
      }
    } catch (error) {
      console.error("Deletion error:", error);
      window.showToast("Failed to delete user", "error");
    }
  }

  // Update UI after user actions
  updateUserStatus(userId, newStatus) {
    const userRow = document.querySelector(`[data-user-id="${userId}"]`);
    if (!userRow) return;

    userRow.dataset.status = newStatus;

    const statusBadge = userRow.querySelector(".user-status");
    if (statusBadge) {
      statusBadge.className = `user-status ${newStatus}`;
      statusBadge.innerHTML = `
        <i class="fas ${
          newStatus === "active" ? "fa-check-circle" : "fa-times-circle"
        }"></i>
        ${newStatus === "active" ? "Active" : "Inactive"}
      `;
    }

    // Update action buttons in dropdown
    this.updateUserActions(userId, newStatus);
  }

  updateUserRole(userId, newRole) {
    const userRow = document.querySelector(`[data-user-id="${userId}"]`);
    if (!userRow) return;

    userRow.dataset.role = newRole;

    const roleBadge = userRow.querySelector(".user-role");
    if (roleBadge) {
      roleBadge.className = `user-role ${newRole}`;
      roleBadge.textContent = newRole;
    }

    // Update action buttons
    this.updateUserActions(userId, null, newRole);
  }

  updateUserActions(userId, status = null, role = null) {
    const userRow = document.querySelector(`[data-user-id="${userId}"]`);
    if (!userRow) return;

    const currentStatus = status || userRow.dataset.status;
    const currentRole = role || userRow.dataset.role;

    // Update dropdown menu items
    const dropdownMenu = userRow.querySelector(".dropdown-menu");
    if (dropdownMenu) {
      // This would update the dropdown items based on new status/role
      // Implementation depends on your dropdown structure
    }
  }

  // Bulk Actions
  toggleSelectAll(checked) {
    const userCheckboxes = document.querySelectorAll(".user-checkbox");
    userCheckboxes.forEach((checkbox) => {
      checkbox.checked = checked;
      this.handleUserSelection(checkbox);
    });
  }

  handleUserSelection(checkbox) {
    const userId = checkbox.value;

    if (checkbox.checked) {
      this.selectedUsers.add(userId);
    } else {
      this.selectedUsers.delete(userId);
    }

    this.updateBulkActionsBar();
    this.updateSelectAllState();
  }

  updateBulkActionsBar() {
    const bulkActionsBar = document.getElementById("bulkActionsBar");
    const selectedCount = document.getElementById("selectedCount");

    if (bulkActionsBar && selectedCount) {
      if (this.selectedUsers.size > 0) {
        bulkActionsBar.classList.add("show");
        selectedCount.textContent = this.selectedUsers.size;
      } else {
        bulkActionsBar.classList.remove("show");
      }
    }
  }

  updateSelectAllState() {
    const selectAllCheckbox = document.getElementById("selectAllUsers");
    const userCheckboxes = document.querySelectorAll(".user-checkbox");

    if (selectAllCheckbox && userCheckboxes.length > 0) {
      const checkedCount = Array.from(userCheckboxes).filter(
        (cb) => cb.checked
      ).length;
      selectAllCheckbox.checked = checkedCount === userCheckboxes.length;
      selectAllCheckbox.indeterminate =
        checkedCount > 0 && checkedCount < userCheckboxes.length;
    }
  }

  async bulkDeactivateUsers() {
    if (this.selectedUsers.size === 0) return;

    const confirmed = await this.showConfirmation(
      "Bulk Deactivate Users",
      `Deactivate ${this.selectedUsers.size} selected users?`,
      "This will disable their login access but preserve their data."
    );

    if (!confirmed) return;

    try {
      const response = await fetch("/users/bulk/deactivate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          user_ids: Array.from(this.selectedUsers),
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Update UI for deactivated users
        this.selectedUsers.forEach((userId) => {
          this.updateUserStatus(userId, "inactive");
        });

        this.clearSelection();
        window.showToast(result.message, "success");
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      console.error("Bulk deactivation error:", error);
      window.showToast("Failed to deactivate users", "error");
    }
  }

  async bulkActivateUsers() {
    if (this.selectedUsers.size === 0) return;

    const confirmed = await this.showConfirmation(
      "Bulk Activate Users",
      `Activate ${this.selectedUsers.size} selected users?`,
      "This will restore their login access."
    );

    if (!confirmed) return;

    try {
      const response = await fetch("/users/bulk/activate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          user_ids: Array.from(this.selectedUsers),
        }),
      });

      const result = await response.json();

      if (result.success) {
        this.selectedUsers.forEach((userId) => {
          this.updateUserStatus(userId, "active");
        });

        this.clearSelection();
        window.showToast(result.message, "success");
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      console.error("Bulk activation error:", error);
      window.showToast("Failed to activate users", "error");
    }
  }

  async bulkDeleteUsers() {
    if (this.selectedUsers.size === 0) return;

    const confirmed = await this.showConfirmation(
      "Permanently Delete Users",
      `⚠️ PERMANENTLY DELETE ${this.selectedUsers.size} selected users?`,
      "This action CANNOT be undone and will permanently remove all user accounts and their associated data.",
      "danger"
    );

    if (!confirmed) return;

    try {
      const response = await fetch("/users/bulk/permanently-delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          user_ids: Array.from(this.selectedUsers),
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Remove users from table
        this.selectedUsers.forEach((userId) => {
          const userRow = document.querySelector(`[data-user-id="${userId}"]`);
          if (userRow) {
            userRow.classList.add("fade-out");
            setTimeout(() => userRow.remove(), 300);
          }
        });

        this.clearSelection();
        window.showToast(result.message, "success");
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      console.error("Bulk deletion error:", error);
      window.showToast("Failed to delete users", "error");
    }
  }

  clearSelection() {
    this.selectedUsers.clear();
    const userCheckboxes = document.querySelectorAll(".user-checkbox");
    userCheckboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
    this.updateBulkActionsBar();
    this.updateSelectAllState();
  }

  // Modal and confirmation dialogs
  showConfirmation(title, message, details = "", type = "warning") {
    return new Promise((resolve) => {
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.style.display = "flex";
      modal.innerHTML = `
        <div class="modal-content confirmation-modal">
          <div class="modal-header">
            <h3>
              <i class="fas ${
                type === "danger"
                  ? "fa-exclamation-triangle text-danger"
                  : "fa-question-circle text-warning"
              }"></i>
              ${title}
            </h3>
          </div>
          <div class="modal-body">
            <p><strong>${message}</strong></p>
            ${details ? `<p class="text-muted">${details}</p>` : ""}
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary cancel-btn">Cancel</button>
            <button class="btn btn-${
              type === "danger" ? "danger" : "warning"
            } confirm-btn">
              <i class="fas fa-check"></i> Confirm
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      const cancelBtn = modal.querySelector(".cancel-btn");
      const confirmBtn = modal.querySelector(".confirm-btn");

      const cleanup = () => modal.remove();

      cancelBtn.addEventListener("click", () => {
        cleanup();
        resolve(false);
      });

      confirmBtn.addEventListener("click", () => {
        cleanup();
        resolve(true);
      });

      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          cleanup();
          resolve(false);
        }
      });
    });
  }

  closeModal(modal) {
    modal.style.display = "none";
  }

  closeAllModals() {
    const modals = document.querySelectorAll('.modal[style*="flex"]');
    modals.forEach((modal) => this.closeModal(modal));
  }

  // User details modal
  showUserDetails(userId) {
    // Implementation for showing user details modal
    const modal = document.getElementById("userDetailsModal");
    if (modal) {
      // Populate modal with user data
      modal.style.display = "flex";
    }
  }

  closeUserDetailsModal() {
    const modal = document.getElementById("userDetailsModal");
    if (modal) {
      modal.style.display = "none";
    }
  }

  // Password reset modal
  showPasswordResetModal(userId) {
    const modal = document.getElementById("passwordResetModal");
    if (modal) {
      modal.style.display = "flex";
    }
  }

  closePasswordResetModal() {
    const modal = document.getElementById("passwordResetModal");
    if (modal) {
      modal.style.display = "none";
    }
  }
}

// Initialize users manager when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  window.usersManager = new UsersManager();

  // Global functions for inline event handlers
  window.toggleDropdown = (event, button) =>
    window.usersManager.toggleDropdown(event, button);
  window.deactivateUser = (userId, userName) =>
    window.usersManager.deactivateUser(userId, userName);
  window.reactivateUser = (userId, userName) =>
    window.usersManager.reactivateUser(userId, userName);
  window.promoteUser = (userId, userName) =>
    window.usersManager.promoteUser(userId, userName);
  window.demoteUser = (userId, userName) =>
    window.usersManager.demoteUser(userId, userName);
  window.permanentlyDeleteUser = (userId, userName) =>
    window.usersManager.permanentlyDeleteUser(userId, userName);
  window.showUserDetails = (userId) =>
    window.usersManager.showUserDetails(userId);
  window.closeUserDetailsModal = () =>
    window.usersManager.closeUserDetailsModal();
  window.showPasswordResetModal = (userId) =>
    window.usersManager.showPasswordResetModal(userId);
  window.closePasswordResetModal = () =>
    window.usersManager.closePasswordResetModal();
});
