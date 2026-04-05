# TODO

## Sibling

- Confer with sibling about design feedback after showing prototype
- Decide: payment policy for late cancellations (after lesson confirmed)
- Decide: reminder email timing default (currently 1 day before)
- Decide: should a parent be able to sign up two students in one form?
- Decide: should clients be emailed when teacher edits a slot?

## Must-haves before beta

- Password change UI — no way for teacher/superuser to change their own password from within the app
- Custom error pages — 403, 404, 500 currently show Flask's plain defaults
- Review email copy with sibling — confirmation, reminder, and auto-close emails
- End-to-end test the full flow — signup → confirmation → cancellation → reminder — with sibling playing teacher
- Test the .ics invite in a real calendar app (Google Calendar, Apple Calendar)
- Clear seed/test data before go-live

## Sibling local setup (non-programmer QOL)

- Make it easy for sibling to run the app locally and make simple tweaks (e.g. email copy)
- Review README for clarity — assume no programming background
- Consider project structure changes that make customizable content (email copy, settings) easy to find and edit without touching app logic

## Nice to have before beta

- Expand test coverage — unit tests for scheduling logic, integration tests for the full booking flow
- Migrate from legacy `Query.get()` to `Session.get()` for SQLAlchemy 2.0 compatibility

- Security headers (X-Frame-Options, Content-Security-Policy etc.)
- Replace PAT embedded in .git/config remote URL with SSH auth

## Hosting (when ready)

- Get a VPS — Hetzner or DigitalOcean, ~$5-6/month, Ubuntu LTS
- Point a domain at it — buy domain if needed, add A record, Caddy handles HTTPS automatically
- Server setup — install Python, clone repo, create .env with production values (fresh SECRET_KEY, SMTP creds)
- WSGI server — swap Flask dev server for Gunicorn (pip install gunicorn), don't use run.py in production
- Caddy — install Caddy, write two-line config pointing domain at Gunicorn
- systemd service — unit file that starts Gunicorn on boot and restarts on crash
- Backups — daily cron job copying instance/scheduler.db off-server (Backblaze B2)
