import frappe
from frappe.utils import now_datetime, add_to_date, get_datetime

def check_completed_sessions():
    if not _due("completion_check_interval", "roster_last_completion_check"):
        return
    _mark_completed_sessions()
    _mark_last_run("roster_last_completion_check")

def process_pending_schedules():
    if not _due("backup_sync_interval", "roster_last_backup_sync"):
        return
    _sync_pending_schedules()
    _mark_last_run("roster_last_backup_sync")

def mark_overdue_deliverables():
    settings = frappe.get_single("Session Manager Settings")
    if now_datetime().hour != settings.overdue_check_hour:
        return
    _flip_overdue_deliverables()

def _due(interval_fieldname, cache_key):
    settings = frappe.get_single("Session Manager Settings")
    interval_minutes = settings.get(interval_fieldname) or 5
    last_run = frappe.cache().get_value(cache_key)
    if not last_run:
        return True
    return get_datetime(last_run) <= add_to_date(now_datetime(), minutes=-interval_minutes)

def _mark_last_run(cache_key):
    frappe.cache().set_value(cache_key, now_datetime())

def _mark_completed_sessions():
    now = now_datetime()
    # Process Mentoring Sessions
    if frappe.db.exists("DocType", "Mentoring Session"):
        sessions = frappe.get_all(
            "Mentoring Session",
            filters={"workflow_state": "Created"},
            fields=["name", "session_date", "end_time"]
        )
        for s in sessions:
            end = get_datetime(f"{s.session_date} {s.end_time}")
            if now > end:
                doc = frappe.get_doc("Mentoring Session", s.name)
                doc.workflow_state = "Completed"
                doc.save(ignore_permissions=True)
            
    # Process Lecture Sessions
    lecture_sessions = frappe.get_all(
        "Lecture Session",
        filters={"workflow_state": "Created"},
        fields=["name", "session_date", "end_time"]
    )
    for s in lecture_sessions:
        end = get_datetime(f"{s.session_date} {s.end_time}")
        if now > end:
            doc = frappe.get_doc("Lecture Session", s.name)
            doc.workflow_state = "Completed"
            doc.save(ignore_permissions=True)

def _sync_pending_schedules():
    # Process Mentoring Sessions
    if frappe.db.exists("DocType", "Mentoring Session"):
        pending = frappe.get_all(
            "Mentoring Session",
            filters={"workflow_state": "Scheduled", "event_id": ["in", ["", None]]},
            pluck="name"
        )
        for name in pending:
            frappe.get_doc("Mentoring Session", name).run_method("create_calendar_event")

    # Process Lecture Sessions
    pending_lectures = frappe.get_all(
        "Lecture Session",
        filters={"workflow_state": "Scheduled", "event_id": ["in", ["", None]]},
        pluck="name"
    )
    for name in pending_lectures:
        try:
            doc = frappe.get_doc("Lecture Session", name)
            doc.create_calendar_event()
        except Exception:
            frappe.log_error(f"Failed to create calendar event for Lecture Session {name}")

def _flip_overdue_deliverables():
    frappe.db.sql("""
        UPDATE `tabSession Fellow`
        SET deliverable_status = 'Overdue'
        WHERE deliverable_status = 'Pending'
          AND parent IN (
              SELECT name FROM `tabLecture Session`
              WHERE deliverable_due_date < CURDATE()
          )
    """)
    frappe.db.commit()
