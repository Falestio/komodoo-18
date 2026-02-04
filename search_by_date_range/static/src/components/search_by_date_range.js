/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useState, onMounted } from "@odoo/owl";

/**
 * Patch ListController to add date range and numeric range search filters
 */
patch(ListController.prototype, {
    setup() {
        super.setup();
        
        this.dateRangeState = useState({
            dateFields: [],
            numericFields: [],
            selectedDateField: '',
            dateFrom: '',
            dateTo: '',
            selectedNumericField: '',
            numericFrom: '',
            numericTo: '',
            showDateFilter: false,
            showNumericFilter: false,
        });
        
        this._rangeFilterGroupId = null;
        
        onMounted(() => {
            this._initRangeFilters();
        });
    },

    /**
     * Initialize range filters by detecting date and numeric fields
     */
    _initRangeFilters() {
        const fields = this.props.archInfo?.fields || this.model?.root?.fields || {};
        const columns = this.props.archInfo?.columns || [];
        
        const dateFields = [];
        const numericFields = [];
        
        // Get fields from columns
        for (const column of columns) {
            if (column.type !== 'field') continue;
            
            const fieldName = column.name;
            const fieldInfo = fields[fieldName];
            
            if (!fieldInfo) continue;
            
            // Check for date/datetime fields
            if (['date', 'datetime'].includes(fieldInfo.type)) {
                dateFields.push({
                    name: fieldName,
                    string: fieldInfo.string || fieldName,
                    type: fieldInfo.type,
                });
            }
            
            // Check for numeric fields
            if (['integer', 'float', 'monetary'].includes(fieldInfo.type)) {
                numericFields.push({
                    name: fieldName,
                    string: fieldInfo.string || fieldName,
                    type: fieldInfo.type,
                });
            }
        }
        
        this.dateRangeState.dateFields = dateFields;
        this.dateRangeState.numericFields = numericFields;
        this.dateRangeState.showDateFilter = dateFields.length > 0;
        this.dateRangeState.showNumericFilter = numericFields.length > 0;
        
        if (dateFields.length > 0) {
            this.dateRangeState.selectedDateField = dateFields[0].name;
        }
        if (numericFields.length > 0) {
            this.dateRangeState.selectedNumericField = numericFields[0].name;
        }
    },

    /**
     * Handle date field selection change
     */
    onDateFieldChange(ev) {
        this.dateRangeState.selectedDateField = ev.target.value;
    },

    /**
     * Handle date from change
     */
    onDateFromChange(ev) {
        this.dateRangeState.dateFrom = ev.target.value;
    },

    /**
     * Handle date to change
     */
    onDateToChange(ev) {
        this.dateRangeState.dateTo = ev.target.value;
    },

    /**
     * Handle numeric field selection change
     */
    onNumericFieldChange(ev) {
        this.dateRangeState.selectedNumericField = ev.target.value;
    },

    /**
     * Handle numeric from change
     */
    onNumericFromChange(ev) {
        this.dateRangeState.numericFrom = ev.target.value;
    },

    /**
     * Handle numeric to change
     */
    onNumericToChange(ev) {
        this.dateRangeState.numericTo = ev.target.value;
    },

    /**
     * Build domain from current filter values
     */
    _buildRangeDomain() {
        const domainParts = [];
        
        // Build date range domain
        if (this.dateRangeState.selectedDateField) {
            const fieldName = this.dateRangeState.selectedDateField;
            const dateFrom = this.dateRangeState.dateFrom;
            const dateTo = this.dateRangeState.dateTo;
            
            if (dateFrom) {
                domainParts.push([fieldName, '>=', dateFrom]);
            }
            if (dateTo) {
                // For datetime fields, we need to include the entire end date
                const fieldInfo = this.dateRangeState.dateFields.find(f => f.name === fieldName);
                if (fieldInfo && fieldInfo.type === 'datetime') {
                    domainParts.push([fieldName, '<=', dateTo + ' 23:59:59']);
                } else {
                    domainParts.push([fieldName, '<=', dateTo]);
                }
            }
        }
        
        // Build numeric range domain
        if (this.dateRangeState.selectedNumericField) {
            const fieldName = this.dateRangeState.selectedNumericField;
            const numFrom = this.dateRangeState.numericFrom;
            const numTo = this.dateRangeState.numericTo;
            
            if (numFrom !== '' && !isNaN(parseFloat(numFrom))) {
                domainParts.push([fieldName, '>=', parseFloat(numFrom)]);
            }
            if (numTo !== '' && !isNaN(parseFloat(numTo))) {
                domainParts.push([fieldName, '<=', parseFloat(numTo)]);
            }
        }
        
        return domainParts;
    },

    /**
     * Build filter description for display
     */
    _buildFilterDescription() {
        const parts = [];
        
        if (this.dateRangeState.selectedDateField && (this.dateRangeState.dateFrom || this.dateRangeState.dateTo)) {
            const fieldInfo = this.dateRangeState.dateFields.find(f => f.name === this.dateRangeState.selectedDateField);
            const fieldName = fieldInfo ? fieldInfo.string : this.dateRangeState.selectedDateField;
            let dateDesc = fieldName + ': ';
            if (this.dateRangeState.dateFrom && this.dateRangeState.dateTo) {
                dateDesc += `${this.dateRangeState.dateFrom} ~ ${this.dateRangeState.dateTo}`;
            } else if (this.dateRangeState.dateFrom) {
                dateDesc += `>= ${this.dateRangeState.dateFrom}`;
            } else {
                dateDesc += `<= ${this.dateRangeState.dateTo}`;
            }
            parts.push(dateDesc);
        }
        
        if (this.dateRangeState.selectedNumericField && (this.dateRangeState.numericFrom !== '' || this.dateRangeState.numericTo !== '')) {
            const fieldInfo = this.dateRangeState.numericFields.find(f => f.name === this.dateRangeState.selectedNumericField);
            const fieldName = fieldInfo ? fieldInfo.string : this.dateRangeState.selectedNumericField;
            let numDesc = fieldName + ': ';
            if (this.dateRangeState.numericFrom !== '' && this.dateRangeState.numericTo !== '') {
                numDesc += `${this.dateRangeState.numericFrom} ~ ${this.dateRangeState.numericTo}`;
            } else if (this.dateRangeState.numericFrom !== '') {
                numDesc += `>= ${this.dateRangeState.numericFrom}`;
            } else {
                numDesc += `<= ${this.dateRangeState.numericTo}`;
            }
            parts.push(numDesc);
        }
        
        return parts.join(', ') || 'Range Filter';
    },

    /**
     * Apply range filters
     */
    async onApplyRangeFilter() {
        const searchModel = this.env.searchModel;
        if (!searchModel) {
            console.warn("SearchModel not available");
            return;
        }
        
        // First, remove any previous range filter
        if (this._rangeFilterGroupId !== null) {
            searchModel.deactivateGroup(this._rangeFilterGroupId);
            this._rangeFilterGroupId = null;
        }
        
        const domainParts = this._buildRangeDomain();
        
        if (domainParts.length === 0) {
            return;
        }
        
        // Convert domain array to string representation
        const domainStr = JSON.stringify(domainParts);
        const description = this._buildFilterDescription();
        
        // Create a new filter and activate it
        const preFilter = {
            description: description,
            domain: domainStr,
            invisible: "True",
            type: "filter",
        };
        
        // Store the group id before creating to track it
        this._rangeFilterGroupId = searchModel.nextGroupId;
        
        searchModel.createNewFilters([preFilter]);
    },

    /**
     * Clear all range filters
     */
    async onClearRangeFilter() {
        this.dateRangeState.dateFrom = '';
        this.dateRangeState.dateTo = '';
        this.dateRangeState.numericFrom = '';
        this.dateRangeState.numericTo = '';
        
        const searchModel = this.env.searchModel;
        if (searchModel && this._rangeFilterGroupId !== null) {
            searchModel.deactivateGroup(this._rangeFilterGroupId);
            this._rangeFilterGroupId = null;
        }
    },
});
