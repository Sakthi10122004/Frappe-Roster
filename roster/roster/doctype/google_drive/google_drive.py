import frappe
from frappe.model.document import Document
from frappe.utils import get_request_site_address
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import json

class GoogleDrive(Document):
    def get_flow(self):
        google_settings = frappe.get_single("Google Settings")
        if not google_settings.enable or not google_settings.client_id or not google_settings.client_secret:
            frappe.throw("Please configure Google Settings (Client ID and Secret) first.")
            
        client_config = {
            "web": {
                "client_id": google_settings.client_id,
                "project_id": "roster",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": google_settings.get_password("client_secret", raise_exception=False)
            }
        }
        
        scopes = ["https://www.googleapis.com/auth/drive.file"]
        
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri=get_request_site_address(True) + "/api/method/roster.roster.doctype.google_drive.google_drive.oauth_callback"
        )
        return flow
        
    def get_credentials(self):
        google_settings = frappe.get_single("Google Settings")
        refresh_token = self.get_password("refresh_token", raise_exception=False)
        
        if not refresh_token:
            frappe.throw("No refresh token found. Please authorize Google Drive.")
            
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=google_settings.client_id,
            client_secret=google_settings.get_password("client_secret", raise_exception=False)
        )
        return credentials

@frappe.whitelist()
def authorize_access(g_drive):
    doc = frappe.get_doc("Google Drive", g_drive)
    flow = doc.get_flow()
    
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    
    frappe.cache().set_value(f"google_drive_state_{state}", g_drive, expires_in_sec=600)
    
    return {"url": auth_url}

@frappe.whitelist(methods=["GET"])
def oauth_callback(state, code=None, error=None):
    if error:
        frappe.throw(f"Google OAuth Error: {error}")
        
    g_drive_name = frappe.cache().get_value(f"google_drive_state_{state}")
    if not g_drive_name:
        frappe.throw("Invalid or expired state token.")
        
    doc = frappe.get_doc("Google Drive", g_drive_name)
    flow = doc.get_flow()
    
    import os
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    if credentials.refresh_token:
        doc.db_set("refresh_token", credentials.refresh_token)
        frappe.db.commit()
    else:
        # Sometimes Google doesn't send a refresh token if already authorized
        if not doc.get_password("refresh_token", raise_exception=False):
            frappe.throw("No refresh token received. You may need to revoke access in your Google Account and try again.")
    
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = f"/app/google-drive/{g_drive_name}"
