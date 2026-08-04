from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)

    role = db.Column(db.String(20), nullable=False)  # admin, staff, user
    is_approved = db.Column(db.Boolean, default=False)
    is_blacklisted = db.Column(db.Boolean, default=False)
    is_active_account = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff_treks = db.relationship("Trek", backref="assigned_staff", lazy=True, foreign_keys="Trek.assigned_staff_id")
    bookings = db.relationship("Booking", backref="user", lazy=True)

    def get_id(self):
        return str(self.id)

    def can_login(self):
        if self.is_blacklisted or not self.is_active_account:
            return False
        if self.role == "staff" and not self.is_approved:
            return False
        return True


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # Easy, Moderate, Hard
    duration_days = db.Column(db.Integer, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False) 

    status = db.Column(db.String(20), nullable=False, default="Pending")
    # Pending / Approved / Open / Closed / Completed

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)

    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="trek", lazy=True, cascade="all, delete-orphan")

    def booked_count(self):
        return Booking.query.filter_by(trek_id=self.id, status="Booked").count()

    def completed_count(self):
        return Booking.query.filter_by(trek_id=self.id, status="Completed").count()

    def refresh_available_slots(self):
        active_bookings = self.booked_count()
        self.available_slots = max(self.total_slots - active_bookings, 0)

    def is_bookable(self):
        return self.status == "Open" and self.available_slots > 0


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)

    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="Booked")
    # Booked / Cancelled / Completed

    notes = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "trek_id", name="unique_user_trek_booking"),
    )
