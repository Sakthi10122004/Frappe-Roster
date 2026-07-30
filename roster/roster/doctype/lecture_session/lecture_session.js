// Copyright (c) 2026, Sakthi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Lecture Session", {
	setup(frm) {
		// Force 12-hour time format for both the input display AND the picker slider.
		// frappe.sys_defaults controls the input field formatting,
		// frappe.boot.sysdefaults controls the air-datepicker timepicker widget.
		frappe.sys_defaults.time_format = "hh:mm:ss A";
		if (frappe.boot.sysdefaults) {
			frappe.boot.sysdefaults.time_format = "hh:mm:ss A";
		}
	},
	refresh(frm) {
		// Add "Fetch All Fellows" button near the invited_fellows table
		frm.add_custom_button(__("Fetch All Fellows"), function () {
			frappe.call({
				method: "roster.roster.doctype.lecture_session.lecture_session.get_all_active_fellows",
				freeze: true,
				freeze_message: __("Fetching all fellows..."),
				callback: function (r) {
					if (r.message && r.message.length) {
						// Collect fellow names already in the table to avoid duplicates
						let existing = {};
						(frm.doc.invited_fellows || []).forEach(function (row) {
							if (row.fellow) {
								existing[row.fellow] = true;
							}
						});

						let added = 0;
						r.message.forEach(function (fellow) {
							if (!existing[fellow.name]) {
								let row = frm.add_child("invited_fellows");
								row.fellow = fellow.name;
								row.fellow_name = fellow.fellow_name;
								added++;
							}
						});

						frm.refresh_field("invited_fellows");

						if (added > 0) {
							frappe.show_alert({
								message: __("{0} fellow(s) added", [added]),
								indicator: "green",
							});
							frm.dirty();
						} else {
							frappe.show_alert({
								message: __("All fellows are already invited"),
								indicator: "blue",
							});
						}
					} else {
						frappe.show_alert({
							message: __("No active fellows found"),
							indicator: "orange",
						});
					}
				},
			});
		}, __("Actions"));

		// Automatically fetch meet link and google calendar ID if they are missing
		if (frm.doc.event_id && (!frm.doc.meet_link || !frm.doc.google_calendar_id)) {
			frappe.db.get_value("Event", frm.doc.event_id, ["google_meet_link", "google_calendar_event_id"], function(r) {
				let dirty = false;
				if (r && r.google_meet_link && !frm.doc.meet_link) {
					frm.set_value("meet_link", r.google_meet_link);
					dirty = true;
				}
				if (r && r.google_calendar_event_id && !frm.doc.google_calendar_id) {
					frm.set_value("google_calendar_id", r.google_calendar_event_id);
					dirty = true;
				}
				if (dirty) frm.save();
			});
		}

		// Show "Send Calendar Invite" button only when in Draft and form is saved
		if (frm.doc.workflow_state === "Draft" && !frm.is_new()) {
			frm.add_custom_button(
				__("Send Calendar Invite"),
				function () {
					if (!frm.doc.mentor) {
						frappe.msgprint(__("Please select a Mentor before scheduling."));
						return;
					}
					if (!frm.doc.session_date || !frm.doc.start_time) {
						frappe.msgprint(
							__("Please set the Session Date and Start Time before scheduling.")
						);
						return;
					}
					if (!(frm.doc.invited_fellows && frm.doc.invited_fellows.length)) {
						frappe.msgprint(__("Please add at least one Fellow before scheduling."));
						return;
					}

					frappe.confirm(
						__(
							"This will create a calendar event and send invite emails to the mentor and {0} fellow(s). Continue?",
							[frm.doc.invited_fellows.length]
						),
						function () {
							frm.set_value("workflow_state", "Scheduled");
							frm.save();
						}
					);
				},
				__("Actions")
			);

			// Make it the primary (blue) button
			frm.change_custom_button_type(
				__("Send Calendar Invite"),
				__("Actions"),
				"primary"
			);
		}
	},
});
