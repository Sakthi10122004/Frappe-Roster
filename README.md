## Roster

Roster is a comprehensive Frappe application designed to manage Lecture Sessions, coordinate Mentors and Fellows, and seamlessly integrate with Google Calendar and Google Docs.

### Key Features
- **Lecture Session Management:** Schedule, track, and manage lecture sessions in a structured way.
- **Roles:** Separate tracking for Mentors and Fellows (Attendees).
- **Automated Emails:** Automatically dispatches tailored emails to participants when a session is scheduled, updated, or cancelled, as well as sending out post-session feedback forms and deliverables.
- **Google Calendar Integration:** Automatically syncs scheduled lecture sessions directly to Google Calendar, fetching the Google Meet links instantly.
- **Google Docs Integration:** One-click automated Google Doc generation for capturing session notes.

---

### Configuration & Setup

After installing the Roster app on your site, you must complete the following configuration steps for the automations to work correctly:

#### 1. Setup Email Templates
The system relies on predefined email templates to communicate with Mentors and Fellows. 
- Go to the core **Email Template** doctype and create three distinct templates:
  1. **Invite Template:** Used for calendar invites. *(e.g., "Lecture Session Invite")*
  2. **Feedback Template:** Used for collecting post-session feedback. *(e.g., "Lecture Session Feedback")*
  3. **Deliverable Template:** Used for sending out post-session deliverables. *(e.g., "Lecture Session Deliverables")*
- You can use Jinja templating within these templates to dynamically reference session details (e.g., `{{ doc.topic }}`, `{{ doc.session_date }}`).

#### 2. Configure Session Manager Settings
Once your templates are created, map them in the global settings:
- Search for **Session Manager Settings** in the global search bar.
- Select the respective default templates you created for Invites, Feedback, and Deliverables.
- Check the box to enable Background Jobs if you wish to run emails and syncs asynchronously.

#### 3. Google OAuth Configuration (Calendar & Meet)
To allow the app to schedule events and generate Google Meet links:
- Go to the Google Cloud Console and create an OAuth 2.0 Client ID for a Web Application.
- Ensure the **Google Calendar API** and **Google Drive API** are enabled in your Google Cloud Project.
- Set the Authorized Redirect URI to your Frappe site URL (e.g., `https://yoursite.com/api/method/frappe.integrations.doctype.google_settings.google_settings.google_oauth_fallback`).
- In Frappe, go to **Google Settings** and enter your Client ID and Client Secret. Ensure it is marked as "Enabled".
- *Note: Frappe's core `Event` syncing mechanism handles the Calendar integration.*

#### 4. Google Drive Authorization (For Meeting Notes)
To allow the app to automatically generate Google Docs for meeting notes, each user must individually authorize their Google Drive account:
- Search for the **Google Drive List** doctype.
- Create a new record, select your Frappe User, and click **Save**.
- After saving, click the **Authorize Google Drive Access** button.
- Log into Google and grant the requested permissions. Your refresh token will be securely saved to the database.

---

### Usage

1. Create **Mentors** and **Fellows** in their respective doctypes.
2. Create a new **Lecture Session**, assign a Mentor, and add invited Fellows.
3. Once the form is saved, click **Send Calendar Invite** to formally schedule the session, dispatch emails, and generate the Google Calendar event (complete with a Meet link).
4. From the Lecture Session calendar view, click on any scheduled session to view details and use the **Auto-create notes** button to automatically generate a fresh Google Doc for the session.

### License

mit
