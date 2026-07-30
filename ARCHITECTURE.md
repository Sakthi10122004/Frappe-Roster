# Roster App Architecture & Data Flow

This document outlines the system architecture, core doctypes, data flow, and primary use cases for the **Roster** Frappe application.

## 1. System Architecture

Roster extends the Frappe framework to act as a centralized Session Management system. It leverages Frappe's built-in `Event` doctype for Google Calendar synchronization while maintaining its own domain-specific entities (`Lecture Session`, `Mentor`, `Fellow`).

### Core Integrations
* **Google Calendar API:** Synced implicitly via Frappe's native `Event` doctype.
* **Google Docs API:** Managed via a custom OAuth 2.0 flow natively implemented in the `Google Drive` doctype.

---

## 2. Core Doctypes & Fields

### 2.1 Master Data Doctypes

#### Mentor
* **Use Case:** Stores profiles of instructors leading the sessions.
* **Key Fields:**
  * `mentor_name` (Data): Full name of the mentor.
  * `email` (Data): Contact email (used for calendar invites).
  * `phone` (Data): Contact number.
  * `organization` (Data): Affiliation.
  * `status` (Select: Active/Inactive).

#### Fellow
* **Use Case:** Stores profiles of students/attendees participating in the sessions.
* **Key Fields:**
  * `fellow_name` (Data): Full name of the fellow.
  * `email` (Data): Contact email (used for calendar invites and feedback forms).
  * `status` (Select: Active/Inactive).

### 2.2 Transactional Doctypes

#### Lecture Session
* **Use Case:** The core entity for scheduling and managing a lecture.
* **Key Fields:**
  * `topic` (Data): Title of the session.
  * `mentor` (Link -> Mentor): The assigned mentor.
  * `session_date` (Date): Date of the session.
  * `start_time` / `end_time` (Time): Time bounds.
  * `invited_fellows` (Table -> Invited Fellow): List of attendees.
  * `workflow_state` (Select): Tracks lifecycle (Draft, Scheduled, Completed, Cancelled, etc.).
  * `event_id` (Link -> Event): Reference to the underlying Frappe Event.
  * `meet_link` (Data): Extracted Google Meet URL.
  * `meeting_notes` (Data): URL to the dynamically generated Google Doc.
  * `deliverable` (Attach): Any post-session file to send to participants.

#### Session Feedback
* **Use Case:** Captures post-session reviews from Fellows.
* **Key Fields:**
  * `session` (Link -> Lecture Session): The session being reviewed.
  * `fellow` (Link -> Fellow): The person submitting the feedback.
  * `rating` (Rating): 1-5 scale rating.
  * `feedback` (Small Text): Written review.

### 2.3 Configuration & Integration Doctypes

#### Session Manager Settings (Single)
* **Use Case:** Global app configuration for automated background jobs and emails.
* **Key Fields:**
  * `enable_background_jobs` (Check): Toggles async email/sync processing.
  * `invite_email_template` (Link -> Email Template): Used when scheduling.
  * `feedback_email_template` (Link -> Email Template): Used post-session.
  * `deliverable_email_template` (Link -> Email Template): Used to distribute files post-session.

#### Google Drive
* **Use Case:** Stores per-user OAuth 2.0 refresh tokens required to generate Google Docs dynamically.
* **Key Fields:**
  * `user` (Link -> User): The Frappe user owning the integration.
  * `enable` (Check): Toggle integration.
  * `refresh_token` (Password): Securely stored OAuth token.

---

## 3. Data Flow & Workflows

### 3.1 Scheduling & Calendar Sync Flow
1. **Creation:** A user creates a `Lecture Session` in **Draft** state.
2. **Assignment:** A Mentor is linked, and active Fellows are fetched into the `invited_fellows` child table.
3. **Trigger:** The user clicks "Send Calendar Invite".
4. **Backend Processing:**
   * The Python controller creates a native Frappe `Event` document linking all participant emails.
   * Frappe's core sync mechanism pushes the `Event` to Google Calendar.
   * Google Calendar generates a Meet Link and returns it to the `Event`.
   * The `Lecture Session` automatically pulls the `meet_link` and `google_calendar_id`.
5. **Notification:** The backend utilizes the `invite_email_template` to dispatch personalized emails to all participants.
6. **State Change:** The session transitions to **Scheduled**.

### 3.2 Dynamic Google Doc Generation Flow
1. **Trigger:** The user opens the Frappe Calendar View, clicks on a scheduled session, and selects "Auto-create notes".
2. **Authentication Check:** The backend queries the `Google Drive` doctype for the active user's (or Administrator's) `refresh_token`.
3. **API Call:** A payload is sent to the Google Docs API (`https://docs.googleapis.com/v1/documents`) to generate a blank document titled after the session `topic`.
4. **Storage:** The returned document URL is saved directly into the `meeting_notes` field of the `Lecture Session`.

### 3.3 Post-Session Completion Flow
1. **Trigger:** The user uploads a `deliverable` file and changes the workflow state to **Completed**.
2. **Validation:** The Python `on_update` hook detects the state change.
3. **Deliverable Dispatch:** If a deliverable is attached, the system formats an email using the `deliverable_email_template` and dispatches it to all invited Fellows with the attachment linked.
4. **Feedback Dispatch:** The system formats an email using the `feedback_email_template`, dynamically embedding a link to a web form (or instructing them to fill out the `Session Feedback` doctype), and dispatches it to all attendees.
