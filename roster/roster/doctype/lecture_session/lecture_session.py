# Copyright (c) 2026, Sakthi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, getdate, get_time


class LectureSession(Document):
	def validate(self):
		self.set_default_end_time()

	def on_update(self):
		"""Dispatch calendar actions based on workflow_state transitions."""
		prev_state = self.get_doc_before_save()
		prev_workflow = prev_state.workflow_state if prev_state else None

		if self.workflow_state != prev_workflow:
			if self.workflow_state == "Scheduled" and not self.event_id:
				self.create_calendar_event()
			elif self.workflow_state == "Cancelled" and self.event_id:
				self.cancel_calendar_event()
			elif self.workflow_state in ("Updated", "Rescheduled") and self.event_id:
				self.update_calendar_event()
			elif self.workflow_state == "Completed":
				if self.deliverable:
					self._send_deliverable_email()
				self._send_feedback_email()
		else:
			# Automatically trigger update if fields were modified while event is active
			if self.event_id and self.workflow_state not in ("Draft", "Cancelled"):
				changed = False
				for field in ("topic", "session_date", "start_time", "end_time", "mentor"):
					if self.has_value_changed(field):
						changed = True
						break
				if not changed and prev_state:
					prev_fellows = {f.fellow for f in prev_state.invited_fellows} if prev_state.invited_fellows else set()
					curr_fellows = {f.fellow for f in self.invited_fellows} if self.invited_fellows else set()
					if prev_fellows != curr_fellows:
						changed = True
				
				if changed:
					self.update_calendar_event()

	def set_default_end_time(self):
		if self.start_time and not self.end_time and self.session_date:
			base = get_datetime(f"{self.session_date} {self.start_time}")
			self.end_time = add_to_date(base, minutes=60).time()

	# ── Calendar Event CRUD ─────────────────────────────────────────

	def create_calendar_event(self):
		"""Create a Frappe Event and send invite emails to all participants."""
		starts_on = get_datetime(f"{self.session_date} {self.start_time}")
		ends_on = get_datetime(f"{self.session_date} {self.end_time}") if self.end_time else None

		event = frappe.new_doc("Event")
		event.subject = f"Lecture: {self.topic or 'Untitled Session'}"
		event.event_category = "Meeting"
		event.event_type = "Public"
		event.starts_on = starts_on
		event.ends_on = ends_on
		event.send_reminder = 1
		event.description = self._build_event_description()

		settings = frappe.get_single("Session Manager Settings")
		if settings.google_calendar:
			event.sync_with_google_calendar = 1
			event.add_video_conferencing = 1
			event.google_calendar = settings.google_calendar

		# Add mentor as participant
		if self.mentor:
			mentor_email = frappe.db.get_value("Mentor", self.mentor, "email")
			event.append("event_participants", {
				"reference_doctype": "Mentor",
				"reference_docname": self.mentor,
				"email": mentor_email,
			})

		# Add fellows
		for row in self.invited_fellows or []:
			if row.fellow:
				fellow_email = frappe.db.get_value("Fellow", row.fellow, "email")
				event.append("event_participants", {
					"reference_doctype": "Fellow",
					"reference_docname": row.fellow,
					"email": fellow_email,
				})

		event.insert(ignore_permissions=True)

		# Write back event reference and advance state
		self.db_set("event_id", event.name, update_modified=False)
		self.db_set("workflow_state", "Created", update_modified=False)

		# Send invite emails
		self._send_invite_emails(action="created")

	def cancel_calendar_event(self):
		"""Cancel the linked Frappe Event and notify participants."""
		if not self.event_id:
			return

		try:
			event = frappe.get_doc("Event", self.event_id)
			event.status = "Cancelled"
			event.save(ignore_permissions=True)
		except frappe.DoesNotExistError:
			frappe.log_error(
				f"Event {self.event_id} not found while cancelling Lecture Session {self.name}"
			)

		self._send_invite_emails(action="cancelled")

	def update_calendar_event(self):
		"""Update the linked Frappe Event with current session details."""
		if not self.event_id:
			return

		try:
			event = frappe.get_doc("Event", self.event_id)
		except frappe.DoesNotExistError:
			# Event was deleted externally — recreate
			self.db_set("event_id", "", update_modified=False)
			self.create_calendar_event()
			return

		event.subject = f"Lecture: {self.topic or 'Untitled Session'}"
		event.starts_on = get_datetime(f"{self.session_date} {self.start_time}")
		event.ends_on = (
			get_datetime(f"{self.session_date} {self.end_time}") if self.end_time else None
		)
		event.description = self._build_event_description()

		# Rebuild participant list
		event.event_participants = []
		if self.mentor:
			mentor_email = frappe.db.get_value("Mentor", self.mentor, "email")
			event.append("event_participants", {
				"reference_doctype": "Mentor",
				"reference_docname": self.mentor,
				"email": mentor_email,
			})
		for row in self.invited_fellows or []:
			if row.fellow:
				fellow_email = frappe.db.get_value("Fellow", row.fellow, "email")
				event.append("event_participants", {
					"reference_doctype": "Fellow",
					"reference_docname": row.fellow,
					"email": fellow_email,
				})

		# To prevent Frappe from creating duplicate events in Google Calendar if the 
		# first sync hasn't finished, we skip triggering GCal sync if event ID is missing.
		# The background job already queued will pick up our updated fields when it runs.
		is_pending_sync = event.sync_with_google_calendar and not event.google_calendar_event_id
		
		if is_pending_sync:
			event.sync_with_google_calendar = 0

		event.save(ignore_permissions=True)

		if is_pending_sync:
			event.db_set("sync_with_google_calendar", 1, update_modified=False)
		self._send_invite_emails(action="updated")

	# ── Helpers ──────────────────────────────────────────────────────

	def _build_event_description(self):
		"""Build a rich HTML description for the calendar event."""
		mentor_name = ""
		if self.mentor:
			mentor_name = frappe.db.get_value("Mentor", self.mentor, "mentor_name") or self.mentor

		lines = [
			f"<b>Topic:</b> {self.topic or '—'}",
			f"<b>Mentor:</b> {mentor_name}",
			f"<b>Date:</b> {frappe.format(self.session_date, {'fieldtype': 'Date'})}",
			f"<b>Time:</b> {self.start_time} – {self.end_time or 'TBD'}",
		]

		if self.meet_link:
			lines.append(f'<b>Meet Link:</b> <a href="{self.meet_link}">{self.meet_link}</a>')

		if self.notes:
			lines.append(f"<b>Notes:</b> {self.notes}")

		fellow_count = len(self.invited_fellows or [])
		lines.append(f"<b>Invited Fellows:</b> {fellow_count}")

		return "<br>".join(lines)

	def _get_participant_emails(self):
		"""Collect deduplicated email addresses of the mentor and all invited fellows."""
		emails = []

		if self.mentor:
			mentor_email = frappe.db.get_value("Mentor", self.mentor, "email")
			if mentor_email:
				emails.append(mentor_email)

		for row in self.invited_fellows or []:
			if row.fellow:
				fellow_email = frappe.db.get_value("Fellow", row.fellow, "email")
				if fellow_email:
					emails.append(fellow_email)

		# Deduplicate while preserving order
		seen = set()
		unique_emails = []
		for email in emails:
			if email not in seen:
				seen.add(email)
				unique_emails.append(email)

		return unique_emails

	def _send_invite_emails(self, action="created"):
		"""Send email notifications to all participants about the session."""
		recipients = self._get_participant_emails()
		if not recipients:
			return

		mentor_name = ""
		if self.mentor:
			mentor_name = frappe.db.get_value("Mentor", self.mentor, "mentor_name") or self.mentor

		action_labels = {
			"created": "Scheduled",
			"updated": "Updated",
			"cancelled": "Cancelled",
		}
		action_label = action_labels.get(action, action.title())

		settings = frappe.get_single("Session Manager Settings")
		if settings.invite_email_template:
			email_template = frappe.get_doc("Email Template", settings.invite_email_template)
			context = {
				"doc": self,
				"action_label": action_label,
				"mentor_name": mentor_name,
				"frappe": frappe
			}
			subject = frappe.render_template(email_template.subject, context)
			if email_template.use_html:
				message = frappe.render_template(email_template.response_html, context)
			else:
				message = frappe.render_template(email_template.response, context)
		else:
			subject = f"Lecture Session {action_label}: {self.topic or 'Untitled'}"

			# Build email body
			message = f"""
			<h3>Lecture Session {action_label}</h3>
			<table style="border-collapse: collapse; width: 100%;">
				<tr><td style="padding: 8px; font-weight: bold;">Topic</td><td style="padding: 8px;">{self.topic or '—'}</td></tr>
				<tr><td style="padding: 8px; font-weight: bold;">Mentor</td><td style="padding: 8px;">{mentor_name}</td></tr>
				<tr><td style="padding: 8px; font-weight: bold;">Date</td><td style="padding: 8px;">{frappe.format(self.session_date, {'fieldtype': 'Date'})}</td></tr>
				<tr><td style="padding: 8px; font-weight: bold;">Time</td><td style="padding: 8px;">{self.start_time} – {self.end_time or 'TBD'}</td></tr>
			"""

			if self.meet_link:
				message += f'<tr><td style="padding: 8px; font-weight: bold;">Meet Link</td><td style="padding: 8px;"><a href="{self.meet_link}">{self.meet_link}</a></td></tr>'

			if self.notes:
				message += f'<tr><td style="padding: 8px; font-weight: bold;">Notes</td><td style="padding: 8px;">{self.notes}</td></tr>'

			message += "</table>"

			if action == "cancelled":
				message += "<p style='color: #e74c3c; font-weight: bold;'>This session has been cancelled.</p>"

		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name,
				now=False,  # Queue for background sending
			)
		except Exception:
			frappe.log_error(f"Failed to send invite emails for Lecture Session {self.name}")

	def _send_deliverable_email(self):
		settings = frappe.get_single("Session Manager Settings")
		template_name = settings.deliverable_email_template
		if not template_name:
			frappe.log_error(f"No Deliverable Email Template configured for Lecture Session {self.name}.")
			return

		# Send only to fellows who attended
		attended_fellows = [f for f in self.invited_fellows if f.attended]
		if not attended_fellows:
			return
			
		email_template = frappe.get_doc("Email Template", template_name)

		for fellow in attended_fellows:
			fellow_email = frappe.db.get_value("Fellow", fellow.fellow, "email")
			if not fellow_email:
				continue
				
			try:
				context = {
					"doc": self,
					"fellow": fellow,
					"deliverable": self.deliverable
				}
				
				subject = frappe.render_template(email_template.subject, context)
				if email_template.use_html:
					message = frappe.render_template(email_template.response_html, context)
				else:
					message = frappe.render_template(email_template.response, context)
					
				frappe.sendmail(
					recipients=[fellow_email],
					message=message,
					subject=subject or f"Deliverables for {self.topic}",
					reference_doctype=self.doctype,
					reference_name=self.name,
					now=False
				)
			except Exception as e:
				frappe.log_error(f"Failed to send deliverable email to {fellow_email}: {str(e)}")

	def _send_feedback_email(self):
		settings = frappe.get_single("Session Manager Settings")
		template_name = settings.feedback_email_template
		if not template_name:
			return

		attended_fellows = [f for f in self.invited_fellows if f.attended]
		if not attended_fellows:
			return
			
		email_template = frappe.get_doc("Email Template", template_name)
		
		for fellow in attended_fellows:
			fellow_email = frappe.db.get_value("Fellow", fellow.fellow, "email")
			if not fellow_email:
				continue
				
			try:
				context = {"doc": self, "fellow": fellow, "fellow_email": fellow_email}
				
				subject = frappe.render_template(email_template.subject, context)
				if email_template.use_html:
					message = frappe.render_template(email_template.response_html, context)
				else:
					message = frappe.render_template(email_template.response, context)
					
				frappe.sendmail(
					recipients=[fellow_email],
					message=message,
					subject=subject or f"Feedback Request: {self.topic}",
					reference_doctype=self.doctype,
					reference_name=self.name,
					now=False
				)
			except Exception as e:
				frappe.log_error(f"Failed to send feedback email to {fellow_email}: {str(e)}")


@frappe.whitelist()
def get_all_active_fellows():
	"""Return all active Fellow records (name + fellow_name) for bulk-invite."""
	return frappe.get_all(
		"Fellow",
		filters={"active": 1},
		fields=["name", "fellow_name"],
		order_by="fellow_name asc",
	)


@frappe.whitelist()
def get_lecture_session_events(start, end, filters=None):
	"""Return Lecture Session records formatted for Frappe Calendar View.

	The calendar expects each event to have 'start' and 'end' as full datetime strings.
	We combine session_date + start_time / end_time into those.
	"""
	import json as _json

	conditions = {
		"session_date": ["between", [start, end]],
	}

	if filters:
		if isinstance(filters, str):
			filters = _json.loads(filters)
		if isinstance(filters, dict):
			conditions.update(filters)
		elif isinstance(filters, list):
			for f in filters:
				if len(f) >= 4:
					conditions[f[1]] = [f[2], f[3]]

	sessions = frappe.get_all(
		"Lecture Session",
		filters=conditions,
		fields=[
			"name", "topic", "session_date", "start_time", "end_time",
			"mentor", "workflow_state", "meet_link", "google_calendar_id"
		],
		order_by="session_date asc, start_time asc",
	)

	# Combine date + time into full datetime strings for the calendar widget
	for s in sessions:
		s["start"] = f"{s.session_date} {s.start_time or '00:00:00'}"
		s["end"] = f"{s.session_date} {s.end_time or s.start_time or '00:00:00'}"
		s["allDay"] = 0
		s["docstatus"] = 1  # Hack to force Frappe calendar to make event non-editable (non-draggable)

	return sessions

@frappe.whitelist()
def create_meeting_notes(session_name):
	from googleapiclient.discovery import build

	doc = frappe.get_doc("Lecture Session", session_name)
	
	# Find Google Drive integration for user
	g_drive_name = frappe.db.get_value("Google Drive", {"user": frappe.session.user, "enable": 1}, "name")
	if not g_drive_name and frappe.session.user == "Administrator":
		# Fallback for Administrator to use any enabled integration
		g_drive_name = frappe.db.get_value("Google Drive", {"enable": 1}, "name")
		
	if not g_drive_name:
		frappe.throw("Please authorize Google Drive access first. Search for 'Google Drive' in the search bar and create a new record for your user.")
		
	g_drive = frappe.get_doc("Google Drive", g_drive_name)
	credentials = g_drive.get_credentials()
	
	try:
		service = build("docs", "v1", credentials=credentials)
		title = f"{doc.topic or 'Untitled Session'} Notes"
		
		# Create empty document
		document = service.documents().create(body={"title": title}).execute()
		document_id = document.get("documentId")
		
		# Pre-draft document content
		date_str = frappe.utils.formatdate(doc.session_date)
		topic_str = doc.topic or "Untitled Session"
		
		attendees = []
		if doc.mentor:
			attendees.append(f"{doc.mentor} (Mentor)")
		for row in (doc.invited_fellows or []):
			if row.fellow_name:
				attendees.append(row.fellow_name)
		attendees_str = ", ".join(attendees)
		
		header_text = f"{date_str} | {topic_str}\nAttendees: {attendees_str}\n\n"
		notes_heading = "Notes\n"
		notes_body = "• \n• \n\n"
		action_heading = "Action items\n"
		action_body = "[ ] \n[ ] \n"
		
		full_text = header_text + notes_heading + notes_body + action_heading + action_body
		
		# Calculate indices for bold formatting
		idx_start = 1
		notes_start = idx_start + len(header_text)
		notes_end = notes_start + len(notes_heading)
		
		action_start = notes_end + len(notes_body)
		action_end = action_start + len(action_heading)
		
		requests = [
			{
				"insertText": {
					"location": {"index": 1},
					"text": full_text
				}
			},
			{
				"updateTextStyle": {
					"range": {
						"startIndex": notes_start,
						"endIndex": notes_end
					},
					"textStyle": {"bold": True},
					"fields": "bold"
				}
			},
			{
				"updateTextStyle": {
					"range": {
						"startIndex": action_start,
						"endIndex": action_end
					},
					"textStyle": {"bold": True},
					"fields": "bold"
				}
			},
			{
				"updateTextStyle": {
					"range": {
						"startIndex": 1,
						"endIndex": 1 + len(f"{date_str} | {topic_str}")
					},
					"textStyle": {"bold": True},
					"fields": "bold"
				}
			}
		]
		
		try:
			service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
		except Exception as format_err:
			frappe.log_error("Google Docs Formatting Failed", str(format_err))
			# We swallow this error so the document is still linked even if formatting fails
		
		url = f"https://docs.google.com/document/d/{document_id}/edit"
		
		doc.db_set("meeting_notes", url)
		frappe.db.commit()
		return {"status": "success", "url": url}
	except Exception as e:
		frappe.log_error("Google Docs Creation Failed", str(e))
		
		error_msg = str(e)
		if "Google Docs API has not been used" in error_msg or "disabled" in error_msg:
			frappe.throw("The **Google Docs API** is not enabled in your Google Cloud Project. Please click [here](https://console.developers.google.com/apis/api/docs.googleapis.com) to enable it, then try again.")
		else:
			frappe.throw("Failed to create Google Doc. Please check your Google Drive authorization and try again.")

