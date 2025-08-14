document.addEventListener('DOMContentLoaded', function() {
    console.log('Simple Export Configuration loaded');
    
    // Setup basic event listeners
    setupBasicListeners();
    
    // Initial preview update
    setTimeout(updatePreview, 100);
});

function setupBasicListeners() {
    // Add listeners to checkboxes
    const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
    checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            toggleColumnName(this.value);
            setTimeout(updatePreview, 50);
        });
    });
    
    // Add listeners to name inputs
    const nameInputs = document.querySelectorAll('input[id^="name_"]');
    nameInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            setTimeout(updatePreview, 300);
        });
    });
    
    // Form validation
    const form = document.getElementById('exportForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const selected = document.querySelectorAll('input[name="selected_columns"]:checked');
            if (selected.length === 0) {
                e.preventDefault();
                alert('Please select at least one column to export.');
            }
        });
    }
}

function toggleColumnName(columnKey) {
    const checkbox = document.getElementById('col_' + columnKey);
    const nameGroup = document.getElementById('name_group_' + columnKey);
    
    if (checkbox && nameGroup) {
        if (checkbox.checked) {
            nameGroup.style.display = 'block';
        } else {
            nameGroup.style.display = 'none';
        }
    }
}

function updatePreview() {
    const previewHeader = document.getElementById('previewHeader');
    const previewTable = document.querySelector('.preview-table tbody');
    
    if (!previewHeader || !previewTable) return;
    
    const selectedColumns = Array.from(document.querySelectorAll('input[name="selected_columns"]:checked'));
    
    if (selectedColumns.length === 0) {
        previewHeader.innerHTML = '';
        previewTable.innerHTML = '<tr><td colspan="100%" style="text-align:center; padding:2rem;">No columns selected</td></tr>';
        updateGenerateButton(0);
        return;
    }
    
    // Build header
    let headerHTML = '';
    selectedColumns.forEach(function(checkbox) {
        const columnKey = checkbox.value;
        const nameInput = document.getElementById('name_' + columnKey);
        const customName = nameInput ? nameInput.value : columnKey;
        headerHTML += '<th>' + customName + '</th>';
    });
    previewHeader.innerHTML = headerHTML;
    
    // Build sample row
    let sampleRowHTML = '<tr>';
    selectedColumns.forEach(function(checkbox) {
        const columnKey = checkbox.value;
        const sampleData = getSampleData(columnKey);
        sampleRowHTML += '<td>' + sampleData + '</td>';
    });
    sampleRowHTML += '</tr>';
    previewTable.innerHTML = sampleRowHTML;
    
    updateGenerateButton(selectedColumns.length);
}

function getSampleData(columnKey) {
    const samples = {
        'employee_id': 'EMP001',
        'location_name': 'Main Office',
        'status': 'Check In',
        'check_in_date': '2025-01-15',
        'check_in_time': '09:30:00',
        'qr_address': '123 Business St',
        'address': '123 Business St',
        'device_info': 'iPhone',
        'ip_address': '192.168.1.100',
        'user_agent': 'Mobile Safari',
        'latitude': '40.7128',
        'longitude': '-74.0060',
        'accuracy': '5.2',
        'location_accuracy': '0.003'
    };
    return samples[columnKey] || 'Sample';
}

function updateGenerateButton(columnCount) {
    const generateBtn = document.getElementById('generateBtn');
    if (!generateBtn) return;
    
    if (columnCount === 0) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = 'Select columns to export';
    } else {
        generateBtn.disabled = false;
        generateBtn.innerHTML = 'Generate Excel Export (' + columnCount + ' columns)';
    }
}

function selectAllColumns() {
    const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
    checkboxes.forEach(function(checkbox) {
        checkbox.checked = true;
        toggleColumnName(checkbox.value);
    });
    updatePreview();
}

function deselectAllColumns() {
    const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
    checkboxes.forEach(function(checkbox) {
        checkbox.checked = false;
        toggleColumnName(checkbox.value);
    });
    updatePreview();
}

function resetToDefaults() {
    // Get checkboxes and reset to defaults
    const checkboxes = document.querySelectorAll('input[name="selected_columns"]');
    checkboxes.forEach(function(checkbox) {
        // Default enabled columns
        const defaultEnabled = ['employee_id', 'location_name', 'status', 'check_in_date', 'check_in_time'];
        checkbox.checked = defaultEnabled.includes(checkbox.value);
        toggleColumnName(checkbox.value);
        
        // Reset name input
        const nameInput = document.getElementById('name_' + checkbox.value);
        if (nameInput) {
            nameInput.value = nameInput.getAttribute('value') || checkbox.value;
        }
    });
    updatePreview();
}