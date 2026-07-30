frappe.views.calendar["Lecture Session"] = {
	field_map: {
		start: "start",
		end: "end",
		id: "name",
		title: "topic",
		allDay: "allDay"
	},
	order_by: "session_date asc",
	get_events_method: "roster.roster.doctype.lecture_session.lecture_session.get_lecture_session_events",
	get_css_class: function (data) {
		// Color code by workflow_state
		var state = data.workflow_state;
		if (state === "Draft") return "default";
		if (state === "Scheduled") return "info";
		if (state === "Created") return "success";
		if (state === "Completed") return "success";
		if (state === "Cancelled") return "danger";
		if (state === "Rescheduled") return "warning";
		if (state === "Updated") return "info";
		if (state === "Failed") return "danger";
		return "default";
	},
	options: {
		editable: false,
		selectable: false,
		eventClick: function(info) {
			let session_id = info.event.id;
			frappe.db.get_doc("Lecture Session", session_id).then(doc => {
				let meet_html = '';
				if (doc.meet_link) {
					meet_html = `
						<div style="margin-top: 15px; display: flex; align-items: flex-start; gap: 15px;">
							<div style="width: 40px; display: flex; justify-content: center; padding-top: 5px;">
								<i class="fa fa-video-camera" style="color: #fbbc04; font-size: 18px;"></i>
							</div>
							<div style="flex-grow: 1;">
								<a href="${doc.meet_link}" target="_blank" style="color: #1a73e8; font-weight: 500; font-size: 14px; text-decoration: none; display: inline-block;">Join with Google Meet</a><br>
								<a href="${doc.meet_link}" target="_blank" style="font-size: 13px; color: #5f6368; text-decoration: none;">${doc.meet_link.replace('https://', '')}</a>
							</div>
							<div style="padding-top: 5px; color: #5f6368; cursor: pointer;">
								<i class="fa fa-clone"></i>
							</div>
						</div>
					`;
				}
				
				let take_notes_html = '';
				if (doc.meeting_notes) {
					take_notes_html = `
						<div style="margin-top: 15px; display: flex; align-items: flex-start; gap: 15px;">
							<div style="width: 40px; display: flex; justify-content: center; padding-top: 5px;">
								<i class="fa fa-file-text-o" style="color: #1a73e8; font-size: 18px;"></i>
							</div>
							<div style="flex-grow: 1;">
								<a href="${doc.meeting_notes}" target="_blank" style="color: #1a73e8; font-weight: 500; font-size: 14px; text-decoration: none; display: inline-block;">Open meeting notes</a><br>
								<div style="font-size: 13px; color: #5f6368;">View the attached notes document</div>
							</div>
						</div>
					`;
				} else {
					take_notes_html = `
						<div style="margin-top: 15px; display: flex; align-items: flex-start; gap: 15px;">
							<div style="width: 40px; display: flex; justify-content: center; padding-top: 5px;">
								<i class="fa fa-file-text-o" style="color: #5f6368; font-size: 18px;"></i>
							</div>
							<div style="flex-grow: 1;">
								<a href="#" onclick="create_meeting_notes('${session_id}'); return false;" style="color: #1a73e8; font-weight: 500; font-size: 14px; text-decoration: none; display: inline-block;">Auto-create notes</a><br>
								<div style="font-size: 13px; color: #5f6368;">Start a new document to capture notes</div>
							</div>
						</div>
					`;
				}
				
				let guests = doc.invited_fellows || [];
				let guests_html = `
					<div style="margin-top: 15px; display: flex; align-items: flex-start; gap: 15px;">
						<div style="width: 40px; display: flex; justify-content: center; padding-top: 5px;">
							<i class="fa fa-users" style="color: #5f6368; font-size: 18px;"></i>
						</div>
						<div style="flex-grow: 1;">
							<div style="font-size: 14px; color: #3c4043;">${guests.length + 1} guests</div>
							<div style="font-size: 13px; color: #5f6368; margin-top: 10px;">
								<ul style="list-style-type: none; padding: 0; margin: 0; line-height: 1.6;">
									<li style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
										<div style="width: 24px; height: 24px; border-radius: 50%; background: #9c27b0; color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">
											${doc.mentor ? doc.mentor.charAt(0).toUpperCase() : 'M'}
										</div>
										<span style="font-size: 14px; color: #3c4043;">${doc.mentor || 'Unknown'} (Mentor)</span>
									</li>
									${guests.map(g => `
										<li style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
											<div style="width: 24px; height: 24px; border-radius: 50%; border: 1px solid #dadce0; color: #5f6368; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">
												${g.fellow_name ? g.fellow_name.charAt(0).toUpperCase() : 'F'}
											</div>
											<span style="font-size: 14px; color: #3c4043;">${g.fellow_name}</span>
										</li>
									`).join('')}
								</ul>
							</div>
						</div>
					</div>
				`;

				let description_html = `
					<div style="margin-top: 15px; display: flex; align-items: flex-start; gap: 15px;">
						<div style="width: 40px; display: flex; justify-content: center; padding-top: 5px;">
							<i class="fa fa-align-left" style="color: #5f6368; font-size: 18px;"></i>
						</div>
						<div style="flex-grow: 1; font-size: 14px; color: #3c4043; line-height: 1.5;">
							<b>Topic:</b> ${doc.topic || '—'}<br>
							<b>Mentor:</b> ${doc.mentor || '—'}<br>
							<b>Date:</b> ${frappe.datetime.global_date_format(doc.session_date)}<br>
							<b>Time:</b> ${doc.start_time} – ${doc.end_time || 'TBD'}<br>
							${doc.meet_link ? `<b>Meet Link:</b> <a href="${doc.meet_link}" target="_blank">${doc.meet_link}</a><br>` : ''}
							<b>Invited Fellows:</b> ${guests.length}<br>
							${doc.notes ? `<br><b>Notes:</b><br>${doc.notes}` : ''}
						</div>
					</div>
				`;

				let footer_html = `
					<div style="margin-top: 15px; padding-top: 15px; display: flex; align-items: flex-start; gap: 15px;">
						<div style="width: 40px; display: flex; justify-content: center; padding-top: 2px;">
							<i class="fa fa-calendar" style="color: #5f6368; font-size: 16px;"></i>
						</div>
						<div style="flex-grow: 1; font-size: 13px; color: #3c4043;">
							<div>T4GC Roster</div>
							<div style="color: #5f6368;">Created by: ${doc.owner}</div>
						</div>
					</div>
				`;

				let d = new frappe.ui.Dialog({
					title: `<div style="display:flex; align-items:center; gap:10px;"><div style="width:14px; height:14px; border-radius:3px; background:#039be5;"></div>Lecture: ${doc.topic || ''}</div>`,
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'details',
							options: `
								<div style="padding: 0px 10px 10px 10px; font-family: 'Roboto', 'Inter', sans-serif;">
									<div style="font-size: 14px; color: #3c4043; margin-left: 55px; margin-bottom: 5px;">
										${frappe.datetime.global_date_format(doc.session_date)} ⋅ 
										${doc.start_time} – ${doc.end_time || ''}
									</div>
									${meet_html}
									${take_notes_html}
									${guests_html}
									${description_html}
									${footer_html}
								</div>
							`
						}
					],
					primary_action_label: __('Open Document'),
					primary_action: function() {
						d.hide();
						frappe.set_route('Form', 'Lecture Session', session_id);
					}
				});
				
				// Expose globally for onclick handler
				window.create_meeting_notes = function(event_name) {
					frappe.call({
						method: "roster.roster.doctype.lecture_session.lecture_session.create_meeting_notes",
						args: { session_name: event_name },
						freeze: true,
						freeze_message: "Creating Google Doc...",
						callback: function(r) {
							if(r.message && r.message.status === "success") {
								frappe.show_alert({message: "Notes document created successfully!", indicator: "green"});
								d.hide();
								// Re-trigger the click to open the dialog with the new link
								setTimeout(() => {
									frappe.views.calendar["Lecture Session"].options.eventClick(info);
								}, 500);
							}
						}
					});
				};

				d.show();
				
				// Make dialog match google calendar popover width
				d.$wrapper.find('.modal-dialog').css({'max-width': '450px', 'width': '100%'});
				// Hide standard title since we put a custom one in the html
				d.$wrapper.find('.modal-title').html(`<div style="display:flex; align-items:center; gap:10px;"><div style="width:14px; height:14px; border-radius:3px; background:#039be5;"></div>Lecture: ${doc.topic || ''}</div>`);
			});
		}
	}
};
