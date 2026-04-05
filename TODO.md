# TODO

## Sibling

1. Confer with sibling about design feedback after showing prototype
2. Decide: payment policy for late cancellations (after lesson confirmed)
3. Decide: reminder email timing default (currently 1 day before)
4. Decide: should a parent be able to sign up two students in one form?
5. Decide: should clients be emailed when teacher edits a slot?
6. Decide: when teacher manually closes a lesson, should clients with pending signups receive an automated cancellation email, or should the teacher contact them directly?
7. Review email copy with sibling — confirmation, reminder, and auto-close emails

## Meta

1. Migrate this TODO file to GitHub Issues for better tracking

## Must-haves before beta

1. Password change UI — no way for teacher/superuser to change their own password from within the app
2. Custom error pages — 403, 404, 500 currently show Flask's plain defaults
3. End-to-end test the full flow — signup → confirmation → cancellation → reminder — with sibling playing teacher
4. Test the .ics invite in a real calendar app (Google Calendar, Apple Calendar)

## Sibling local setup (non-programmer QOL)

1. Make it easy for sibling to run the app locally and make simple tweaks (e.g. email copy)
2. Review README for clarity — assume no programming background
3. Consider project structure changes that make customizable content (email copy, settings) easy to find and edit without touching app logic

## Nice to have before beta

1. Backups — daily cron job copying instance/scheduler.db off-server (e.g. Backblaze B2 via rclone)
2. Expand test coverage — unit tests for scheduling logic, integration tests for the full booking flow
3. Migrate from legacy `Query.get()` to `Session.get()` for SQLAlchemy 2.0 compatibility
4. Security headers (X-Frame-Options, Content-Security-Policy etc.)
5. Replace PAT embedded in .git/config remote URL with SSH auth

## Hosting (when ready)

1. Get a VPS — Hetzner or DigitalOcean, ~$5-6/month, Ubuntu LTS
2. Point a domain at it — buy domain if needed, add A record, Caddy handles HTTPS automatically
3. Server setup — install Python, clone repo, create .env with production values (fresh SECRET_KEY, SMTP creds)
4. WSGI server — swap Flask dev server for Gunicorn (pip install gunicorn), don't use run.py in production
5. Caddy — install Caddy, write two-line config pointing domain at Gunicorn
6. systemd service — unit file that starts Gunicorn on boot and restarts on crash
