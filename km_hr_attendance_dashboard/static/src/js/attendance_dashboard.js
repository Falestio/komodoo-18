/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class AttendanceDashboard extends Component {
    static template = "km_hr_attendance_dashboard.AttendanceDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const today = this._toDateInputValue(new Date());
        const saved = this._loadState();
        const urlState = this._loadUrlState();

        this.state = useState({
            loading: false,
            rangeMode: urlState.rangeMode ?? saved.rangeMode ?? false,
            date: urlState.date || saved.date || today,
            dateFrom: urlState.dateFrom || saved.dateFrom || today,
            dateTo: urlState.dateTo || saved.dateTo || today,
            searchText: urlState.searchText ?? saved.searchText ?? "",
            stats: {},
            attendances: [],
            sortBy: saved.sortBy || "employee",
            sortDir: saved.sortDir || "asc",
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    _toDateInputValue(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    async loadData() {
        this.state.loading = true;
        try {
            const dateFrom = this.state.rangeMode ? this.state.dateFrom : this.state.date;
            const dateTo = this.state.rangeMode ? this.state.dateTo : this.state.date;
            const result = await this.orm.call(
                "km.hr.attendance.dashboard",
                "get_attendance_dashboard_data",
                [dateFrom, dateTo, this.state.searchText]
            );
            this.state.stats = result.stats || {};
            this.state.attendances = result.attendances || [];
            this.state.dateFrom = result.date_from || dateFrom;
            this.state.dateTo = result.date_to || dateTo;
            this._saveState();
            this._updateUrl();
        } catch (error) {
            console.error("Error loading attendance dashboard:", error);
        } finally {
            this.state.loading = false;
        }
    }

    onToggleRangeMode() {
        this.state.rangeMode = !this.state.rangeMode;
        if (!this.state.rangeMode) {
            this.state.dateFrom = this.state.date;
            this.state.dateTo = this.state.date;
        }
        this.loadData();
    }

    onDateChange(ev) {
        this.state.date = ev.target.value;
        this.loadData();
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        if (this.state.dateTo < this.state.dateFrom) {
            this.state.dateTo = this.state.dateFrom;
        }
        this.loadData();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        if (this.state.dateTo < this.state.dateFrom) {
            this.state.dateFrom = this.state.dateTo;
        }
        this.loadData();
    }

    onSearchChange(ev) {
        this.state.searchText = ev.target.value.trim();
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

    formatDate(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleDateString("id-ID", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
        });
    }

    formatTime(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleTimeString("id-ID", {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    formatHours(hours) {
        if (hours === undefined || hours === null) return "-";
        return `${hours.toFixed(2)} h`;
    }

    onSort(column) {
        if (this.state.sortBy === column) {
            this.state.sortDir = this.state.sortDir === "asc" ? "desc" : "asc";
        } else {
            this.state.sortBy = column;
            this.state.sortDir = "asc";
        }
        this._saveState();
        this._updateUrl();
    }

    get sortedAttendances() {
        const data = [...this.state.attendances];
        const dir = this.state.sortDir === "asc" ? 1 : -1;
        const by = this.state.sortBy;

        return data.sort((a, b) => {
            const valA = this._getSortValue(a, by);
            const valB = this._getSortValue(b, by);
            if (valA < valB) return -1 * dir;
            if (valA > valB) return 1 * dir;
            return 0;
        });
    }

    _getSortValue(row, by) {
        switch (by) {
            case "date":
                return row.check_in_date || "";
            case "check_in":
                return row.check_in || "";
            case "check_out":
                return row.check_out || "";
            case "worked_hours":
                return row.worked_hours || 0;
            case "status":
                return row.status || "";
            case "employee":
            default:
                return (row.employee_name || "").toLowerCase();
        }
    }

    openAttendanceForm(attendanceId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'hr.attendance',
            res_id: attendanceId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    _loadState() {
        try {
            return JSON.parse(sessionStorage.getItem("km_attendance_dashboard_state")) || {};
        } catch {
            return {};
        }
    }

    _saveState() {
        const dateFrom = this.state.rangeMode ? this.state.dateFrom : this.state.date;
        const dateTo = this.state.rangeMode ? this.state.dateTo : this.state.date;
        const payload = {
            rangeMode: this.state.rangeMode,
            date: this.state.date,
            dateFrom,
            dateTo,
            searchText: this.state.searchText,
            sortBy: this.state.sortBy,
            sortDir: this.state.sortDir,
        };
        sessionStorage.setItem("km_attendance_dashboard_state", JSON.stringify(payload));
    }

    _loadUrlState() {
        const params = new URLSearchParams(window.location.search);
        const rangeMode = params.get("range") === "1";
        return {
            rangeMode: params.has("range") ? rangeMode : undefined,
            date: params.get("date") || undefined,
            dateFrom: params.get("from") || undefined,
            dateTo: params.get("to") || undefined,
            searchText: params.get("q") || undefined,
        };
    }

    _updateUrl() {
        const params = new URLSearchParams(window.location.search);
        params.set("range", this.state.rangeMode ? "1" : "0");
        params.set("date", this.state.date);
        params.set("from", this.state.dateFrom);
        params.set("to", this.state.dateTo);
        if (this.state.searchText) {
            params.set("q", this.state.searchText);
        } else {
            params.delete("q");
        }
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, "", newUrl);
    }
}

registry.category("actions").add("km_attendance_dashboard", AttendanceDashboard);

export default AttendanceDashboard;
