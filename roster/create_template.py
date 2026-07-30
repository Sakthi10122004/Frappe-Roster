import frappe

def run():
    frappe.init(site="sakthi.com")
    frappe.connect()
    
    template_name = "Deliverables Template"
    if not frappe.db.exists("Email Template", template_name):
        doc = frappe.get_doc({
            "doctype": "Email Template",
            "name": template_name,
            "subject": "Deliverables for {{ doc.topic }}",
            "response": """<p>Hi {{ fellow.fellow_name }},</p>

<p>Thank you for attending the <strong>{{ doc.topic }}</strong> lecture session today!</p>

<p>As discussed, here are your deliverables from the session:</p>

<div style="padding: 15px; border-left: 4px solid #1a73e8; background-color: #f8f9fa; margin: 15px 0;">
{{ deliverable }}
</div>

{% if doc.meeting_notes %}
<p>You can access the meeting notes for this session here: <a href="{{ doc.meeting_notes }}">Meeting Notes Document</a></p>
{% endif %}

<p>Best regards,<br>
The Tech4Good Team</p>"""
        })
        doc.insert(ignore_permissions=True)
        print(f"Created template: {template_name}")
        
        # Link it to settings
        settings = frappe.get_single("Session Manager Settings")
        settings.deliverable_email_template = template_name
        settings.save(ignore_permissions=True)
        frappe.db.commit()
    else:
        print(f"Template {template_name} already exists.")
