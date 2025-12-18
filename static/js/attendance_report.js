/**
 * Enhanced Attendance Report JavaScript
 * Handles filtering, sorting, pagination, and new location/accuracy features
 */

// Global variables
let currentPage = 1;
let entriesPerPage = 50;
let sortColumn = -1;
let sortDirection = "asc";
let attendanceData = [];
let filteredData = [];

// Charts
let dailyChart = null;
let locationChart = null;

// Initialize page when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  console.log("Enhanced Attendance Report page initialized");

  initializeReport();
  loadAttendanceData();
  initializeCharts();
  setupEventListeners();
  initializeDateRangeFilters();
});

function initializeReport() {
  // Load data from table
  loadTableData();

  // Initialize pagination
  updatePagination();

  // Apply initial filters if any
  applyFilters();
}


function extractAccuracyValue(cell) {
  const text = cell.textContent;
  const match = text.match(/(\d+\.?\d*)m/);
  return match ? parseFloat(match[1]) : null;
}

function extractAccuracyLevel(cell) {
  const text = cell.textContent;
  if (text.includes("high")) return "high";
  if (text.includes("medium")) return "medium";
  if (text.includes("low")) return "low";
  return "unknown";
}

function extractCoordinates(cell) {
  // This would need to be enhanced based on actual data structure
  // For now, return placeholder
  return "Coordinates available";
}

function initializeDateRangeFilters() {
  const dateFromInput = document.getElementById("date_from");
  const dateToInput = document.getElementById("date_to");

  if (dateFromInput && dateToInput) {
    // Set max date to today
    const today = new Date().toISOString().split("T")[0];
    dateFromInput.max = today;
    dateToInput.max = today;

    // Add validation to ensure 'from' date is not after 'to' date
    dateFromInput.addEventListener("change", function () {
      if (dateToInput.value && this.value > dateToInput.value) {
        dateToInput.value = this.value;
      }
    });

    dateToInput.addEventListener("change", function () {
      if (dateFromInput.value && this.value < dateFromInput.value) {
        dateFromInput.value = this.value;
      }
    });
  }
}

function setupEventListeners() {
  // Enhanced search and filter listeners
  const searchInput = document.getElementById("searchInput");
  const locationFilter = document.getElementById("location");
  const employeeFilter = document.getElementById("employee");

  if (searchInput) {
    searchInput.addEventListener("input", debounce(applyFilters, 300));
  }

  if (locationFilter) {
    locationFilter.addEventListener("change", applyFilters);
  }

  if (employeeFilter) {
    employeeFilter.addEventListener("input", debounce(applyFilters, 300));
  }

  // Entries per page listener
  const entriesSelect = document.getElementById("entriesPerPage");
  if (entriesSelect) {
    entriesSelect.addEventListener("change", changeEntriesPerPage);
  }

  // Modal close listeners
  window.addEventListener("click", function (event) {
    const recordModal = document.getElementById("recordModal");
    const mapModal = document.getElementById("mapModal");

    if (event.target === recordModal) {
      closeModal();
    }
    if (event.target === mapModal) {
      closeMapModal();
    }
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeModal();
      closeMapModal();
    }
  });
}

function applyFilters() {
  const searchTerm =
    document.getElementById("searchInput")?.value.toLowerCase() || "";
  const locationFilter = document.getElementById("location")?.value || "";
  const employeeFilter =
    document.getElementById("employee")?.value.toLowerCase() || "";

  filteredData = attendanceData.filter((record) => {
    const matchesSearch =
      !searchTerm ||
      record.employeeId.toLowerCase().includes(searchTerm) ||
      record.location.toLowerCase().includes(searchTerm) ||
      record.event.toLowerCase().includes(searchTerm);

    const matchesLocation =
      !locationFilter || record.location === locationFilter;
    const matchesEmployee =
      !employeeFilter ||
      record.employeeId.toLowerCase().includes(employeeFilter);

    return matchesSearch && matchesLocation && matchesEmployee;
  });

  currentPage = 1;
  updateTable();
  updatePagination();
  updateFilterStats();
}

function sortTable(columnIndex) {
  if (sortColumn === columnIndex) {
    sortDirection = sortDirection === "asc" ? "desc" : "asc";
  } else {
    sortColumn = columnIndex;
    sortDirection = "asc";
  }

  const sortKey = getSortKey(columnIndex);

  filteredData.sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];

    // Handle numeric values for accuracy
    if (columnIndex === 8 && aVal !== null && bVal !== null) {
      aVal = parseFloat(aVal);
      bVal = parseFloat(bVal);
    }

    // Handle null values
    if (aVal === null || aVal === undefined) aVal = "";
    if (bVal === null || bVal === undefined) bVal = "";

    if (typeof aVal === "string") {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }

    let result;
    if (aVal < bVal) result = -1;
    else if (aVal > bVal) result = 1;
    else result = 0;

    return sortDirection === "asc" ? result : -result;
  });

  updateTable();
  updateSortIndicators(columnIndex);
}

function getSortKey(columnIndex) {
  const sortKeys = [
    "index",
    "employeeId",
    "location",
    "event",
    "date",
    "time",
    "qr_address",
    "checked_in_address",
    "accuracy",
    "device",
  ];
  return sortKeys[columnIndex] || "index";
}

function updateSortIndicators(activeColumn) {
  // Update sort indicators in table headers
  const headers = document.querySelectorAll(".attendance-table th");
  headers.forEach((header, index) => {
    const icon = header.querySelector("i");
    if (icon) {
      icon.className = "fas fa-sort";
      if (index === activeColumn) {
        icon.className =
          sortDirection === "asc" ? "fas fa-sort-up" : "fas fa-sort-down";
      }
    }
  });
}

function updateTable() {
  const table = document.getElementById("attendanceTable");
  if (!table) return;

  const tbody = table.querySelector("tbody");
  const startIndex = (currentPage - 1) * entriesPerPage;
  const endIndex =
    entriesPerPage === "all"
      ? filteredData.length
      : startIndex + entriesPerPage;
  const pageData = filteredData.slice(startIndex, endIndex);

  tbody.innerHTML = "";

  pageData.forEach((record, index) => {
    const row = createTableRow(record, startIndex + index + 1);
    tbody.appendChild(row);
  });

  // Update any dynamic elements
  updateFilterStats();
}

function changeEntriesPerPage() {
  const select = document.getElementById("entriesPerPage");
  entriesPerPage = select.value === "all" ? "all" : parseInt(select.value);
  currentPage = 1;
  updateTable();
  updatePagination();
}

function updatePagination() {
  const container = document.getElementById("paginationContainer");
  if (!container || entriesPerPage === "all") {
    if (container) container.innerHTML = "";
    return;
  }

  const totalPages = Math.ceil(filteredData.length / entriesPerPage);

  if (totalPages <= 1) {
    container.innerHTML = "";
    return;
  }

  let paginationHTML = '<div class="pagination">';

  // Previous button
  paginationHTML += `
        <button onclick="goToPage(${currentPage - 1})" 
                class="pagination-btn" 
                ${currentPage === 1 ? "disabled" : ""}>
            <i class="fas fa-chevron-left"></i>
        </button>
    `;

  // Page numbers
  const maxVisiblePages = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

  if (endPage - startPage + 1 < maxVisiblePages) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1);
  }

  if (startPage > 1) {
    paginationHTML += `<button onclick="goToPage(1)" class="pagination-btn">1</button>`;
    if (startPage > 2) {
      paginationHTML += '<span class="pagination-ellipsis">...</span>';
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    paginationHTML += `
            <button onclick="goToPage(${i})" 
                    class="pagination-btn ${i === currentPage ? "active" : ""}">
                ${i}
            </button>
        `;
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      paginationHTML += '<span class="pagination-ellipsis">...</span>';
    }
    paginationHTML += `<button onclick="goToPage(${totalPages})" class="pagination-btn">${totalPages}</button>`;
  }

  // Next button
  paginationHTML += `
        <button onclick="goToPage(${currentPage + 1})" 
                class="pagination-btn" 
                ${currentPage === totalPages ? "disabled" : ""}>
            <i class="fas fa-chevron-right"></i>
        </button>
    `;

  paginationHTML += "</div>";

  // Add pagination info
  const startRecord = (currentPage - 1) * entriesPerPage + 1;
  const endRecord = Math.min(currentPage * entriesPerPage, filteredData.length);

  paginationHTML += `
        <div class="pagination-info">
            Showing ${startRecord} to ${endRecord} of ${
    filteredData.length
  } entries
            ${
              filteredData.length !== attendanceData.length
                ? `(filtered from ${attendanceData.length} total entries)`
                : ""
            }
        </div>
    `;

  container.innerHTML = paginationHTML;
}

function goToPage(page) {
  const totalPages = Math.ceil(filteredData.length / entriesPerPage);

  if (page < 1 || page > totalPages) return;

  currentPage = page;
  updateTable();
  updatePagination();

  // Scroll to top of table
  const table = document.getElementById("attendanceTable");
  if (table) {
    table.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function updateFilterStats() {
  // Update stats display if needed
  const totalRecords = filteredData.length;
  console.log(`Filtered records: ${totalRecords}`);
}

// Enhanced record actions
function editRecord(recordId) {
  // Check permissions before allowing edit
  if (!hasEditPermission) {
    alert(
      "Access denied. Only administrators can edit attendance records."
    );
    return;
  }

  console.log(`Edit record: ${recordId}`);
  // Log the action
  console.log(`[LOG] User attempting to edit attendance record: ${recordId}`);

  // Redirect to edit page
  window.location.href = `/attendance/${recordId}/edit`;
}

function deleteRecord(recordId, employeeId) {
  // Check permissions before allowing delete
  if (!hasEditPermission) {
    alert(
      "Access denied. Only administrators can delete attendance records."
    );
    return;
  }

  console.log(`Delete record: ${recordId}`);

  // Confirmation dialog
  const confirmMessage = `Are you sure you want to delete the attendance record for employee "${employeeId}"?\n\nThis action cannot be undone.`;

  if (confirm(confirmMessage)) {
    console.log(
      `[LOG] User confirmed deletion of attendance record: ${recordId}`
    );

    // Send delete request
    fetch(`/attendance/${recordId}/delete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          console.log(
            `[LOG] Successfully deleted attendance record: ${recordId}`
          );
          alert("Attendance record deleted successfully!");
          window.location.reload();
        } else {
          console.error(
            `[LOG] Failed to delete attendance record: ${recordId} - ${data.message}`
          );
          alert(data.message || "Error deleting record. Please try again.");
        }
      })
      .catch((error) => {
        console.error(
          `[LOG] Error during attendance record deletion: ${recordId}`,
          error
        );
        alert("Error deleting record. Please try again.");
      });
  }
}

function closeModal() {
  const modal = document.getElementById("recordModal");
  if (modal) {
    modal.style.display = "none";
  }
}

// Chart initialization (placeholder)
function initializeCharts() {
  console.log("Initializing charts...");
  // Chart implementation would go here
}

function loadAttendanceData() {
  console.log("Loading attendance data for charts...");
  // Additional data loading for charts would go here
}

// Utility function
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

// Enhanced JavaScript functions for location accuracy features

function loadTableData() {
  const table = document.getElementById("attendanceTable");
  if (table) {
    const rows = table.querySelectorAll("tbody tr");
    attendanceData = Array.from(rows).map((row, index) => {
      const cells = row.querySelectorAll("td");
      
      // Extract verification data from the accuracy badge
      const verificationData = extractVerificationData(cells[9]);
      
      return {
          id: row.dataset.recordId,
          index: index + 1,
          employeeId: cells[1] ? cells[1].textContent.trim() : "",
          employeeName: cells[2] ? cells[2].textContent.trim() : "", // NEW: Employee Name column
          location: cells[3] ? cells[3].textContent.trim() : "", // Updated from cells[2]
          event: cells[4] ? cells[4].textContent.trim() : "", // Updated from cells[3]
          date: cells[5] ? cells[5].textContent.trim() : "", // Updated from cells[4]
          time: cells[6] ? cells[6].textContent.trim() : "", // Updated from cells[5]
          qr_address: cells[7] // Updated from cells[6]
              ? cells[7].getAttribute("title") || cells[7].textContent.trim()
              : "",
          checked_in_address: cells[8] // Updated from cells[7]
              ? cells[8].getAttribute("title") || cells[8].textContent.trim()
              : "",
          // FIXED: Extract location accuracy for address display logic
          location_accuracy: cells[9] ? extractLocationAccuracy(cells[9]) : null, // Updated from cells[8]
          accuracy_level: cells[9] // Updated from cells[8]
              ? extractLocationAccuracyLevel(cells[9])
              : "unknown",
          device: cells[10] // Updated from cells[9]
              ? cells[10].textContent.trim()
              : "",
          isModified: row.classList.contains('modified-record'),
          verification_required: verificationData.required,
          verification_status: verificationData.status
      };
    });

    filteredData = [...attendanceData];
    console.log(`Loaded ${attendanceData.length} attendance records`);

    // Debug log for location accuracy data
    const recordsWithAccuracy = attendanceData.filter(
      (r) => r.location_accuracy !== null
    );
    console.log(
      `Records with location accuracy: ${recordsWithAccuracy.length}`
    );
    if (recordsWithAccuracy.length > 0) {
      console.log(
        `Sample location accuracy values:`,
        recordsWithAccuracy.slice(0, 3).map((r) => r.location_accuracy)
      );
    }
  }
}

function extractLocationAccuracy(cell) {
  const text = cell.textContent;
  console.log(`Extracting accuracy from: "${text}"`);

  // Look for miles pattern (e.g., "0.003 mi", "1.234 mi")
  const milesMatch = text.match(/(\d+\.?\d*)\s*mi/);
  if (milesMatch) {
    const value = parseFloat(milesMatch[1]);
    console.log(`Found miles: ${value}`);
    return value;
  }

  // Look for specific accuracy patterns in the HTML
  const accuracyMatch = text.match(/accuracy[:\s]*(\d+\.?\d*)/i);
  if (accuracyMatch) {
    const value = parseFloat(accuracyMatch[1]);
    console.log(`Found accuracy: ${value}`);
    return value;
  }

  // Check for data attributes
  const dataAccuracy = cell.getAttribute("data-accuracy");
  if (dataAccuracy) {
    const value = parseFloat(dataAccuracy);
    console.log(`Found data-accuracy: ${value}`);
    return value;
  }

  // Fallback: look for GPS accuracy in meters and convert to miles (approximate)
  const metersMatch = text.match(/(\d+\.?\d*)\s*m/);
  if (metersMatch) {
    const meters = parseFloat(metersMatch[1]);
    const miles = meters * 0.000621371; // Convert meters to miles (approximate)
    console.log(`Found meters: ${meters}, converted to miles: ${miles}`);
    return miles;
  }

  console.log(`No accuracy found in: "${text}"`);
  return null;
}

function extractLocationAccuracyLevel(cell) {
  // Get the numerical accuracy value from the cell
  const accuracy = extractLocationAccuracy(cell);
  
  // Return 2-level accuracy based on 0.5-mile threshold
  if (accuracy !== null && accuracy !== undefined) {
    return accuracy < 0.3 ? "accurate" : "inaccurate";
  }
  return "unknown";
}

function extractVerificationData(cell) {
  // Extract verification status from badge classes in the HTML
  if (!cell) {
    console.log('extractVerificationData: No cell provided');
    return { required: false, status: null };
  }
  
  const badge = cell.querySelector('.location-accuracy-badge');
  if (!badge) {
    console.log('extractVerificationData: No badge found in cell');
    return { required: false, status: null };
  }
  
  console.log('extractVerificationData: Badge classes:', badge.className);
  
  // Check badge classes for verification status
  if (badge.classList.contains('badge-review-needed')) {
    console.log('extractVerificationData: Found pending verification');
    return { required: true, status: 'pending' };
  } else if (badge.classList.contains('badge-verified')) {
    console.log('extractVerificationData: Found approved verification');
    return { required: true, status: 'approved' };
  } else if (badge.classList.contains('badge-rejected')) {
    console.log('extractVerificationData: Found rejected verification');
    return { required: true, status: 'rejected' };
  }
  
  console.log('extractVerificationData: No verification status found, standard badge');
  return { required: false, status: null };
}

function createTableRow(record, displayIndex) {
  const row = document.createElement("tr");
  row.dataset.recordId = record.id;
  
  // Apply highlighting if record was modified
  if (record.isModified) {
      row.classList.add('modified-record');
  }

  // Debug logging for first few records
  if (displayIndex <= 3) {
    console.log(`=== CREATING ROW ${displayIndex} ===`);
    console.log(`Employee: ${record.employeeId}`);
    console.log(`Location accuracy: ${record.location_accuracy}`);
    console.log(`Verification required: ${record.verification_required}`);
    console.log(`Verification status: ${record.verification_status}`);
    console.log(`QR address: ${record.qr_address}`);
    console.log(`Check-in address: ${record.checked_in_address}`);
  }

  // Create location accuracy badge HTML - check verification status first
  let locationAccuracyBadge;
  
  if (record.verification_required && record.verification_status === 'pending') {
    // Show Review Needed badge for pending verification
    locationAccuracyBadge = `<span class="location-accuracy-badge badge-review-needed" 
            onclick="openVerificationPhotoModal('${record.id}')"
            style="cursor: pointer;"
            title="Click to review verification photo - Distance: ${record.location_accuracy ? record.location_accuracy.toFixed(3) : 'N/A'} miles">
        <i class="fas fa-exclamation-triangle"></i>
        Review Needed
        <small>(${record.location_accuracy ? record.location_accuracy.toFixed(3) : 'N/A'} mi)</small>
    </span>`;
  } else if (record.verification_status === 'approved') {
    // Show Verified badge for approved verification
    locationAccuracyBadge = `<span class="location-accuracy-badge badge-verified" 
            title="Verification approved - Distance: ${record.location_accuracy ? record.location_accuracy.toFixed(3) : 'N/A'} miles">
        <i class="fas fa-check-circle"></i>
        Verified
        <small>(${record.location_accuracy ? record.location_accuracy.toFixed(3) : 'N/A'} mi)</small>
    </span>`;
  } else if (record.verification_status === 'rejected') {
    // Show Rejected badge for rejected verification
    locationAccuracyBadge = `<span class="location-accuracy-badge badge-rejected" 
            title="Verification rejected - Distance: ${record.location_accuracy ? record.location_accuracy.toFixed(3) : 'N/A'} miles">
        <i class="fas fa-times-circle"></i>
        Rejected
        <small>(${record.location_accuracy ? record.location_accuracy.toFixed(3) : 'N/A'} mi)</small>
    </span>`;
  } else if (record.location_accuracy !== null) {
    // Show standard location accuracy badge
    locationAccuracyBadge = `<span class="location-accuracy-badge accuracy-${
          record.accuracy_level
        }" 
                title="Distance between QR location and check-in location: ${
                  record.location_accuracy
                } miles - ${record.accuracy_level}">
            <i class="fas fa-ruler"></i>
            ${record.location_accuracy.toFixed(3)} mi
            <small>(${record.accuracy_level})</small>
        </span>`;
  } else {
    // No accuracy data
    locationAccuracyBadge = `<span class="location-accuracy-badge accuracy-unknown" title="Location accuracy could not be calculated">
            <i class="fas fa-question-circle"></i>
            Unknown
        </span>`;
  }

  // Address display logic based on location accuracy
  let addressDisplayHTML = "";
  let addressToShow = record.checked_in_address;
  let addressIcon = "fas fa-location-arrow";
  let addressClass = "address-normal-accuracy";
  let addressTitle = `Check-in Address: ${record.checked_in_address}`;

  // Apply 0.5-mile threshold logic
  if (
    record.location_accuracy !== null &&
    record.location_accuracy !== undefined
  ) {
    const accuracy = parseFloat(record.location_accuracy);

    if (displayIndex <= 3) {
      console.log(`Applying address logic for ${record.employeeId}:`);
      console.log(`  Accuracy value: ${accuracy}`);
      console.log(`  Is <= 0.3? ${accuracy <= 0.3}`);
    }

    if (!isNaN(accuracy) && accuracy <= 0.3) {
      // High accuracy - use QR address
      addressToShow = record.qr_address;
      addressIcon = "fas fa-check-circle";
      addressClass = "address-high-accuracy";
      addressTitle = `QR Address (High Accuracy ≤ 0.5 mi): ${record.qr_address}`;

      if (displayIndex <= 3) {
        console.log(`  → Using QR address: ${addressToShow}`);
      }

      addressDisplayHTML = `
        <i class="${addressIcon}" style="color: #059669; margin-right: 4px;" 
           title="High accuracy - showing QR location"></i>
        <span title="${addressTitle}" class="${addressClass}">
          ${
            addressToShow.length > 45
              ? addressToShow.substring(0, 45) + "..."
              : addressToShow
          }
        </span>
      `;
    } else {
      // Lower accuracy - use check-in address
      if (displayIndex <= 3) {
        console.log(`  → Using check-in address: ${addressToShow}`);
      }

      addressDisplayHTML = `
        <i class="fas fa-exclamation-triangle" style="color: #f59e0b; margin-right: 4px;" 
           title="Lower accuracy - showing actual check-in location"></i>
        <span title="${addressTitle} (Accuracy: ${accuracy.toFixed(
        3
      )} mi)" class="${addressClass}">
          ${
            addressToShow.length > 45
              ? addressToShow.substring(0, 45) + "..."
              : addressToShow
          }
        </span>
      `;
    }
  } else {
    // No accuracy data - use check-in address
    if (displayIndex <= 3) {
      console.log(
        `  → No accuracy data, using check-in address: ${addressToShow}`
      );
    }

    addressDisplayHTML = `
      <i class="${addressIcon}"></i>
      <span title="${addressTitle}" class="${addressClass}">
        ${
          addressToShow.length > 45
            ? addressToShow.substring(0, 45) + "..."
            : addressToShow
        }
      </span>
    `;
  }

  row.innerHTML = `
        <td>${displayIndex}</td>
        <td>
            <div class="employee-info">
                <span class="employee-id">${record.employeeId}</span>
            </div>
        </td>
        <td>
            <div class="employee-name">
                <i class="fas fa-user"></i>
                <span>${record.employeeName || 'Unknown'}</span>
            </div>
        </td>
        <td>
            <div class="location-info">
                <i class="fas fa-map-marker-alt"></i>
                ${record.location}
            </div>
        </td>
        <td>
            <div class="event-info">
                ${record.event}
            </div>
        </td>
        <td>
            <div class="date-info">
                ${record.date}
            </div>
        </td>
        <td>
            <div class="time-info">
                ${record.time}
            </div>
        </td>
        <td>
            <div class="address-info qr-address">
                <i class="fas fa-qrcode" style="color: #6366f1; margin-right: 4px;" title="QR Code Address (Fixed)"></i>
                <span title="QR Address: ${record.qr_address}">
                    ${
                      record.qr_address.length > 50
                        ? record.qr_address.substring(0, 50) + "..."
                        : record.qr_address
                    }
                </span>
            </div>
        </td>
        <td>
            <div class="address-info checkin-address">
                ${addressDisplayHTML}
            </div>
        </td>
        <td>
            <div class="location-accuracy-info">
                ${locationAccuracyBadge}
            </div>
        </td>
        <td>
            <div class="device-info">
                <i class="fas fa-mobile-alt"></i>
                <span title="${record.device}">
                    ${
                      record.device.length > 20
                        ? record.device.substring(0, 20) + "..."
                        : record.device
                    }
                </span>
            </div>
        </td>
        <td>
            <div class="record-actions">
                ${
                  record.verification_required && record.verification_status === 'pending'
                    ? `<button onclick="openVerificationPhotoModal('${record.id}')" 
                              class="action-btn btn-review"
                              title="Review Verification Photo">
                          <i class="fas fa-camera"></i>
                      </button>`
                    : ''
                }
                ${
                  hasEditPermission
                    ? `
                <button onclick="editRecord('${record.id}')" 
                        class="action-btn btn-edit"
                        title="Edit Record">
                    <i class="fas fa-edit"></i>
                </button>
                <button onclick="deleteRecord('${record.id}', '${record.employeeId}')" 
                        class="action-btn btn-delete"
                        title="Delete Record">
                    <i class="fas fa-trash"></i>
                </button>
                `
                    : `
                <span class="text-muted" title="Admin access required">
                    <i class="fas fa-lock"></i>
                </span>
                `
                }
            </div>
        </td>
    `;

  return row;
}

function getSortKey(columnIndex) {
  const sortKeys = [
    "index",
    "employeeId",
    "location",
    "event",
    "date",
    "time",
    "qr_address",
    "checked_in_address",
    "location_accuracy",
    "device",
  ];
  return sortKeys[columnIndex] || "index";
}

// Enhanced sorting for location accuracy (numeric sorting)
function sortTable(columnIndex) {
  if (sortColumn === columnIndex) {
    sortDirection = sortDirection === "asc" ? "desc" : "asc";
  } else {
    sortColumn = columnIndex;
    sortDirection = "asc";
  }

  const sortKey = getSortKey(columnIndex);

  filteredData.sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];

    // Handle numeric values for location accuracy
    if (columnIndex === 8 && aVal !== null && bVal !== null) {
      aVal = parseFloat(aVal);
      bVal = parseFloat(bVal);
    }

    // Handle null values - put them at the end
    if (aVal === null || aVal === undefined) {
      return sortDirection === "asc" ? 1 : -1;
    }
    if (bVal === null || bVal === undefined) {
      return sortDirection === "asc" ? -1 : 1;
    }

    if (typeof aVal === "string") {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }

    let result;
    if (aVal < bVal) result = -1;
    else if (aVal > bVal) result = 1;
    else result = 0;

    return sortDirection === "asc" ? result : -result;
  });

  updateTable();
  updateSortIndicators(columnIndex);
}

// Enhanced statistics display for location accuracy
function updateFilterStats() {
  const totalRecords = filteredData.length;
  const recordsWithAccuracy = filteredData.filter(
    (r) => r.location_accuracy !== null
  ).length;
  const avgAccuracy =
    recordsWithAccuracy > 0
      ? filteredData
          .filter((r) => r.location_accuracy !== null)
          .reduce((sum, r) => sum + r.location_accuracy, 0) /
        recordsWithAccuracy
      : 0;

  console.log(`Filtered records: ${totalRecords}`);
  console.log(`Records with location accuracy: ${recordsWithAccuracy}`);
  console.log(`Average location accuracy: ${avgAccuracy.toFixed(3)} miles`);
}

// Function to get accuracy level color for charts or displays
function getAccuracyLevelColor(level) {
  const colors = {
    accurate: "#059669", // green
    inaccurate: "#dc2626", // red
    unknown: "#6b7280", // gray
  };
  return colors[level] || colors["unknown"];
}

// Enhanced export function to include location accuracy
function exportAttendanceWithAccuracy() {
  // Build CSV header with location accuracy
  const headers = [
    "#",
    "Employee ID",
    "Employee Name",
    "Location",
    "Event",
    "Date",
    "Time",
    "QR Address",
    "Check-in Address",
    "Location Accuracy (miles)",
    "Accuracy Level",
    "Device",
  ];

  // Build CSV rows
  const rows = filteredData.map((record, index) => [
    index + 1,
    record.employeeId,
    record.employeeName || "Unknown",
    record.location,
    record.event,
    record.date,
    record.time,
    record.qr_address,
    record.checked_in_address,
    record.location_accuracy ? record.location_accuracy.toFixed(3) : "Unknown",
    record.accuracy_level,
    record.device,
  ]);

  // Create CSV content
  const csvContent = [headers, ...rows]
    .map((row) => row.map((field) => `"${field}"`).join(","))
    .join("\n");

  // Download CSV
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute(
    "download",
    `attendance_report_with_accuracy_${
      new Date().toISOString().split("T")[0]
    }.csv`
  );
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function exportAttendance() {
  // Check user role before proceeding
  const userRole = window.userRole; // Read from global variable set in template
  console.log("Template - session.role:", '{{ session.role }}');
  console.log("Template - window.userRole set to:", window.userRole);

  if (!['admin', 'payroll'].includes(userRole)) {
    console.log("Export access denied - insufficient privileges");
    alert("Access denied. Only administrators and payroll staff can export data.");
    return;
  }

  // Log export action
  console.log(`Export button clicked by ${userRole} - redirecting to configuration page`);

  // Get current filters
  const currentFilters = getCurrentFilters();

  // Build URL with current filters
  const params = new URLSearchParams();
  if (currentFilters.date_from)
    params.append("date_from", currentFilters.date_from);
  if (currentFilters.date_to) params.append("date_to", currentFilters.date_to);
  if (currentFilters.location)
    params.append("location", currentFilters.location);
  if (currentFilters.employee)
    params.append("employee", currentFilters.employee);
  if (currentFilters.project)
    params.append("project", currentFilters.project);

  // Navigate to export configuration page
  const configUrl =
    "/export-configuration" +
    (params.toString() ? "?" + params.toString() : "");
  window.location.href = configUrl;
}

function getCurrentFilters() {
  // Extract current filter values from the page
  return {
    date_from: document.getElementById("date_from")?.value || "",
    date_to: document.getElementById("date_to")?.value || "",
    location: document.getElementById("location")?.value || "",
    employee: document.getElementById("employee")?.value || "",
    project: document.getElementById("project")?.value || "",
  };
}

// Add a quick CSV export function as backup (keep existing functionality)
function exportAttendanceCSV() {
  // Check user role before proceeding
  const userRole = window.userRole;
  
  if (!['admin', 'payroll'].includes(userRole)) {
    console.log("CSV export access denied - insufficient privileges");
    alert("Access denied. Only administrators and payroll staff can export data.");
    return;
  }

  // Build export URL with current filters for CSV
  const params = new URLSearchParams();
  const filters = getCurrentFilters();

  if (filters.date_from) params.append("date_from", filters.date_from);
  if (filters.date_to) params.append("date_to", filters.date_to);
  if (filters.location) params.append("location", filters.location);
  if (filters.employee) params.append("employee", filters.employee);
  if (filters.project) params.append("project", filters.project);
  params.append("export", "csv");

  // Create a temporary link and click it to download
  const downloadUrl = window.location.pathname + "?" + params.toString();
  window.open(downloadUrl, "_blank");
}

// Enhanced export menu (if you want to add dropdown with multiple export options)
function showExportMenu() {
  // Create export options menu
  const existingMenu = document.getElementById("exportMenu");
  if (existingMenu) {
    existingMenu.remove();
    return;
  }

  const exportBtn = document.querySelector(
    'button[onclick="exportAttendance()"]'
  );
  if (!exportBtn) return;

  const menu = document.createElement("div");
  menu.id = "exportMenu";
  menu.style.cssText = `
        position: absolute;
        top: 100%;
        right: 0;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        z-index: 1000;
        min-width: 200px;
        margin-top: 5px;
    `;

  menu.innerHTML = `
        <div style="padding: 0.5rem;">
            <button onclick="exportAttendance(); closeExportMenu();" 
                    style="width: 100%; padding: 0.75rem; border: none; background: none; text-align: left; cursor: pointer; border-radius: 4px;"
                    onmouseover="this.style.background='#f7fafc'" 
                    onmouseout="this.style.background='none'">
                <i class="fas fa-file-excel" style="color: #48bb78; margin-right: 0.5rem;"></i>
                Excel Export (Customizable)
            </button>
            <button onclick="exportAttendanceCSV(); closeExportMenu();" 
                    style="width: 100%; padding: 0.75rem; border: none; background: none; text-align: left; cursor: pointer; border-radius: 4px;"
                    onmouseover="this.style.background='#f7fafc'" 
                    onmouseout="this.style.background='none'">
                <i class="fas fa-file-csv" style="color: #4299e1; margin-right: 0.5rem;"></i>
                Quick CSV Export
            </button>
        </div>
    `;

  exportBtn.parentElement.style.position = "relative";
  exportBtn.parentElement.appendChild(menu);

  // Close menu when clicking outside
  setTimeout(() => {
    document.addEventListener("click", function closeOnClickOutside(e) {
      if (!menu.contains(e.target) && e.target !== exportBtn) {
        closeExportMenu();
        document.removeEventListener("click", closeOnClickOutside);
      }
    });
  }, 100);
}

function closeExportMenu() {
  const menu = document.getElementById("exportMenu");
  if (menu) {
    menu.remove();
  }
}

// Initialize export functionality when page loads
document.addEventListener("DOMContentLoaded", function () {
  // Update export button to use enhanced functionality
  const exportBtn = document.querySelector(
    'button[onclick="exportAttendance()"]'
  );
  if (exportBtn) {
    // You can modify the button to show a dropdown instead
    // exportBtn.onclick = showExportMenu;
    // exportBtn.innerHTML = '<i class="fas fa-download"></i> Export Data <i class="fas fa-chevron-down" style="margin-left: 0.5rem;"></i>';
  }

  console.log("Enhanced export functionality initialized");
});

// ============================================
// VERIFICATION PHOTO REVIEW FUNCTIONS
// ============================================

/**
 * Open verification photo modal for review
 * @param {string} recordId - The attendance record ID
 */
function openVerificationPhotoModal(recordId) {
  console.log(`Opening verification photo modal for record: ${recordId}`);

  const modal = document.getElementById("verificationPhotoModal");
  const modalBody = document.getElementById("verificationPhotoModalBody");

  if (!modal || !modalBody) {
    console.error("Verification photo modal elements not found");
    return;
  }

  // Show loading state
  modalBody.innerHTML = `
    <div class="verification-loading">
      <i class="fas fa-spinner fa-spin"></i>
      <p>Loading verification photo...</p>
    </div>
  `;

  modal.style.display = "block";

  // Fetch record details with verification photo
  fetch(`/api/attendance/${recordId}/verification-details`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to fetch verification details");
      }
      return response.json();
    })
    .then((data) => {
      if (!data.success) {
        throw new Error(data.message || "Failed to load verification data");
      }

      renderVerificationPhotoModal(data.record);
    })
    .catch((error) => {
      console.error("Error loading verification photo:", error);
      modalBody.innerHTML = `
        <div class="verification-error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Error loading verification photo. Please try again.</p>
          <button onclick="closeVerificationPhotoModal()" class="btn btn-secondary">Close</button>
        </div>
      `;
    });
}

/**
 * Render verification photo modal content
 * @param {Object} record - The attendance record with verification data
 */
function renderVerificationPhotoModal(record) {
  const modalBody = document.getElementById("verificationPhotoModalBody");

  const content = `
    <div class="verification-photo-review">
      <!-- Employee & Date Info -->
      <div class="verification-header-info">
        <h3>
          <i class="fas fa-user"></i>
          Employee: ${record.employee_id}
        </h3>
        <p>
          <i class="fas fa-calendar"></i>
          ${record.check_in_date} at ${record.check_in_time}
        </p>
      </div>

      <!-- Verification Photo -->
      <div class="verification-photo-container">
        ${
          record.verification_photo
            ? `<img src="${record.verification_photo}" 
                   alt="Verification Photo" 
                   class="verification-photo-large"
                   onclick="window.open(this.src, '_blank')" 
                   style="cursor: zoom-in;"
                   title="Click to view full size" />`
            : `<div class="no-photo">
                 <i class="fas fa-image"></i>
                 <p>No verification photo available</p>
               </div>`
        }
      </div>

      <!-- Location Details -->
      <div class="verification-details-grid">
        <div class="verification-detail-card">
          <h4>Location Name</h4>
          <p>${record.location_name}</p>
        </div>

        <div class="verification-detail-card">
          <h4>Distance from QR</h4>
          <p>${parseFloat(record.location_accuracy).toFixed(3)} miles</p>
        </div>

        <div class="verification-detail-card">
          <h4>Verification Status</h4>
          <p>
            <span class="verification-status-pending">
              <i class="fas fa-clock"></i>
              Pending Review
            </span>
          </p>
        </div>

        <div class="verification-detail-card">
          <h4>Device</h4>
          <p>${record.device_info || "Unknown"}</p>
        </div>
      </div>

      <!-- Address Information -->
      <div class="verification-detail-card" style="grid-column: 1 / -1;">
        <h4>Check-in Address</h4>
        <p>${record.checked_in_address || "No address recorded"}</p>
      </div>

      <!-- Action Buttons -->
      <div class="verification-actions">
        <button onclick="updateVerificationStatus(${
          record.id
        }, 'approved')" class="btn-approve">
          <i class="fas fa-check-circle"></i>
          Approve Check-in
        </button>
        <button onclick="updateVerificationStatus(${
          record.id
        }, 'rejected')" class="btn-reject">
          <i class="fas fa-times-circle"></i>
          Reject Check-in
        </button>
      </div>
    </div>
  `;

  modalBody.innerHTML = content;
}

/**
 * Close verification photo modal
 */
function closeVerificationPhotoModal() {
  const modal = document.getElementById("verificationPhotoModal");
  if (modal) {
    modal.style.display = "none";
  }
}

/**
 * Update verification status (approve/reject)
 * @param {number} recordId - The attendance record ID
 * @param {string} status - The new status ('approved' or 'rejected')
 */
function updateVerificationStatus(recordId, status) {
  if (
    !confirm(
      `Are you sure you want to ${status} this verification?\n\nThis action will be logged for audit purposes.`
    )
  ) {
    return;
  }

  console.log(`Updating verification status for record ${recordId} to ${status}`);

  // Show loading state
  const modalBody = document.getElementById("verificationPhotoModalBody");
  modalBody.innerHTML = `
    <div class="verification-loading">
      <i class="fas fa-spinner fa-spin"></i>
      <p>Updating verification status...</p>
    </div>
  `;

  // Send update request
  fetch(`/verification-review/${recordId}/update`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({
      status: status,
      note: `Verification ${status} from attendance report review`,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert(
          `Verification ${status} successfully!\n\nThe page will reload to show the updated status.`
        );
        closeVerificationPhotoModal();
        // Reload the page to show updated status
        window.location.reload();
      } else {
        throw new Error(data.message || "Failed to update verification status");
      }
    })
    .catch((error) => {
      console.error("Error updating verification status:", error);
      alert(`Error: ${error.message}\n\nPlease try again.`);
      // Reload modal to show previous state
      openVerificationPhotoModal(recordId);
    });
}

// Close verification modal when clicking outside
window.addEventListener("click", function (event) {
  const verificationModal = document.getElementById("verificationPhotoModal");

  if (event.target === verificationModal) {
    closeVerificationPhotoModal();
  }
});

// Keyboard shortcut for closing verification modal
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeVerificationPhotoModal();
  }
});