/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Patch ListController to add export current list functionality
 */
patch(ListController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notification = useService("notification");
    },

    /**
     * Check if there are selected records
     */
    get hasSelectedRecords() {
        return this.model.root.selection && this.model.root.selection.length > 0;
    },

    /**
     * Get visible columns from the list view
     */
    _getVisibleColumns() {
        const columns = this.props.archInfo?.columns || [];
        const fields = this.props.archInfo?.fields || this.model?.root?.fields || {};
        
        const visibleColumns = [];
        
        for (const column of columns) {
            // Skip non-field columns (like buttons, etc)
            if (column.type !== 'field') continue;
            
            // Skip handle widget (drag handle)
            if (column.widget === 'handle') continue;
            
            // Skip invisible columns
            if (column.invisible === true || column.invisible === "True" || column.invisible === "1") continue;
            
            const fieldName = column.name;
            const fieldInfo = fields[fieldName];
            
            if (!fieldInfo) continue;
            
            visibleColumns.push({
                name: fieldName,
                string: column.string || fieldInfo.string || fieldName,
                type: fieldInfo.type,
                widget: column.widget,
            });
        }
        
        return visibleColumns;
    },

    /**
     * Format cell value based on field type
     */
    _formatCellValue(record, column) {
        const fieldName = column.name;
        const value = record.data[fieldName];
        
        if (value === undefined || value === null || value === false) {
            // For boolean false, return "False", otherwise empty
            if (column.type === 'boolean') {
                return _t("False");
            }
            return '';
        }
        
        switch (column.type) {
            case 'boolean':
                return value ? _t("True") : _t("False");
            
            case 'many2one':
                // Many2one returns [id, name] or object with display_name
                if (Array.isArray(value)) {
                    return value[1] || '';
                }
                return value.display_name || value.name || '';
            
            case 'many2many':
            case 'one2many':
                // Return count or names
                if (Array.isArray(value)) {
                    if (value.length === 0) return '';
                    if (value[0] && typeof value[0] === 'object') {
                        return value.map(v => v.display_name || v.name || '').join(', ');
                    }
                    return `${value.length} record(s)`;
                }
                if (value.records) {
                    return value.records.map(r => r.data.display_name || r.data.name || '').join(', ');
                }
                return '';
            
            case 'date':
            case 'datetime':
                if (value) {
                    // Odoo returns luxon DateTime object or string
                    if (typeof value === 'object' && value.toFormat) {
                        return column.type === 'date' 
                            ? value.toFormat('yyyy-MM-dd')
                            : value.toFormat('yyyy-MM-dd HH:mm:ss');
                    }
                    return String(value);
                }
                return '';
            
            case 'selection':
                // Selection returns the key, need to get the label
                const fieldInfo = this.model.root.fields[fieldName];
                if (fieldInfo && fieldInfo.selection) {
                    const selection = fieldInfo.selection.find(s => s[0] === value);
                    return selection ? selection[1] : value;
                }
                return value;
            
            case 'integer':
            case 'float':
            case 'monetary':
                return typeof value === 'number' ? value : parseFloat(value) || 0;
            
            case 'html':
                // Strip HTML tags
                if (typeof value === 'string') {
                    const div = document.createElement('div');
                    div.innerHTML = value;
                    return div.textContent || div.innerText || '';
                }
                return value;
            
            default:
                return String(value);
        }
    },

    /**
     * Export selected rows to Excel
     */
    async onExportCurrentList() {
        const selectedRecords = this.model.root.selection;
        const totalCount = this.model.root.count; // Total records matching current domain
        const limit = this.model.root.limit || 80; // Default page limit
        
        // Check if "Select All" was used (multiple ways to detect)
        const isDomainSelected = this.model.root.isDomainSelected || 
                                 this.model.root.selectDomain ||
                                 (selectedRecords.length === limit && totalCount > limit);
        
        if (!selectedRecords || selectedRecords.length === 0) {
            this.notification.add(_t("Please select at least one record to export."), {
                type: 'warning',
            });
            return;
        }
        
        // Get visible columns
        const columns = this._getVisibleColumns();
        
        if (columns.length === 0) {
            this.notification.add(_t("No columns available to export."), {
                type: 'warning',
            });
            return;
        }
        
        // Prepare headers
        const headers = columns.map(col => col.string);
        const fieldNames = columns.map(col => col.name);
        
        // ALWAYS use domain-based export for consistency and to support "Select All"
        // This ensures we export ALL records, not just the 80 loaded in the view
        const domain = this.model.root.domain || [];
        const context = this.model.root.context || {};
        
        // Get IDs of selected records
        const selectedIds = selectedRecords.map(record => record.resId);
        
        const exportData = {
            model: this.props.resModel,
            headers: headers,
            field_names: fieldNames,
            domain: domain,
            context: context,
            selected_ids: selectedIds,
            is_domain_selected: isDomainSelected,
            total_count: totalCount,
        };
        
        this._submitExportForm(exportData, isDomainSelected ? totalCount : selectedRecords.length);
    },
    
    /**
     * Submit export form
     */
    _submitExportForm(exportData, recordCount) {
        // Generate unique token
        const token = Date.now().toString();
        
        // Trigger download
        const url = '/web/export/current_list_xls';
        
        // Create form and submit
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        form.target = '_blank';
        
        const dataInput = document.createElement('input');
        dataInput.type = 'hidden';
        dataInput.name = 'data';
        dataInput.value = JSON.stringify(exportData);
        form.appendChild(dataInput);
        
        const tokenInput = document.createElement('input');
        tokenInput.type = 'hidden';
        tokenInput.name = 'token';
        tokenInput.value = token;
        form.appendChild(tokenInput);
        
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = odoo.csrf_token;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
        
        this.notification.add(
            recordCount === 'all' 
                ? _t("Exporting all records to Excel...") 
                : _t("Exporting %s record(s) to Excel...", recordCount), 
            { type: 'success' }
        );
    },
});
