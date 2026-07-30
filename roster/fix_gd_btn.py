import frappe
def run():
    frappe.init(site="sakthi.com")
    frappe.connect()
    
    doc = frappe.get_doc("DocType", "Google Drive")
    for field in doc.fields:
        if field.fieldname == "cb":
            field.options = """<button class="btn btn-primary btn-sm" onclick="if(cur_frm.is_new()){frappe.msgprint('Please save the document first!');return;}frappe.call({method: 'roster.roster.doctype.google_drive.google_drive.authorize_access', args: { g_drive: cur_frm.doc.name }, callback: function(r) { if (!r.exc) { window.open(r.message.url); } } });">Authorize Google Drive Access</button>"""
            break
            
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Fixed button")
