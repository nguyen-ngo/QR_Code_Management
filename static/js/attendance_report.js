/**
 * Attendance Report JavaScript
 * Handles filtering, sorting, pagination, and analytics for attendance data
 */

// Global variables
let currentPage = 1;
let entriesPerPage = 50;
let sortColumn = -1;
let sortDirection = 'asc';
let attendanceData = [];
let filteredData = [];

// Charts
let dailyChart = null;
let locationChart = null;

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Attendance Report page initialized');
    
    initializeReport();
    loadAttendanceData();
    initializeCharts();
    setupEventListeners();
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
    const table = document.getElementById('attendanceTable');
    if (table) {
        const rows = table.querySelectorAll('tbody tr');
        attendanceData = Array.from(rows).map((row, index) => {
            const cells = row.querySelectorAll('td');
            return {
                id: row.dataset.recordId,
                index: index + 1,
                employeeId: cells[1] ? cells[1].textContent.trim() : '',
                location: cells[2] ? cells[2].textContent.trim() : '',
                event: cells[3] ? cells[3].textContent.trim() : '',
                date: cells[4] ? cells[4].textContent.trim() : '',
                time: cells[5] ? cells[5].textContent.trim() : '',
                device: cells[6] ? cells[6].getAttribute('title') || cells[6].textContent.trim() : '',
                status: cells[7] ? cells[7].textContent.trim() : '',
                element: row
            };
        });
        
        filteredData = [...attendanceData];
    }
}

function setupEventListeners() {
    // Entries per page change
    const entriesSelect = document.getElementById('entriesPerPage');
    if (entriesSelect) {
        entriesSelect.addEventListener('change', changeEntriesPerPage);
    }
    
    // Filter form
    const filtersForm = document.getElementById('filtersForm');
    if (filtersForm) {
        filtersForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
        });
    }
    
    // Real-time employee filter
    const employeeFilter = document.getElementById('employee');
    if (employeeFilter) {
        employeeFilter.addEventListener('input', debounce(applyFilters, 300));
    }
    
    // Date and location filters
    const dateFilter = document.getElementById('date');
    const locationFilter = document.getElementById('location');
    
    if (dateFilter) {
        dateFilter.addEventListener('change', applyFilters);
    }
    
    if (locationFilter) {
        locationFilter.addEventListener('change', applyFilters);
    }
}

function changeEntriesPerPage() {
    const select = document.getElementById('entriesPerPage');
    entriesPerPage = select.value === 'all' ? filteredData.length : parseInt(select.value);
    currentPage = 1;
    updateTable();
    updatePagination();
}

function applyFilters() {
    const dateFilter = document.getElementById('date')?.value || '';
    const locationFilter = document.getElementById('location')?.value || '';
    const employeeFilter = document.getElementById('employee')?.value.toLowerCase() || '';
    
    filteredData = attendanceData.filter(record => {
        const matchesDate = !dateFilter || record.date === dateFilter;
        const matchesLocation = !locationFilter || record.location === locationFilter;
        const matchesEmployee = !employeeFilter || 
            record.employeeId.toLowerCase().includes(employeeFilter);
        
        return matchesDate && matchesLocation && matchesEmployee;
    });
    
    currentPage = 1;
    updateTable();
    updatePagination();
    updateFilterStats();
}

function clearFilters() {
    // Clear form inputs
    const form = document.getElementById('filtersForm');
    if (form) {
        form.reset();
    }
    
    // Reset filtered data
    filteredData = [...attendanceData];
    currentPage = 1;
    
    // Update display  
    updateTable();
    updatePagination();
    updateFilterStats();
    
    // Update URL without filters
    const url = new URL(window.location);
    url.search = '';
    window.history.pushState({}, '', url);
}

function sortTable(columnIndex) {
    const headers = ['index', 'employeeId', 'location', 'event', 'date', 'time', 'device', 'status'];
    const column = headers[columnIndex];
    
    if (sortColumn === columnIndex) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = columnIndex;
        sortDirection = 'asc';
    }
    
    filteredData.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        
        // Handle different data types
        if (column === 'date' || column === 'time') {
            aVal = new Date(column === 'date' ? aVal : `2000-01-01 ${aVal}`);
            bVal = new Date(column === 'date' ? bVal : `2000-01-01 ${bVal}`);
        } else if (column === 'index') {
            aVal = parseInt(aVal);
            bVal = parseInt(bVal);
        } else {
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();
        }
        
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    updateTable();
    updateSortIndicators(columnIndex);
}

function updateSortIndicators(activeColumn) {
    const headers = document.querySelectorAll('th[onclick]');
    headers.forEach((header, index) => {
        const icon = header.querySelector('i');
        if (icon) {
            if (index === activeColumn) {
                icon.className = `fas fa-sort-${sortDirection === 'asc' ? 'up' : 'down'}`;
            } else {
                icon.className = 'fas fa-sort';
            }
        }
    });
}

function updateTable() {
    const tbody = document.querySelector('#attendanceTable tbody');
    if (!tbody) return;
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * entriesPerPage;
    const endIndex = entriesPerPage === filteredData.length ? 
        filteredData.length : 
        Math.min(startIndex + entriesPerPage, filteredData.length);
    
    // Hide all rows first
    attendanceData.forEach(record => {
        if (record.element) {
            record.element.style.display = 'none';
        }
    });
    
    // Show filtered and paginated rows
    const visibleData = filteredData.slice(startIndex, endIndex);
    visibleData.forEach((record, index) => {
        if (record.element) {
            record.element.style.display = '';
            // Update row number
            const firstCell = record.element.querySelector('td:first-child');
            if (firstCell) {
                firstCell.textContent = startIndex + index + 1;
            }
        }
    });
    
    // Show empty state if no data
    showEmptyStateIfNeeded();
}

function showEmptyStateIfNeeded() {
    const tbody = document.querySelector('#attendanceTable tbody');
    let emptyRow = tbody.querySelector('.empty-row');
    
    if (filteredData.length === 0) {
        if (!emptyRow) {
            emptyRow = document.createElement('tr');
            emptyRow.className = 'empty-row';
            emptyRow.innerHTML = `
                <td colspan="9" style="text-align: center; padding: 3rem;">
                    <div style="color: #6b7280;">
                        <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <h3>No Records Found</h3>
                        <p>No attendance records match your current filters.</p>
                        <button onclick="clearFilters()" class="btn btn-primary" style="margin-top: 1rem;">
                            <i class="fas fa-refresh"></i> Clear Filters
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(emptyRow);
        }
        emptyRow.style.display = '';
    } else if (emptyRow) {
        emptyRow.style.display = 'none';
    }
}

function updatePagination() {
    const container = document.getElementById('paginationContainer');
    if (!container) return;
    
    const totalPages = Math.ceil(filteredData.length / entriesPerPage);
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let paginationHTML = '<div class="pagination">';
    
    // Previous button
    paginationHTML += `
        <button onclick="goToPage(${currentPage - 1})" 
                class="pagination-btn" 
                ${currentPage === 1 ? 'disabled' : ''}>
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
                    class="pagination-btn ${i === currentPage ? 'active' : ''}">
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
                ${currentPage === totalPages ? 'disabled' : ''}>
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    paginationHTML += '</div>';
    
    // Add pagination info
    const startRecord = (currentPage - 1) * entriesPerPage + 1;
    const endRecord = Math.min(currentPage * entriesPerPage, filteredData.length);
    
    paginationHTML += `
        <div class="pagination-info">
            Showing ${startRecord} to ${endRecord} of ${filteredData.length} entries
            ${filteredData.length !== attendanceData.length ? 
                `(filtered from ${attendanceData.length} total entries)` : ''}
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
    const table = document.getElementById('attendanceTable');
    if (table) {
        table.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function updateFilterStats() {
    // Update stats display if needed
    const totalRecords = filteredData.length;
    console.log(`Filtered records: ${totalRecords}`);
}

// Record actions
function viewRecordDetails(recordId) {
    const record = attendanceData.find(r => r.id == recordId);
    if (!record) return;
    
    const modal = document.getElementById('recordModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalTitle || !modalBody) return;
    
    modalTitle.textContent = `Attendance Record - ${record.employeeId}`;
    
    modalBody.innerHTML = `
        <div class="record-details">
            <div class="detail-grid">
                <div class="detail-item">
                    <strong>Employee ID:</strong>
                    <span>${record.employeeId}</span>
                </div>
                <div class="detail-item">
                    <strong>Location:</strong>
                    <span>${record.location}</span>
                </div>
                <div class="detail-item">
                    <strong>Event:</strong>
                    <span>${record.event}</span>
                </div>
                <div class="detail-item">
                    <strong>Date:</strong>
                    <span>${record.date}</span>
                </div>
                <div class="detail-item">
                    <strong>Time:</strong>
                    <span>${record.time}</span>
                </div>
                <div class="detail-item">
                    <strong>Device:</strong>
                    <span>${record.device}</span>
                </div>
                <div class="detail-item">
                    <strong>Status:</strong>
                    <span class="status-badge ${record.status.toLowerCase()}">
                        ${record.status}
                    </span>
                </div>
            </div>
        </div>
    `;
    
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('show'), 10);
}

function editRecord(recordId) {
    // Placeholder for edit functionality
    alert(`Edit functionality for record ${recordId} would be implemented here.`);
}

function deleteRecord(recordId) {
    const record = attendanceData.find(r => r.id == recordId);
    if (!record) return;
    
    const confirmed = confirm(
        `Are you sure you want to delete the attendance record for ${record.employeeId}?\n\n` +
        `Date: ${record.date}\n` +
        `Time: ${record.time}\n` +
        `Location: ${record.location}\n\n` +
        'This action cannot be undone.'
    );
    
    if (confirmed) {
        // Here you would make an API call to delete the record
        console.log(`Deleting record ${recordId}`);
        
        // For demo purposes, just remove from current data
        const index = attendanceData.findIndex(r => r.id == recordId);
        if (index > -1) {
            // Remove from DOM
            if (attendanceData[index].element) {
                attendanceData[index].element.remove();
            }
            
            // Remove from data arrays
            attendanceData.splice(index, 1);
            const filteredIndex = filteredData.findIndex(r => r.id == recordId);
            if (filteredIndex > -1) {
                filteredData.splice(filteredIndex, 1);
            }
            
            // Update display
            updateTable();
            updatePagination();
            
            showToast('Record deleted successfully', 'success');
        }
    }
}

function closeRecordModal() {
    const modal = document.getElementById('recordModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 200);
    }
}

// Export functionality
function exportAttendance() {
    const exportData = filteredData.map(record => ({
        'Employee ID': record.employeeId,
        'Location': record.location,
        'Event': record.event,
        'Date': record.date,
        'Time': record.time,
        'Device': record.device,
        'Status': record.status
    }));
    
    const csv = convertToCSV(exportData);
    downloadCSV(csv, `attendance_report_${new Date().toISOString().split('T')[0]}.csv`);
    
    showToast('Attendance data exported successfully', 'success');
}

function convertToCSV(data) {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => 
            headers.map(header => {
                const value = row[header];
                // Escape commas and quotes
                return typeof value === 'string' && (value.includes(',') || value.includes('"')) 
                    ? `"${value.replace(/"/g, '""')}"` 
                    : value;
            }).join(',')
        )
    ].join('\n');
    
    return csvContent;
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

function refreshReport() {
    showToast('Refreshing report...', 'info');
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

// Charts initialization
function initializeCharts() {
    loadAttendanceStats();
}

function loadAttendanceStats() {
    fetch('/api/attendance/stats')
        .then(response => response.json())
        .then(data => {
            createDailyChart(data.daily_stats || []);
            createLocationChart(data.location_stats || []);
        })
        .catch(error => {
            console.error('Error loading attendance stats:', error);
        });
}

function createDailyChart(dailyStats) {
    const ctx = document.getElementById('dailyChart');
    if (!ctx) return;
    
    if (dailyChart) {
        dailyChart.destroy();
    }
    
    dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dailyStats.map(stat => stat.date),
            datasets: [{
                label: 'Check-ins',
                data: dailyStats.map(stat => stat.checkins),
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                tension: 0.4,
                fill: true
            }, {
                label: 'Unique Employees',
                data: dailyStats.map(stat => stat.employees),
                borderColor: '#059669',
                backgroundColor: 'rgba(5, 150, 105, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function createLocationChart(locationStats) {
    const ctx = document.getElementById('locationChart');
    if (!ctx) return;
    
    if (locationChart) {
        locationChart.destroy();
    }
    
    locationChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: locationStats.map(stat => stat.location),
            datasets: [{
                data: locationStats.map(stat => stat.checkins),
                backgroundColor: [
                    '#2563eb',
                    '#059669',
                    '#d97706',
                    '#dc2626',
                    '#7c3aed',
                    '#0891b2',
                    '#65a30d',
                    '#c2410c'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'right'
                }
            }
        }
    });
}

// Utility functions
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

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;
    
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        padding: 1rem;
        z-index: 1000;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        border-left: 4px solid ${getToastColor(type)};
        max-width: 400px;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

function getToastIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

function getToastColor(type) {
    const colors = {
        success: '#059669',
        error: '#dc2626',
        warning: '#d97706',
        info: '#0891b2'
    };
    return colors[type] || colors.info;
}

// Global function exports
window.sortTable = sortTable;
window.changeEntriesPerPage = changeEntriesPerPage;
window.clearFilters = clearFilters;
window.goToPage = goToPage;
window.viewRecordDetails = viewRecordDetails;
window.editRecord = editRecord;
window.deleteRecord = deleteRecord;
window.closeRecordModal = closeRecordModal;
window.exportAttendance = exportAttendance;
window.refreshReport = refreshReport;