from werkzeug.security import generate_password_hash
from models import db, User

def seed_admin():
    admin_email = "admin@trekapp.com"
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            full_name="Admin",
            email=admin_email,
            phone="9999999999",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            is_approved=True,
            is_blacklisted=False,
            is_active_account=True
        )
        db.session.add(admin)
        db.session.commit()
