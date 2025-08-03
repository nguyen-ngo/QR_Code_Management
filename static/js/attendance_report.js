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

function loadTableData() {
  const table = document.getElementById("attendanceTable");
  if (table) {
    const rows = table.querySelectorAll("tbody tr");
    attendanceData = Array.from(rows).map((row, index) => {
      const cells = row.querySelectorAll("td");
      return {
        id: row.dataset.recordId,
        index: index + 1,
        employeeId: cells[1] ? cells[1].textContent.trim() : "",
        location: cells[2] ? cells[2].textContent.trim() : "",
        event: cells[3] ? cells[3].textContent.trim() : "",
        date: cells[4] ? cells[4].textContent.trim() : "",
        time: cells[5] ? cells[5].textContent.trim() : "",
        qr_address: cells[6]
          ? cells[6].getAttribute("title") || cells[6].textContent.trim()
          : "",
        checked_in_address: cells[7]
          ? cells[7].getAttribute("title") || cells[7].textContent.trim()
          : "",
        accuracy: cells[8] ? extractAccuracyValue(cells[8]) : null,
        accuracy_level: cells[8] ? extractAccuracyLevel(cells[8]) : "unknown",
        device: cells[9]
          ? cells[9].getAttribute("title") || cells[9].textContent.trim()
          : "",
        has_location_data: cells[8]
          ? !cells[8].textContent.includes("No GPS")
          : false,
        coordinates: extractCoordinates(cells[8]),
      };
    });

    filteredData = [...attendanceData];
    console.log(`Loaded ${attendanceData.length} attendance records`);
  }
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

function createTableRow(record, displayIndex) {
  const row = document.createElement("tr");
  row.dataset.recordId = record.id;

  // Create accuracy badge HTML
  const accuracyBadge =
    record.accuracy !== null
      ? `<span class="accuracy-badge accuracy-${
          record.accuracy_level
        }" title="GPS accuracy: ${record.accuracy}m">
            <i class="fas fa-crosshairs"></i>
            ${record.accuracy.toFixed(1)}m
            <small>(${record.accuracy_level})</small>
         </span>`
      : `<span class="accuracy-badge accuracy-unknown" title="No GPS data available">
            <i class="fas fa-question-circle"></i>
            No GPS
         </span>`;

  row.innerHTML = `
        <td>${displayIndex}</td>
        <td>
            <div class="employee-info">
                <span class="employee-id">${record.employeeId}</span>
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
                <i class="fas fa-qrcode"></i>
                <span title="${record.qr_address}">
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
                <i class="fas fa-location-arrow"></i>
                <span title="${record.checked_in_address}">
                    ${
                      record.checked_in_address.length > 50
                        ? record.checked_in_address.substring(0, 50) + "..."
                        : record.checked_in_address
                    }
                </span>
            </div>
        </td>
        <td>
            <div class="accuracy-info">
                ${accuracyBadge}
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
                <button onclick="editRecord('${record.id}')" 
                        class="action-btn btn-edit"
                        title="Edit Record">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        </td>
    `;

  return row;
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
  console.log(`Edit record: ${recordId}`);
  // Implement edit functionality
  alert("Edit functionality to be implemented");
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
      return {
        id: row.dataset.recordId,
        index: index + 1,
        employeeId: cells[1] ? cells[1].textContent.trim() : "",
        location: cells[2] ? cells[2].textContent.trim() : "",
        event: cells[3] ? cells[3].textContent.trim() : "",
        date: cells[4] ? cells[4].textContent.trim() : "",
        time: cells[5] ? cells[5].textContent.trim() : "",
        qr_address: cells[6]
          ? cells[6].getAttribute("title") || cells[6].textContent.trim()
          : "",
        checked_in_address: cells[7]
          ? cells[7].getAttribute("title") || cells[7].textContent.trim()
          : "",
        location_accuracy: cells[8] ? extractLocationAccuracy(cells[8]) : null,
        accuracy_level: cells[8]
          ? extractLocationAccuracyLevel(cells[8])
          : "unknown",
        device: cells[9]
          ? cells[9].getAttribute("title") || cells[9].textContent.trim()
          : "",
        has_location_data: cells[8]
          ? !cells[8].textContent.includes("Unknown")
          : false,
        coordinates: extractCoordinates(cells[8]),
      };
    });

    filteredData = [...attendanceData];
    console.log(
      `Loaded ${attendanceData.length} attendance records with location accuracy`
    );
  }
}

function extractLocationAccuracy(cell) {
  const text = cell.textContent;
  const match = text.match(/(\d+\.?\d*)\s*mi/);
  return match ? parseFloat(match[1]) : null;
}

function extractLocationAccuracyLevel(cell) {
  const text = cell.textContent;
  if (text.includes("excellent")) return "excellent";
  if (text.includes("good")) return "good";
  if (text.includes("fair")) return "fair";
  if (text.includes("poor")) return "poor";
  return "unknown";
}

function createTableRow(record, displayIndex) {
  const row = document.createElement("tr");
  row.dataset.recordId = record.id;

  // Create location accuracy badge HTML
  const locationAccuracyBadge =
    record.location_accuracy !== null
      ? `<span class="location-accuracy-badge accuracy-${
          record.accuracy_level
        }" 
                title="Distance between QR location and check-in location: ${
                  record.location_accuracy
                } miles">
            <i class="fas fa-ruler"></i>
            ${record.location_accuracy.toFixed(3)} mi
            <small>(${record.accuracy_level})</small>
         </span>`
      : `<span class="location-accuracy-badge accuracy-unknown" title="Location accuracy could not be calculated">
            <i class="fas fa-question-circle"></i>
            Unknown
         </span>`;

  row.innerHTML = `
        <td>${displayIndex}</td>
        <td>
            <div class="employee-info">
                <span class="employee-id">${record.employeeId}</span>
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
                <i class="fas fa-qrcode"></i>
                <span title="${record.qr_address}">
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
                <i class="fas fa-location-arrow"></i>
                <span title="${record.checked_in_address}">
                    ${
                      record.checked_in_address.length > 50
                        ? record.checked_in_address.substring(0, 50) + "..."
                        : record.checked_in_address
                    }
                </span>
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
                <button onclick="editRecord('${record.id}')" 
                        class="action-btn btn-edit"
                        title="Edit Record">
                    <i class="fas fa-edit"></i>
                </button>
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
    excellent: "#059669", // green
    good: "#10b981", // lighter green
    fair: "#f59e0b", // yellow
    poor: "#dc2626", // red
    unknown: "#6b7280", // gray
  };
  return colors[level] || colors["unknown"];
}

// Enhanced export function to include location accuracy
function exportAttendanceWithAccuracy() {
  // Build CSV header with location accuracy
  const headers = [
    "Employee ID",
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
  const rows = filteredData.map((record) => [
    record.employeeId,
    record.location,
    record.event,
    record.date,
    record.time,
    record.qr_address,
    record.checked_in_address,
    record.location_accuracy !== null
      ? record.location_accuracy.toFixed(3)
      : "Unknown",
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
