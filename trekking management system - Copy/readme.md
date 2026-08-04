# Trekking Management Application

A Flask-based web application for managing treks, staff, and users.

## Features

- Admin, Staff, and User authentication
- Admin can create, edit, delete treks
- Admin can approve and blacklist staff/users
- Admin can assign staff to treks
- Staff can manage assigned treks only
- Users can browse, filter, and book open treks
- Overbooking prevention
- Booking history

## Tech Stack

- Flask
- Jinja2
- Bootstrap
- SQLite
- Flask-Login
- Flask-WTF

## Default Admin Credentials

- Email: admin@trekapp.com
- Password: admin123

## Run Locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
