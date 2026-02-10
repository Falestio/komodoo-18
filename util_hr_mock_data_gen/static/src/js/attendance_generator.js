/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class AttendanceGenerator extends Component {
    static template = "util_hr_mock_data_gen.AttendanceGenerator";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const today = this._toDateInputValue(new Date());
        const firstDayOfMonth = this._toDateInputValue(new Date(new Date().getFullYear(), new Date().getMonth(), 1));

        this.state = useState({
            loading: false,
            generating: false,
            employees: [],
            selectedEmployees: new Set(),
            searchText: "",
            dateFrom: firstDayOfMonth,
            dateTo: today,
            checkInTime: "08:00",
            checkOutTime: "17:00",
            latePercentage: 10,
            overtimePercentage: 20,
            varianceMinutes: 30,
            randomize: true,
            deleteExisting: false,
            selectAll: false,
        });

        onWillStart(async () => {
            await this.loadEmployees();
        });
    }

    _toDateInputValue(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    async loadEmployees() {
        this.state.loading = true;
        try {
            const employees = await this.orm.call(
                "util.attendance.generator",
                "get_employees",
                []
            );
            this.state.employees = employees;
        } catch (error) {
            this.notification.add("Error loading employees: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    get filteredEmployees() {
        if (!this.state.searchText) {
            return this.state.employees;
        }
        const search = this.state.searchText.toLowerCase();
        return this.state.employees.filter(emp => 
            emp.name.toLowerCase().includes(search) ||
            (emp.department && emp.department.toLowerCase().includes(search)) ||
            (emp.job && emp.job.toLowerCase().includes(search))
        );
    }

    onSearchChange(ev) {
        this.state.searchText = ev.target.value.trim();
    }

    toggleEmployee(employeeId) {
        if (this.state.selectedEmployees.has(employeeId)) {
            this.state.selectedEmployees.delete(employeeId);
        } else {
            this.state.selectedEmployees.add(employeeId);
        }
        this._updateSelectAllState();
    }

    isSelected(employeeId) {
        return this.state.selectedEmployees.has(employeeId);
    }

    toggleSelectAll() {
        if (this.state.selectAll) {
            // Deselect all
            this.state.selectedEmployees.clear();
            this.state.selectAll = false;
        } else {
            // Select all visible employees
            this.filteredEmployees.forEach(emp => {
                this.state.selectedEmployees.add(emp.id);
            });
            this.state.selectAll = true;
        }
    }

    _updateSelectAllState() {
        const visibleIds = this.filteredEmployees.map(e => e.id);
        this.state.selectAll = visibleIds.length > 0 && 
            visibleIds.every(id => this.state.selectedEmployees.has(id));
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        if (this.state.dateTo < this.state.dateFrom) {
            this.state.dateTo = this.state.dateFrom;
        }
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        if (this.state.dateTo < this.state.dateFrom) {
            this.state.dateFrom = this.state.dateTo;
        }
    }

    async onGenerate() {
        if (this.state.selectedEmployees.size === 0) {
            this.notification.add("Please select at least one employee", {
                type: "warning",
            });
            return;
        }

        if (!confirm(`Generate attendance data for ${this.state.selectedEmployees.size} employee(s) from ${this.state.dateFrom} to ${this.state.dateTo}?`)) {
            return;
        }

        this.state.generating = true;
        try {
            // Parse check-in time
            const [checkInHour, checkInMinute] = this.state.checkInTime.split(':').map(Number);
            // Parse check-out time
            const [checkOutHour, checkOutMinute] = this.state.checkOutTime.split(':').map(Number);

            const params = {
                employee_ids: Array.from(this.state.selectedEmployees),
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                check_in_hour: checkInHour,
                check_in_minute: checkInMinute,
                check_out_hour: checkOutHour,
                check_out_minute: checkOutMinute,
                late_percentage: this.state.latePercentage,
                overtime_percentage: this.state.overtimePercentage,
                variance_minutes: this.state.varianceMinutes,
                randomize: this.state.randomize,
                delete_existing: this.state.deleteExisting,
            };

            const result = await this.orm.call(
                "util.attendance.generator",
                "generate_attendance",
                [params]
            );

            if (result.success) {
                this.notification.add(result.message, {
                    type: "success",
                    title: "Success",
                });
            } else {
                this.notification.add(result.message, {
                    type: "danger",
                    title: "Error",
                });
            }
        } catch (error) {
            this.notification.add("Error: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.generating = false;
        }
    }
}

registry.category("actions").add("util_attendance_generator", AttendanceGenerator);

export default AttendanceGenerator;
