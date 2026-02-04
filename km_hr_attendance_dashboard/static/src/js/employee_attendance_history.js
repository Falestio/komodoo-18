/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class EmployeeAttendanceHistory extends Component {
    static template = "km_hr_attendance_dashboard.EmployeeAttendanceHistory";

    setup() {
        this.orm = useService("orm");

        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const currentMonth = `${year}-${month}`;

        const saved = this._loadState();
        const urlState = this._loadUrlState();

        this.state = useState({
            loading: false,
            month: urlState.month || saved.month || currentMonth,
            employees: [],
            employeeId: urlState.employeeId || saved.employeeId || null,
            stats: {},
            attendances: [],
        });

        onWillStart(async () => {
            await this.loadEmployees();
            const ctxEmployeeId = this.props.action?.context?.employee_id || this.props.action?.context?.active_id;
            const paramEmployeeId = this.props.action?.params?.employee_id;
            const targetEmployeeId = ctxEmployeeId || paramEmployeeId;
            if (targetEmployeeId) {
                this.state.employeeId = targetEmployeeId;
            } else if (this.state.employees.length) {
                this.state.employeeId = this.state.employees[0].id;
            }
            await this.loadData();
        });

        onWillUpdateProps((nextProps) => {
            const nextEmployeeId = nextProps?.action?.context?.employee_id
                || nextProps?.action?.context?.active_id
                || nextProps?.action?.params?.employee_id;
            if (nextEmployeeId && nextEmployeeId !== this.state.employeeId) {
                this.state.employeeId = nextEmployeeId;
                this.loadData();
            }
        });
    }

    async loadEmployees() {
        try {
            const employees = await this.orm.call(
                "km.hr.attendance.dashboard",
                "get_employees",
                []
            );
            this.state.employees = employees || [];
        } catch (error) {
            console.error("Error loading employees:", error);
        }
    }

    async loadData() {
        if (!this.state.employeeId) return;

        this.state.loading = true;
        try {
            const { dateFrom, dateTo } = this._getMonthRange(this.state.month);
            const result = await this.orm.call(
                "km.hr.attendance.dashboard",
                "get_employee_history_data",
                [this.state.employeeId, dateFrom, dateTo]
            );
            this.state.stats = result.stats || {};
            this.state.attendances = result.attendances || [];
            this._saveState();
            this._updateUrl();
        } catch (error) {
            console.error("Error loading employee history:", error);
        } finally {
            this.state.loading = false;
        }
    }

    _getMonthRange(month) {
        const [year, monthStr] = month.split("-");
        const monthIndex = parseInt(monthStr, 10) - 1;
        const start = new Date(parseInt(year, 10), monthIndex, 1);
        const end = new Date(parseInt(year, 10), monthIndex + 1, 0);
        const dateFrom = this._toDateInputValue(start);
        const dateTo = this._toDateInputValue(end);
        return { dateFrom, dateTo };
    }

    _toDateInputValue(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    onMonthChange(ev) {
        this.state.month = ev.target.value;
        this.loadData();
    }

    onEmployeeChange(ev) {
        this.state.employeeId = parseInt(ev.target.value, 10);
        this.loadData();
    }

    formatDateTime(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleString("id-ID", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    formatHours(hours) {
        if (hours === undefined || hours === null) return "-";
        return `${hours.toFixed(2)} h`;
    }

    _loadState() {
        try {
            return JSON.parse(localStorage.getItem("km_employee_attendance_history_state")) || {};
        } catch {
            return {};
        }
    }

    _saveState() {
        const payload = {
            month: this.state.month,
            employeeId: this.state.employeeId,
        };
        localStorage.setItem("km_employee_attendance_history_state", JSON.stringify(payload));
    }

    _loadUrlState() {
        const params = new URLSearchParams(window.location.search);
        const employeeId = params.get("employee_id");
        return {
            employeeId: employeeId ? parseInt(employeeId, 10) : undefined,
            month: params.get("month") || undefined,
        };
    }

    _updateUrl() {
        const params = new URLSearchParams(window.location.search);
        if (this.state.employeeId) {
            params.set("employee_id", String(this.state.employeeId));
        }
        if (this.state.month) {
            params.set("month", this.state.month);
        }
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, "", newUrl);
    }
}

registry.category("actions").add("km_employee_attendance_history", EmployeeAttendanceHistory);

export default EmployeeAttendanceHistory;
