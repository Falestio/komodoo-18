from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models


class KmHrAttendanceDashboard(models.AbstractModel):
    _name = "km.hr.attendance.dashboard"
    _description = "KM Attendance Dashboard"

    GRACE_MINUTES = 5

    def _get_employee_timezone(self, employee):
        tz_name = employee.tz or employee.user_id.tz or self.env.user.tz or "UTC"
        return pytz.timezone(tz_name)

    def _get_calendar_bounds(self, employee, work_date):
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if not calendar:
            return None

        weekday = str(work_date.weekday())
        lines = calendar.attendance_ids.filtered(
            lambda att: att.dayofweek == weekday
            and not att.display_type
            and att.hour_from is not None
            and att.hour_to is not None
            and att.hour_from < att.hour_to
            and (not att.date_from or att.date_from <= work_date)
            and (not att.date_to or att.date_to >= work_date)
        )
        if not lines:
            return None

        hour_from = min(lines.mapped("hour_from"))
        hour_to = max(lines.mapped("hour_to"))
        tz = self._get_employee_timezone(employee)

        start_local = datetime.combine(work_date, time.min) + timedelta(hours=hour_from)
        end_local = datetime.combine(work_date, time.min) + timedelta(hours=hour_to)

        start_utc = tz.localize(start_local).astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = tz.localize(end_local).astimezone(pytz.UTC).replace(tzinfo=None)
        return {
            "start": start_utc,
            "end": end_utc,
            "calendar": calendar,
        }

    def _classify_attendance(self, attendance, bounds):
        check_in = attendance.check_in
        check_out = attendance.check_out
        grace = timedelta(minutes=self.GRACE_MINUTES)

        result = {
            "on_time": False,
            "late": False,
            "early": False,
            "no_clock_in": False,
            "no_clock_out": False,
        }

        if not check_in:
            result["no_clock_in"] = True
            return result

        if not check_out:
            result["no_clock_out"] = True

        if not bounds:
            return result

        start = bounds["start"]
        end = bounds["end"]

        if check_in > start + grace:
            result["late"] = True
        if check_out and check_out < end - grace:
            result["early"] = True

        if not result["late"] and not result["early"] and check_out:
            result["on_time"] = True

        return result

    def _daterange(self, date_from, date_to):
        current = date_from
        while current <= date_to:
            yield current
            current += timedelta(days=1)

    def _count_day_offs(self, date_from, date_to):
        leaves = self.env["resource.calendar.leaves"].search([
            ("date_from", "<=", datetime.combine(date_to, time.max)),
            ("date_to", ">=", datetime.combine(date_from, time.min)),
            ("resource_id", "=", False),
        ])

        days = set()
        for leave in leaves:
            start = fields.Datetime.to_datetime(leave.date_from).date()
            end = fields.Datetime.to_datetime(leave.date_to).date()
            for day in self._daterange(max(start, date_from), min(end, date_to)):
                days.add(day)
        return len(days)

    def _employees_on_time_off(self, date_from, date_to, employee_ids=None):
        domain = [
            ("state", "=", "validate"),
            ("request_date_from", "<=", date_to),
            ("request_date_to", ">=", date_from),
        ]
        if employee_ids is not None:
            domain.append(("employee_id", "in", employee_ids))
        leaves = self.env["hr.leave"].search(domain)
        return set(leaves.mapped("employee_id").ids)

    def _employee_leave_days(self, employee, date_from, date_to):
        leaves = self.env["hr.leave"].search([
            ("state", "=", "validate"),
            ("employee_id", "=", employee.id),
            ("request_date_from", "<=", date_to),
            ("request_date_to", ">=", date_from),
        ])
        days = set()
        for leave in leaves:
            start = max(leave.request_date_from, date_from)
            end = min(leave.request_date_to, date_to)
            for day in self._daterange(start, end):
                days.add(day)
        return days

    def _get_employees(self, search=None):
        domain = [("active", "=", True)]
        if search:
            domain.append(("name", "ilike", search))
        employees = self.env["hr.employee"].search(domain, order="name")
        return [{"id": emp.id, "name": emp.name} for emp in employees]

    @api.model
    def get_employees(self, search=None):
        return self._get_employees(search=search)

    @api.model
    def get_attendance_dashboard_data(self, date_from, date_to, search=None):
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        today = fields.Date.today()

        employees = self.env["hr.employee"].search([( "active", "=", True)])
        if search:
            employees = employees.filtered(lambda e: search.lower() in (e.name or "").lower())
        employee_ids = employees.ids

        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)

        attendance_domain = [
            ("employee_id", "in", employee_ids),
            ("check_in", "<=", end_dt),
            "|",
            ("check_out", ">=", start_dt),
            ("check_out", "=", False),
        ]
        attendances = self.env["hr.attendance"].search(attendance_domain, order="check_in desc")

        stats = {
            "on_time": 0,
            "late": 0,
            "early": 0,
            "no_clock_in": 0,
            "no_clock_out": 0,
            "absent": 0,
            "day_off": 0,
            "time_off": 0,
        }

        rows = []
        for att in attendances:
            work_date = fields.Datetime.to_datetime(att.check_in).date() if att.check_in else fields.Date.today()
            bounds = self._get_calendar_bounds(att.employee_id, work_date)
            flags = self._classify_attendance(att, bounds)

            stats["on_time"] += 1 if flags["on_time"] else 0
            stats["late"] += 1 if flags["late"] else 0
            stats["early"] += 1 if flags["early"] else 0
            stats["no_clock_in"] += 1 if flags["no_clock_in"] else 0
            stats["no_clock_out"] += 1 if flags["no_clock_out"] else 0
            rows.append({
                "id": att.id,
                "employee_id": att.employee_id.id,
                "employee_name": att.employee_id.name,
                "employee_image": f"/web/image/hr.employee/{att.employee_id.id}/image_128",
                "check_in_date": fields.Date.to_string(work_date) if att.check_in else None,
                "check_in": fields.Datetime.to_string(att.check_in) if att.check_in else None,
                "check_out": fields.Datetime.to_string(att.check_out) if att.check_out else None,
                "worked_hours": att.worked_hours,
                "status": "on_time" if flags["on_time"] else "late" if flags["late"] else "early" if flags["early"] else "no_clock_out" if flags["no_clock_out"] else "",
            })

        stats["day_off"] = self._count_day_offs(date_from, date_to)

        time_off_employees = self._employees_on_time_off(date_from, date_to, employee_ids=employee_ids)
        stats["time_off"] = len(time_off_employees)

        leave_days_map = {
            employee.id: self._employee_leave_days(employee, date_from, min(date_to, today))
            for employee in employees
        }

        absent_end = min(date_to, today)
        for work_date in self._daterange(date_from, absent_end):
            for employee in employees:
                bounds = self._get_calendar_bounds(employee, work_date)
                if not bounds:
                    continue

                if work_date in leave_days_map.get(employee.id, set()):
                    continue

                day_start = datetime.combine(work_date, time.min)
                day_end = datetime.combine(work_date, time.max)
                has_attendance = any(
                    att.employee_id.id == employee.id and att.check_in <= day_end and (att.check_out or day_end) >= day_start
                    for att in attendances
                )
                if not has_attendance:
                    stats["absent"] += 1

        return {
            "stats": stats,
            "attendances": rows,
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
        }

    @api.model
    def get_employee_history_data(self, employee_id, date_from, date_to):
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        employee = self.env["hr.employee"].browse(employee_id)

        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)

        attendance_domain = [
            ("employee_id", "=", employee.id),
            ("check_in", "<=", end_dt),
            "|",
            ("check_out", ">=", start_dt),
            ("check_out", "=", False),
        ]
        attendances = self.env["hr.attendance"].search(attendance_domain, order="check_in desc")

        stats = {
            "on_time": 0,
            "late": 0,
            "early": 0,
            "no_clock_in": 0,
            "no_clock_out": 0,
            "absent": 0,
            "day_off": 0,
            "time_off": 0,
            "next_workdays": 0,
        }

        rows = []
        for att in attendances:
            work_date = fields.Datetime.to_datetime(att.check_in).date() if att.check_in else fields.Date.today()
            bounds = self._get_calendar_bounds(att.employee_id, work_date)
            flags = self._classify_attendance(att, bounds)

            stats["on_time"] += 1 if flags["on_time"] else 0
            stats["late"] += 1 if flags["late"] else 0
            stats["early"] += 1 if flags["early"] else 0
            stats["no_clock_in"] += 1 if flags["no_clock_in"] else 0
            stats["no_clock_out"] += 1 if flags["no_clock_out"] else 0
            rows.append({
                "id": att.id,
                "check_in": fields.Datetime.to_string(att.check_in) if att.check_in else None,
                "check_out": fields.Datetime.to_string(att.check_out) if att.check_out else None,
                "worked_hours": att.worked_hours,
                "status": "on_time" if flags["on_time"] else "late" if flags["late"] else "early" if flags["early"] else "no_clock_out" if flags["no_clock_out"] else "",
            })

        stats["day_off"] = self._count_day_offs(date_from, date_to)
        time_off_employees = self._employees_on_time_off(date_from, date_to, employee_ids=[employee.id])
        stats["time_off"] = len(time_off_employees)

        today = fields.Date.today()
        absent_end = min(date_to, today)
        time_off_days = self._employee_leave_days(employee, date_from, absent_end)
        for work_date in self._daterange(date_from, absent_end):
            bounds = self._get_calendar_bounds(employee, work_date)
            if not bounds:
                continue
            if work_date in time_off_days:
                continue

            day_start = datetime.combine(work_date, time.min)
            day_end = datetime.combine(work_date, time.max)
            has_attendance = any(
                att.check_in <= day_end and (att.check_out or day_end) >= day_start
                for att in attendances
            )
            if not has_attendance:
                stats["absent"] += 1

        future_start = max(today, date_from)
        time_off_future = self._employee_leave_days(employee, future_start, date_to)
        for work_date in self._daterange(future_start, date_to):
            bounds = self._get_calendar_bounds(employee, work_date)
            if not bounds:
                continue
            if work_date in time_off_future:
                continue
            stats["next_workdays"] += 1

        return {
            "employee": {"id": employee.id, "name": employee.name},
            "stats": stats,
            "attendances": rows,
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
        }
