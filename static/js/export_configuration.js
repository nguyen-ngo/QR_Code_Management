/**
 * Enhanced Export Configuration JavaScript with Drag & Drop
 * Handles column selection, preview updates, drag & drop reordering, and preference management
 */

// Global variables
let availableColumns = [];
let sortableInstance = null;
let savedColumnOrder = [];

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced Export Configuration with Drag & Drop initialized');
    
    // Initialize available columns data
    initializeColumnsData();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load saved preferences if available
    loadSavedPreferences();
    
    // Update preview on load
    updatePreview();
    
    // Initialize drag & drop
    initializeDragDrop();
});

function initializeColumnsData() {
    try {
        // Extract column data from the form
        const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
        availableColumns = Array.from(checkboxes).map(cb => {
            const columnKey = cb.value;
            const label = cb.parentElement.querySelector('label').textContent.trim();
            const nameInput = document.getElementById('name_' + columnKey);
            
            return {
                key: columnKey,
                label: label,
                defaultName: nameInput ? nameInput.value : label,
                enabled: cb.checked
            };
        });
        
        console.log('Initialized columns data:', availableColumns);
    } catch (error) {
        console.error('Error initializing columns data:', error);
    }
}

function setupEventListeners() {
    try {
        // Add change listeners to all column checkboxes
        const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                toggleColumnName(this.value);
                updateSelectedColumnsList();
                updatePreview();
                
                // Add visual feedback
                const columnItem = this.closest('.column-item');
                if (this.checked) {
                    columnItem.classList.add('selected');
                } else {
                    columnItem.classList.remove('selected');
                }
            });
        });
        
        // Add input listeners to all column name inputs
        const nameInputs = document.querySelectorAll('input[id^="name_"]');
        nameInputs.forEach(input => {
            input.addEventListener('input', debounce(() => {
                updateSelectedColumnsList();
                updatePreview();
            }, 300));
        });
        
        // Form validation before submit
        const form = document.getElementById('exportForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                if (!validateForm()) {
                    e.preventDefault();
                }
            });
        }
    } catch (error) {
        console.error('Error setting up event listeners:', error);
    }
}

function toggleColumnName(columnKey) {
    try {
        const checkbox = document.getElementById('col_' + columnKey);
        const nameGroup = document.getElementById('name_group_' + columnKey);
        
        if (checkbox && nameGroup) {
            if (checkbox.checked) {
                nameGroup.style.display = 'block';
                nameGroup.style.opacity = '0';
                setTimeout(() => {
                    nameGroup.style.opacity = '1';
                }, 10);
            } else {
                nameGroup.style.opacity = '0';
                setTimeout(() => {
                    nameGroup.style.display = 'none';
                }, 300);
            }
        }
    } catch (error) {
        console.error('Error toggling column name:', error);
    }
}

function initializeDragDrop() {
    try {
        const selectedColumnsList = document.getElementById('selectedColumnsList');
        if (selectedColumnsList) {
            sortableInstance = Sortable.create(selectedColumnsList, {
                animation: 200,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                handle: '.column-drag-handle',
                onStart: function(evt) {
                    console.log('Drag started:', evt.oldIndex);
                },
                onEnd: function(evt) {
                    console.log('Drag ended:', evt.oldIndex, '->', evt.newIndex);
                    updateColumnOrderNumbers();
                    updatePreview();
                    
                    // Save the new order
                    savePreferences();
                }
            });
            
            console.log('Drag & drop initialized successfully');
        }
    } catch (error) {
        console.error('Error initializing drag & drop:', error);
    }
}

function updateSelectedColumnsList() {
    try {
        const selectedColumnsList = document.getElementById('selectedColumnsList');
        const selectedColumnsSection = document.getElementById('selectedColumnsSection');
        
        if (!selectedColumnsList || !selectedColumnsSection) return;
        
        // Get currently selected columns
        const selectedColumns = Array.from(document.querySelectorAll('input[name="selected_columns"]:checked'));
        
        if (selectedColumns.length === 0) {
            selectedColumnsSection.style.display = 'none';
            return;
        }
        
        selectedColumnsSection.style.display = 'block';
        selectedColumnsSection.classList.add('has-columns');
        
        // Get current order if exists, otherwise use selection order
        let orderedColumns = [];
        if (savedColumnOrder.length > 0) {
            // Use saved order, but only include currently selected columns
            orderedColumns = savedColumnOrder.filter(key => 
                selectedColumns.some(cb => cb.value === key)
            );
            // Add any newly selected columns that weren't in saved order
            selectedColumns.forEach(cb => {
                if (!orderedColumns.includes(cb.value)) {
                    orderedColumns.push(cb.value);
                }
            });
        } else {
            orderedColumns = selectedColumns.map(cb => cb.value);
        }
        
        // Build the selected columns list HTML
        let listHTML = '';
        orderedColumns.forEach((columnKey, index) => {
            const nameInput = document.getElementById('name_' + columnKey);
            const columnData = availableColumns.find(col => col.key === columnKey);
            const customName = nameInput ? nameInput.value : (columnData ? columnData.label : columnKey);
            
            listHTML += `
                <div class="selected-column-item" data-column-key="${columnKey}">
                    <div class="selected-column-info">
                        <div class="column-drag-handle" title="Drag to reorder">
                            <i class="fas fa-grip-vertical"></i>
                        </div>
                        <div class="selected-column-details">
                            <div class="selected-column-name">${columnData ? columnData.label : columnKey}</div>
                            <div class="selected-column-export-name">Export as: "${customName}"</div>
                        </div>
                    </div>
                    <div class="column-order-number">${index + 1}</div>
                </div>
            `;
        });
        
        if (listHTML === '') {
            listHTML = `
                <div class="selected-columns-empty">
                    <i class="fas fa-hand-point-up"></i>
                    <p>Select columns above to see them here for reordering</p>
                </div>
            `;
        }
        
        selectedColumnsList.innerHTML = listHTML;
        
        // Re-initialize sortable after updating content
        if (sortableInstance) {
            sortableInstance.destroy();
        }
        initializeDragDrop();
        
        console.log(`Updated selected columns list with ${orderedColumns.length} columns`);
    } catch (error) {
        console.error('Error updating selected columns list:', error);
    }
}

function updateColumnOrderNumbers() {
    try {
        const orderNumbers = document.querySelectorAll('.column-order-number');
        orderNumbers.forEach((element, index) => {
            element.textContent = index + 1;
        });
    } catch (error) {
        console.error('Error updating column order numbers:', error);
    }
}

function getCurrentColumnOrder() {
    try {
        const selectedItems = document.querySelectorAll('.selected-column-item');
        return Array.from(selectedItems).map(item => item.dataset.columnKey);
    } catch (error) {
        console.error('Error getting current column order:', error);
        return [];
    }
}

function updateColumnOrderField() {
    try {
        const columnOrderField = document.getElementById('column_order');
        const currentOrder = getCurrentColumnOrder();
        if (columnOrderField) {
            columnOrderField.value = JSON.stringify(currentOrder);
        }
    } catch (error) {
        console.error('Error updating column order field:', error);
    }
}

function updatePreview() {
    try {
        const previewHeader = document.getElementById('previewHeader');
        const previewTable = document.querySelector('.preview-table tbody');
        
        if (!previewHeader || !previewTable) {
            console.warn('Preview elements not found');
            return;
        }
        
        // Get selected columns in their current order
        const currentOrder = getCurrentColumnOrder();
        
        if (currentOrder.length === 0) {
            // No columns selected
            previewHeader.innerHTML = '';
            previewTable.innerHTML = `
                <tr>
                    <td colspan="100%" class="preview-placeholder">
                        <i class="fas fa-exclamation-triangle"></i>
                        No columns selected - please select at least one column to export
                    </td>
                </tr>
            `;
            updateGenerateButton(0);
            return;
        }
        
        // Build header with order numbers
        let headerHTML = '';
        currentOrder.forEach((columnKey, index) => {
            const nameInput = document.getElementById('name_' + columnKey);
            const customName = nameInput ? nameInput.value : columnKey;
            
            headerHTML += `<th data-order="${index + 1}">${customName}</th>`;
        });
        previewHeader.innerHTML = headerHTML;
        
        // Build sample data row
        let sampleRowHTML = '<tr>';
        currentOrder.forEach(columnKey => {
            let sampleData = getSampleData(columnKey);
            
            // Special handling for address column to show the logic
            if (columnKey === 'address') {
                sampleData = `<span title="If location accuracy ≤ 0.5 miles: shows QR address, otherwise: shows actual check-in address">123 Business St, City*</span>`;
            }
            
            sampleRowHTML += `<td>${sampleData}</td>`;
        });
        sampleRowHTML += '</tr>';
        
        // Add explanation row if address column is selected
        const hasAddressColumn = currentOrder.includes('address');
        if (hasAddressColumn) {
            sampleRowHTML += `
                <tr style="background-color: #f8f9fa; font-size: 0.85em; color: #6c757d;">
                    <td colspan="${currentOrder.length}" style="text-align: center; padding: 0.75rem; font-style: italic;">
                        <i class="fas fa-info-circle"></i>
                        * Check-in Address: Shows QR address when location accuracy ≤ 0.5 miles, otherwise shows actual GPS address
                    </td>
                </tr>
            `;
        }
        
        previewTable.innerHTML = sampleRowHTML;
        
        // Update generate button
        updateGenerateButton(currentOrder.length);
        
        console.log(`Preview updated with ${currentOrder.length} columns in order:`, currentOrder);
    } catch (error) {
        console.error('Error updating preview:', error);
    }
}

function getSampleData(columnKey) {
    // Return sample data for each column type
    const sampleData = {
        'employee_id': 'EMP001',
        'location_name': 'Main Office',
        'status': 'Check In',
        'check_in_date': '2025-08-14',
        'check_in_time': '09:30:00',
        'qr_address': '123 Business St, City',
        'address': '123 Business St, City',
        'device_info': 'iPhone 14 Pro',
        'ip_address': '192.168.1.100',
        'user_agent': 'Mobile Safari',
        'latitude': '40.7128',
        'longitude': '-74.0060',
        'accuracy': '5.2',
        'location_accuracy': '0.003'
    };
    
    return sampleData[columnKey] || 'Sample Data';
}

function selectAllColumns() {
    try {
        const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
        checkboxes.forEach(checkbox => {
            if (!checkbox.checked) {
                checkbox.checked = true;
                checkbox.closest('.column-item').classList.add('selected');
                toggleColumnName(checkbox.value);
            }
        });
        updateSelectedColumnsList();
        updatePreview();
        
        console.log('All columns selected');
    } catch (error) {
        console.error('Error selecting all columns:', error);
    }
}

function deselectAllColumns() {
    try {
        const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                checkbox.checked = false;
                checkbox.closest('.column-item').classList.remove('selected');
                toggleColumnName(checkbox.value);
            }
        });
        updateSelectedColumnsList();
        updatePreview();
        
        console.log('All columns deselected');
    } catch (error) {
        console.error('Error deselecting all columns:', error);
    }
}

function resetToDefaults() {
    try {
        // Reset to default selections
        availableColumns.forEach(column => {
            const checkbox = document.getElementById('col_' + column.key);
            const nameInput = document.getElementById('name_' + column.key);
            const columnItem = checkbox ? checkbox.closest('.column-item') : null;
            
            if (checkbox) {
                checkbox.checked = column.enabled;
                if (column.enabled) {
                    columnItem?.classList.add('selected');
                } else {
                    columnItem?.classList.remove('selected');
                }
                toggleColumnName(column.key);
            }
            
            if (nameInput) {
                nameInput.value = column.defaultName;
            }
        });
        
        // Clear saved order
        savedColumnOrder = [];
        
        updateSelectedColumnsList();
        updatePreview();
        
        // Clear saved preferences
        try {
            localStorage.removeItem('exportPreferences');
        } catch (storageError) {
            console.warn('Could not clear saved preferences:', storageError);
        }
        
        console.log('Reset to default settings');
    } catch (error) {
        console.error('Error resetting to defaults:', error);
    }
}

function updateGenerateButton(columnCount) {
    try {
        const generateBtn = document.getElementById('generateBtn');
        if (!generateBtn) return;
        
        if (columnCount === 0) {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Select columns to export';
            generateBtn.classList.add('btn-disabled');
        } else {
            generateBtn.disabled = false;
            generateBtn.innerHTML = `<i class="fas fa-download"></i> Generate Excel Export (${columnCount} columns)`;
            generateBtn.classList.remove('btn-disabled');
        }
    } catch (error) {
        console.error('Error updating generate button:', error);
    }
}

function validateForm() {
    try {
        const selectedColumns = document.querySelectorAll('input[name="selected_columns"]:checked');
        
        if (selectedColumns.length === 0) {
            alert('Please select at least one column to export.');
            return false;
        }
        
        // Validate that all selected columns have names
        let hasEmptyNames = false;
        selectedColumns.forEach(checkbox => {
            const nameInput = document.getElementById('name_' + checkbox.value);
            if (nameInput && nameInput.value.trim() === '') {
                hasEmptyNames = true;
                nameInput.style.borderColor = '#e53e3e';
                nameInput.focus();
            } else if (nameInput) {
                nameInput.style.borderColor = '#e2e8f0';
            }
        });
        
        if (hasEmptyNames) {
            alert('Please provide names for all selected columns.');
            return false;
        }
        
        // Update column order field before submitting
        updateColumnOrderField();
        
        // Save preferences before submitting
        savePreferences();
        
        return true;
    } catch (error) {
        console.error('Error validating form:', error);
        return false;
    }
}

function savePreferences() {
    try {
        const selectedColumns = Array.from(document.querySelectorAll('input[name="selected_columns"]:checked'))
            .map(cb => cb.value);
        
        const columnNames = {};
        selectedColumns.forEach(col => {
            const input = document.getElementById('name_' + col);
            if (input) {
                columnNames[col] = input.value.trim();
            }
        });
        
        // Get current column order
        const columnOrder = getCurrentColumnOrder();
        
        const prefs = {
            selected_columns: selectedColumns,
            column_names: columnNames,
            column_order: columnOrder,
            timestamp: new Date().toISOString()
        };
        
        localStorage.setItem('exportPreferences', JSON.stringify(prefs));
        console.log('Preferences saved with column order:', prefs);
        
    } catch (e) {
        console.warn('Could not save preferences:', e);
    }
}

function loadSavedPreferences() {
    try {
        const savedPrefs = localStorage.getItem('exportPreferences');
        if (!savedPrefs) {
            console.log('No saved preferences found');
            // Check if there are already selected columns on page load and update preview
            const alreadySelected = document.querySelectorAll('input[name="selected_columns"]:checked');
            if (alreadySelected.length > 0) {
                console.log('Found pre-selected columns, updating preview');
                updateSelectedColumnsList();
                updatePreview();
            }
            return;
        }
        
        const prefs = JSON.parse(savedPrefs);
        
        // Check if preferences are not too old (30 days)
        const savedDate = new Date(prefs.timestamp || 0);
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        
        if (savedDate < thirtyDaysAgo) {
            localStorage.removeItem('exportPreferences');
            console.log('Saved preferences are too old, removed');
            // Check if there are already selected columns on page load and update preview
            const alreadySelected = document.querySelectorAll('input[name="selected_columns"]:checked');
            if (alreadySelected.length > 0) {
                console.log('Found pre-selected columns, updating preview');
                updateSelectedColumnsList();
                updatePreview();
            }
            return;
        }
        
        // Apply saved column selections
        if (prefs.selected_columns) {
            const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
            checkboxes.forEach(cb => {
                const shouldBeChecked = prefs.selected_columns.includes(cb.value);
                if (cb.checked !== shouldBeChecked) {
                    cb.checked = shouldBeChecked;
                    const columnItem = cb.closest('.column-item');
                    if (shouldBeChecked) {
                        columnItem?.classList.add('selected');
                    } else {
                        columnItem?.classList.remove('selected');
                    }
                    toggleColumnName(cb.value);
                }
            });
        }
        
        // Apply saved column names
        if (prefs.column_names) {
            Object.keys(prefs.column_names).forEach(key => {
                const input = document.getElementById('name_' + key);
                if (input && prefs.column_names[key]) {
                    input.value = prefs.column_names[key];
                }
            });
        }
        
        // Save column order for later use
        if (prefs.column_order) {
            savedColumnOrder = prefs.column_order;
        }
        
        console.log('Preferences loaded:', prefs);
        
        // Update preview after loading preferences
        updateSelectedColumnsList();
        updatePreview();
        
    } catch (e) {
        console.warn('Could not load saved preferences:', e);
        try {
            localStorage.removeItem('exportPreferences');
        } catch (removeError) {
            console.warn('Could not remove invalid preferences:', removeError);
        }
        
        // Check if there are already selected columns on page load and update preview
        const alreadySelected = document.querySelectorAll('input[name="selected_columns"]:checked');
        if (alreadySelected.length > 0) {
            console.log('Found pre-selected columns after preference error, updating preview');
            updateSelectedColumnsList();
            updatePreview();
        }
    }
}

// Utility function for debouncing
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

// Global functions for template usage
window.selectAllColumns = selectAllColumns;
window.deselectAllColumns = deselectAllColumns;
window.resetToDefaults = resetToDefaults;
window.toggleColumnName = toggleColumnName;
window.updateSelectedColumnsList = updateSelectedColumnsList;
window.getCurrentColumnOrder = getCurrentColumnOrder;
window.updateColumnOrderField = updateColumnOrderField;
window.savePreferences = savePreferences;

// Add CSS for disabled button
const style = document.createElement('style');
style.textContent = `
.btn-disabled {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
    background: #a0aec0 !important;
    pointer-events: none;
}

.btn-disabled:hover {
    transform: none !important;
    box-shadow: none !important;
}
`;
document.head.appendChild(style);