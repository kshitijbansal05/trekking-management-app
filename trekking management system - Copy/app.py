import os
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import Config
from models import db, User, Trek, Booking
from forms import (
    LoginForm, UserRegisterForm, StaffRegisterForm,
    TrekForm, ProfileForm, StaffTrekUpdateForm
)
from seed import seed_admin

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()
    seed_admin()


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.role not in roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("index"))
            if current_user.is_blacklisted or not current_user.is_active_account:
                logout_user()
                flash("Your account is inactive or blacklisted.", "danger")
                return redirect(url_for("login"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/")
def index():
    open_treks = Trek.query.filter_by(status="Open").order_by(Trek.start_date.asc()).limit(6).all()
    return render_template("index.html", open_treks=open_treks)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect_dashboard()

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and user.password_hash:
            if not user.can_login():
                if user.role == "staff" and not user.is_approved:
                    flash("Staff registration pending admin approval.", "warning")
                else:
                    flash("Your account is inactive or blacklisted.", "danger")
                return redirect(url_for("login"))

            login_user(user)
            flash("Login successful.", "success")
            return redirect_dashboard()

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/register/user", methods=["GET", "POST"])
def register_user():
    if current_user.is_authenticated:
        return redirect_dashboard()

    form = UserRegisterForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            password_hash=form.password.data,
            role="user",
            is_approved=True
        )
        db.session.add(user)
        db.session.commit()
        flash("User registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register_user.html", form=form)


@app.route("/register/staff", methods=["GET", "POST"])
def register_staff():
    if current_user.is_authenticated:
        return redirect_dashboard()

    form = StaffRegisterForm()
    if form.validate_on_submit():
        staff = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            password_hash=form.password.data,
            role="staff",
            is_approved=False
        )
        db.session.add(staff)
        db.session.commit()
        flash("Staff registration submitted. Wait for admin approval.", "success")
        return redirect(url_for("login"))
    return render_template("register_staff.html", form=form)


def redirect_dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif current_user.role == "staff":
        return redirect(url_for("staff_dashboard"))
    return redirect(url_for("user_dashboard"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip()
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", form=form)


# ---------------- ADMIN ---------------- #

@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role="user").count()
    total_staff = User.query.filter_by(role="staff").count()
    total_bookings = Booking.query.count()

    pending_staff = User.query.filter_by(role="staff", is_approved=False).all()
    recent_treks = Trek.query.order_by(Trek.created_at.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        pending_staff=pending_staff,
        recent_treks=recent_treks
    )


@app.route("/admin/treks")
@login_required
@role_required("admin")
def admin_treks():
    treks = Trek.query.order_by(Trek.start_date.asc()).all()
    staff_list = User.query.filter_by(role="staff", is_approved=True, is_blacklisted=False).all()
    return render_template("admin/trek_list.html", treks=treks, staff_list=staff_list)


@app.route("/admin/treks/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_trek():
    form = TrekForm()
    if form.validate_on_submit():
        trek = Trek(
            name=form.name.data.strip(),
            location=form.location.data.strip(),
            difficulty=form.difficulty.data,
            duration_days=form.duration_days.data,
            total_slots=form.total_slots.data,
            available_slots=form.total_slots.data,
            status=form.status.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data.strip() if form.description.data else ""
        )
        db.session.add(trek)
        db.session.commit()
        flash("Trek created successfully.", "success")
        return redirect(url_for("admin_treks"))
    return render_template("admin/trek_form.html", form=form, title="Create Trek")


@app.route("/admin/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    form = TrekForm(obj=trek)

    if form.validate_on_submit():
        active_bookings = trek.booked_count()
        if form.total_slots.data < active_bookings:
            flash(f"Total slots cannot be less than current booked users ({active_bookings}).", "danger")
            return render_template("admin/trek_form.html", form=form, title="Edit Trek")

        trek.name = form.name.data.strip()
        trek.location = form.location.data.strip()
        trek.difficulty = form.difficulty.data
        trek.duration_days = form.duration_days.data
        trek.total_slots = form.total_slots.data
        trek.status = form.status.data
        trek.start_date = form.start_date.data
        trek.end_date = form.end_date.data
        trek.description = form.description.data.strip() if form.description.data else ""
        trek.refresh_available_slots()

        db.session.commit()
        flash("Trek updated successfully.", "success")
        return redirect(url_for("admin_treks"))

    return render_template("admin/trek_form.html", form=form, title="Edit Trek")


@app.route("/admin/treks/<int:trek_id>/delete")
@login_required
@role_required("admin")
def delete_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    db.session.delete(trek)
    db.session.commit()
    flash("Trek deleted successfully.", "info")
    return redirect(url_for("admin_treks"))


@app.route("/admin/treks/<int:trek_id>/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_staff(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    staff_id = request.form.get("staff_id")

    if staff_id:
        staff = User.query.filter_by(id=staff_id, role="staff", is_approved=True, is_blacklisted=False).first()
        if staff:
            trek.assigned_staff_id = staff.id
            db.session.commit()
            flash("Staff assigned successfully.", "success")
        else:
            flash("Invalid staff selection.", "danger")
    return redirect(url_for("admin_treks"))


@app.route("/admin/staff")
@login_required
@role_required("admin")
def admin_staff():
    staff_members = User.query.filter_by(role="staff").order_by(User.created_at.desc()).all()
    return render_template("admin/staff.html", staff_members=staff_members)


@app.route("/admin/staff/<int:user_id>/approve")
@login_required
@role_required("admin")
def approve_staff(user_id):
    staff = User.query.filter_by(id=user_id, role="staff").first_or_404()
    staff.is_approved = True
    db.session.commit()
    flash("Staff approved successfully.", "success")
    return redirect(url_for("admin_staff"))


@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():
    users = User.query.filter(User.role.in_(["user", "staff"])).order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/user/<int:user_id>/toggle_blacklist")
@login_required
@role_required("admin")
def toggle_blacklist(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Admin cannot be blacklisted.", "danger")
        return redirect(url_for("admin_users"))

    user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    flash("Blacklist status updated.", "info")
    return redirect(request.referrer or url_for("admin_users"))


@app.route("/admin/bookings")
@login_required
@role_required("admin")
def admin_bookings():
    bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings)


@app.route("/admin/search")
@login_required
@role_required("admin")
def admin_search():
    q = request.args.get("q", "").strip()
    users = []
    staff = []
    treks = []

    if q:
        users = User.query.filter(
            User.role == "user",
            ((User.full_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")) | (User.id == q if q.isdigit() else False))
        ).all()

        staff = User.query.filter(
            User.role == "staff",
            ((User.full_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")) | (User.id == q if q.isdigit() else False))
        ).all()

        treks = Trek.query.filter(
            (Trek.name.ilike(f"%{q}%")) | (Trek.location.ilike(f"%{q}%")) | (Trek.id == q if q.isdigit() else False)
        ).all()

    return render_template("admin/search.html", q=q, users=users, staff=staff, treks=treks)


# ---------------- STAFF ---------------- #

@app.route("/staff/dashboard")
@login_required
@role_required("staff")
def staff_dashboard():
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).order_by(Trek.start_date.asc()).all()
    return render_template("staff/dashboard.html", assigned_treks=assigned_treks)


@app.route("/staff/treks")
@login_required
@role_required("staff")
def staff_treks():
    treks = Trek.query.filter_by(assigned_staff_id=current_user.id).order_by(Trek.start_date.asc()).all()
    return render_template("staff/assigned_treks.html", treks=treks)


@app.route("/staff/trek/<int:trek_id>/manage", methods=["GET", "POST"])
@login_required
@role_required("staff")
def manage_trek(trek_id):
    trek = Trek.query.filter_by(id=trek_id, assigned_staff_id=current_user.id).first_or_404()
    form = StaffTrekUpdateForm()

    if request.method == "GET":
        form.available_slots.data = trek.available_slots
        if trek.status in ["Open", "Closed", "Completed"]:
            form.status.data = trek.status
        else:
            form.status.data = "Closed"

    if form.validate_on_submit():
        booked_users = trek.booked_count()
        minimum_available = 0
        maximum_available = trek.total_slots - booked_users

        if form.available_slots.data < minimum_available or form.available_slots.data > maximum_available:
            flash(f"Available slots must be between {minimum_available} and {maximum_available}.", "danger")
            return render_template("staff/trek_manage.html", trek=trek, form=form)

        trek.available_slots = form.available_slots.data
        trek.total_slots = booked_users + form.available_slots.data
        trek.status = form.status.data
        db.session.commit()
        flash("Trek updated successfully.", "success")
        return redirect(url_for("staff_treks"))

    return render_template("staff/trek_manage.html", trek=trek, form=form)


@app.route("/staff/trek/<int:trek_id>/participants")
@login_required
@role_required("staff")
def participants(trek_id):
    trek = Trek.query.filter_by(id=trek_id, assigned_staff_id=current_user.id).first_or_404()
    bookings = Booking.query.filter_by(trek_id=trek.id).order_by(Booking.booking_date.desc()).all()
    return render_template("staff/participants.html", trek=trek, bookings=bookings)


@app.route("/staff/booking/<int:booking_id>/complete")
@login_required
@role_required("staff")
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.trek.assigned_staff_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("staff_dashboard"))

    booking.status = "Completed"
    db.session.commit()
    flash("Participant marked as completed.", "success")
    return redirect(url_for("participants", trek_id=booking.trek_id))


# ---------------- USER ---------------- #

@app.route("/user/dashboard")
@login_required
@role_required("user")
def user_dashboard():
    treks = Trek.query.filter_by(status="Open").order_by(Trek.start_date.asc()).all()
    my_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template("user/dashboard.html", treks=treks, my_bookings=my_bookings)


@app.route("/user/treks")
@login_required
@role_required("user")
def user_treks():
    difficulty = request.args.get("difficulty", "").strip()
    location = request.args.get("location", "").strip()

    query = Trek.query.filter_by(status="Open")

    if difficulty:
        query = query.filter(Trek.difficulty == difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f"%{location}%"))

    treks = query.order_by(Trek.start_date.asc()).all()
    return render_template("user/treks.html", treks=treks, difficulty=difficulty, location=location)


@app.route("/user/book/<int:trek_id>")
@login_required
@role_required("user")
def book_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.status != "Open":
        flash("This trek is not open for booking.", "danger")
        return redirect(url_for("user_treks"))

    existing = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id).first()
    if existing:
        flash("You have already booked this trek.", "warning")
        return redirect(url_for("user_treks"))

    trek.refresh_available_slots()
    if trek.available_slots <= 0:
        trek.status = "Closed"
        db.session.commit()
        flash("No slots available. Booking closed.", "danger")
        return redirect(url_for("user_treks"))

    booking = Booking(
        user_id=current_user.id,
        trek_id=trek.id,
        status="Booked"
    )
    db.session.add(booking)
    db.session.flush()

    trek.refresh_available_slots()
    if trek.available_slots == 0:
        trek.status = "Closed"

    db.session.commit()
    flash("Trek booked successfully.", "success")
    return redirect(url_for("my_bookings"))


@app.route("/user/bookings")
@login_required
@role_required("user")
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template("user/my_bookings.html", bookings=bookings)


@app.route("/user/history")
@login_required
@role_required("user")
def history():
    bookings = Booking.query.filter_by(user_id=current_user.id).filter(
        Booking.status.in_(["Completed", "Cancelled", "Booked"])
    ).order_by(Booking.booking_date.desc()).all()
    return render_template("user/history.html", bookings=bookings)


@app.route("/user/booking/<int:booking_id>/cancel")
@login_required
@role_required("user")
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()

    if booking.status != "Booked":
        flash("Only active bookings can be cancelled.", "warning")
        return redirect(url_for("my_bookings"))

    booking.status = "Cancelled"
    booking.trek.refresh_available_slots()
    if booking.trek.status == "Closed" and booking.trek.available_slots > 0:
        booking.trek.status = "Open"

    db.session.commit()
    flash("Booking cancelled successfully.", "info")
    return redirect(url_for("my_bookings"))


if __name__ == "__main__":
    app.run(debug=True)
