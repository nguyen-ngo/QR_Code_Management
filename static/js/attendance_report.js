/**
 * Enhanced Attendance Report JavaScript with Location Support
 * Fixed version - removes undefined function calls
 */

// Global variables
let currentPage = 1;
let entriesPerPage = 50;
let sortColumn = -1;
let sortDirection = 'asc';
let attendanceData = [];
let filteredData = [];

// Charts (if you want to add them later)
let dailyChart = null;
let locationChart = null;

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced Attendance Report page initialized');
    
    initializeReport();
    setupEventListeners();
    
    // Initialize location-specific features
    initializeLocationFeatures();
});

function initializeReport() {
    console.log('📊 Initializing attendance report...');
    
    // Load data from existing table
    loadTableData();
    
    // Initialize pagination if needed
    updatePagination();
    
    // Apply any initial filters
    applyFilters();
    
    console.log('✅ Report initialized successfully');
}

function loadTableData() {
    const table = document.getElementById('attendanceTable');
    if (!table) {
        console.log('⚠️ Attendance table not found');
        return;
    }
    
    const rows = table.querySelectorAll('tbody tr');
    attendanceData = Array.from(rows).map((row, index) => {
        const cells = row.querySelectorAll('td');
        return {
            id: row.dataset.recordId || index,
            index: index + 1,
            employeeId: cells[1] ? cells[1].textContent.trim() : '',
            location: cells[2] ? cells[2].textContent.trim() : '',
            event: cells[3] ? cells[3].textContent.trim() : '',
            date: cells[4] ? cells[4].textContent.trim() : '',
            time: cells[5] ? cells[5].textContent.trim() : '',
            // Location data (new columns)
            gpsStatus: cells[6] ? cells[6].textContent.trim() : '',
            coordinates: cells[7] ? cells[7].textContent.trim() : '',
            accuracy: cells[8] ? cells[8].textContent.trim() : '',
            address: cells[9] ? cells[9].textContent.trim() : '',
            device: cells[10] ? cells[10].getAttribute('title') || cells[10].textContent.trim() : '',
            status: cells[11] ? cells[11].textContent.trim() : '',
            row: row
        };
    });
    
    filteredData = [...attendanceData];
    console.log(`📋 Loaded ${attendanceData.length} attendance records`);
}

function setupEventListeners() {
    // Entries per page selector
    const entriesSelect = document.getElementById('entriesPerPage');
    if (entriesSelect) {
        entriesSelect.addEventListener('change', changeEntriesPerPage);
    }
    
    // Search functionality (if you have a search input)
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Filter form submission
    const filterForm = document.querySelector('form[action*="attendance"]');
    if (filterForm) {
        filterForm.addEventListener('submit', handleFilterSubmit);
    }
    
    console.log('👂 Event listeners set up');
}

function initializeLocationFeatures() {
    console.log('📍 Initializing location features...');
    
    // Count records with location data
    const recordsWithLocation = attendanceData.filter(record => 
        record.gpsStatus && record.gpsStatus.includes('GPS')
    ).length;
    
    const locationCoverage = attendanceData.length > 0 
        ? Math.round((recordsWithLocation / attendanceData.length) * 100)
        : 0;
    
    console.log(`📊 Location coverage: ${recordsWithLocation}/${attendanceData.length} (${locationCoverage}%)`);
    
    // Add click handlers for map links
    document.querySelectorAll('.map-link').forEach(link => {
        link.addEventListener('click', function(e) {
            console.log('🗺️ Opening map link:', this.href);
        });
    });
    
    // Add click handlers for view record buttons
    document.querySelectorAll('.action-btn[title*="View"]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const recordId = this.closest('tr').dataset.recordId;
            if (recordId) {
                viewRecord(recordId);
            }
        });
    });
}

function changeEntriesPerPage() {
    const select = document.getElementById('entriesPerPage');
    if (!select) return;
    
    entriesPerPage = select.value === 'all' ? filteredData.length : parseInt(select.value);
    currentPage = 1;
    
    console.log(`📄 Changed entries per page to: ${entriesPerPage}`);
    displayPage();
    updatePagination();
}

function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase().trim();
    
    if (searchTerm === '') {
        filteredData = [...attendanceData];
    } else {
        filteredData = attendanceData.filter(record => 
            record.employeeId.toLowerCase().includes(searchTerm) ||
            record.location.toLowerCase().includes(searchTerm) ||
            record.event.toLowerCase().includes(searchTerm) ||
            record.address.toLowerCase().includes(searchTerm)
        );
    }
    
    currentPage = 1;
    displayPage();
    updatePagination();
    
    console.log(`🔍 Search results: ${filteredData.length} records found`);
}

function handleFilterSubmit(event) {
    // Let the form submit normally to reload with filters
    console.log('🔽 Applying filters...');
}

function sortTable(columnIndex) {
    if (sortColumn === columnIndex) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = columnIndex;
        sortDirection = 'asc';
    }
    
    // Update sort indicators
    updateSortIndicators();
    
    // Sort the data
    const sortKey = getSortKey(columnIndex);
    if (sortKey) {
        filteredData.sort((a, b) => {
            let aVal = a[sortKey] || '';
            let bVal = b[sortKey] || '';
            
            // Convert to strings for comparison
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();
            
            if (sortDirection === 'asc') {
                return aVal.localeCompare(bVal);
            } else {
                return bVal.localeCompare(aVal);
            }
        });
        
        displayPage();
        
        console.log(`🔄 Sorted by column ${columnIndex} (${sortDirection})`);
    }
}

function getSortKey(columnIndex) {
    const sortKeys = {
        0: 'index',
        1: 'employeeId',
        2: 'location', 
        3: 'event',
        4: 'date',
        5: 'time',
        6: 'gpsStatus',
        7: 'coordinates',
        8: 'accuracy',
        9: 'address',
        10: 'device',
        11: 'status'
    };
    
    return sortKeys[columnIndex];
}

function updateSortIndicators() {
    // Update sort arrows in table headers
    document.querySelectorAll('.attendance-table th i.fas').forEach((icon, index) => {
        icon.className = 'fas fa-sort';
        
        if (index === sortColumn) {
            icon.className = sortDirection === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
        }
    });
}

function displayPage() {
    const table = document.getElementById('attendanceTable');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Hide all rows first
    tbody.querySelectorAll('tr').forEach(row => {
        row.style.display = 'none';
    });
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * entriesPerPage;
    const endIndex = startIndex + (entriesPerPage === filteredData.length ? filteredData.length : entriesPerPage);
    
    // Show relevant rows
    for (let i = startIndex; i < endIndex && i < filteredData.length; i++) {
        const record = filteredData[i];
        if (record.row) {
            record.row.style.display = '';
        }
    }
    
    console.log(`📄 Displaying records ${startIndex + 1}-${Math.min(endIndex, filteredData.length)} of ${filteredData.length}`);
}

function updatePagination() {
    // This is a placeholder for pagination controls
    // You can implement pagination UI here if needed
    
    const totalPages = Math.ceil(filteredData.length / entriesPerPage);
    console.log(`📄 Page ${currentPage} of ${totalPages}`);
}

function applyFilters() {
    // Filters are handled by the backend through form submission
    // This function can be used for client-side filtering if needed
    console.log('🔽 Filters applied');
}

// Export and utility functions
function exportToCSV() {
    const table = document.getElementById('attendanceTable');
    if (!table) {
        console.error('❌ Table not found for export');
        return;
    }
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = [];
        const cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length - 1; j++) { // Skip actions column
            let cellText = cols[j].innerText.replace(/"/g, '""');
            // Clean up the text (remove extra whitespace, newlines)
            cellText = cellText.replace(/\s+/g, ' ').trim();
            row.push('"' + cellText + '"');
        }
        csv.push(row.join(','));
    }
    
    // Download CSV
    const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.download = `attendance_report_${new Date().toISOString().slice(0, 10)}.csv`;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    
    console.log('📄 CSV exported successfully');
}

function printReport() {
    window.print();
    console.log('🖨️ Print dialog opened');
}

function viewRecord(recordId) {
    console.log('👁️ Viewing record:', recordId);
    
    const modal = document.getElementById('recordModal');
    const detailsDiv = document.getElementById('recordDetails');
    
    if (!modal || !detailsDiv) {
        console.error('❌ Modal elements not found');
        return;
    }
    
    // Find the record row
    const row = document.querySelector(`tr[data-record-id="${recordId}"]`);
    if (!row) {
        console.error('❌ Record row not found');
        return;
    }
    
    const cells = row.querySelectorAll('td');
    
    detailsDiv.innerHTML = `
        <div class="record-detail-grid">
            <div class="detail-item">
                <strong>Employee ID:</strong>
                <span>${cells[1] ? cells[1].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Location:</strong>
                <span>${cells[2] ? cells[2].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Event:</strong>
                <span>${cells[3] ? cells[3].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Date:</strong>
                <span>${cells[4] ? cells[4].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Time:</strong>
                <span>${cells[5] ? cells[5].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>GPS Status:</strong>
                <span>${cells[6] ? cells[6].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Coordinates:</strong>
                <span>${cells[7] ? cells[7].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Accuracy:</strong>
                <span>${cells[8] ? cells[8].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Address:</strong>
                <span>${cells[9] ? cells[9].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Device:</strong>
                <span>${cells[10] ? cells[10].textContent.trim() : 'N/A'}</span>
            </div>
            <div class="detail-item">
                <strong>Status:</strong>
                <span>${cells[11] ? cells[11].textContent.trim() : 'N/A'}</span>
            </div>
        </div>
    `;
    
    modal.style.display = 'flex';
    console.log('✅ Record modal opened');
}

function closeModal() {
    const modal = document.getElementById('recordModal');
    if (modal) {
        modal.style.display = 'none';
        console.log('❌ Modal closed');
    }
}

function clearFilters() {
    // Get the current URL without query parameters
    const baseUrl = window.location.origin + window.location.pathname;
    window.location.href = baseUrl;
    
    console.log('🔄 Clearing filters and reloading');
}

// Global event handlers
window.onclick = function(event) {
    const modal = document.getElementById('recordModal');
    if (event.target === modal) {
        closeModal();
    }
}

// Make functions globally available
window.exportToCSV = exportToCSV;
window.printReport = printReport;
window.viewRecord = viewRecord;
window.closeModal = closeModal;
window.clearFilters = clearFilters;
window.sortTable = sortTable;
window.changeEntriesPerPage = changeEntriesPerPage;

console.log('📍 Enhanced Attendance Report JavaScript loaded successfully');
console.log('🔧 Available functions: exportToCSV, printReport, viewRecord, sortTable');