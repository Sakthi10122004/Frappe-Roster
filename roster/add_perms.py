import frappe

def run():
    frappe.init(site="sakthi.com")
    frappe.connect()
    
    doc = frappe.get_doc("DocType", "Google Drive")
    if not doc.permissions:
        doc.append("permissions", {
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Permissions added.")
    else:
        print("Permissions already exist.")
