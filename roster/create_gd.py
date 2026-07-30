import frappe
def run():
    if not frappe.db.exists("DocType", "Google Drive"):
        doc = frappe.new_doc("DocType")
        doc.name = "Google Drive"
        doc.module = "Roster"
        doc.custom = 0
        doc.istable = 0
        doc.issingle = 0
        
        doc.append("fields", {"fieldname": "enable", "fieldtype": "Check", "label": "Enable", "default": "0"})
        doc.append("fields", {"fieldname": "user", "fieldtype": "Link", "options": "User", "label": "User", "unique": 1})
        doc.append("fields", {"fieldname": "authorization_code", "fieldtype": "Password", "label": "Authorization Code"})
        doc.append("fields", {"fieldname": "refresh_token", "fieldtype": "Password", "label": "Refresh Token", "read_only": 1})
        doc.append("fields", {"fieldname": "cb", "fieldtype": "HTML", "label": "Authorize", "options": "<button class=\"btn btn-primary btn-sm\" onclick=\"frappe.call({\n\t\t\t\tmethod: 'roster.roster.doctype.google_drive.google_drive.authorize_access',\n\t\t\t\targs: { g_drive: cur_frm.doc.name },\n\t\t\t\tcallback: function(r) {\n\t\t\t\t\tif (!r.exc) {\n\t\t\t\t\t\tfrm.save();\n\t\t\t\t\t\twindow.open(r.message.url);\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t});\">Authorize Google Drive Access</button>"})
        
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Google Drive Doctype")
