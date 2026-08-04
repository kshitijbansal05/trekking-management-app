from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError
from models import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class UserRegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register as User")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Email already registered.")


class StaffRegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register as Staff")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Email already registered.")


class TrekForm(FlaskForm):
    name = StringField("Trek Name", validators=[DataRequired(), Length(max=150)])
    location = StringField("Location", validators=[DataRequired(), Length(max=150)])
    difficulty = SelectField("Difficulty", choices=[("Easy", "Easy"), ("Moderate", "Moderate"), ("Hard", "Hard")], validators=[DataRequired()])
    duration_days = IntegerField("Duration (Days)", validators=[DataRequired(), NumberRange(min=1)])
    total_slots = IntegerField("Total Slots", validators=[DataRequired(), NumberRange(min=1)])
    status = SelectField("Status", choices=[
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Open", "Open"),
        ("Closed", "Closed"),
        ("Completed", "Completed")
    ], validators=[DataRequired()])
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    description = TextAreaField("Description")
    submit = SubmitField("Save Trek")

    def validate_end_date(self, field):
        if self.start_date.data and field.data < self.start_date.data:
            raise ValidationError("End date cannot be before start date.")


class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone", validators=[Length(max=20)])
    submit = SubmitField("Update Profile")


class StaffTrekUpdateForm(FlaskForm):
    available_slots = IntegerField("Available Slots", validators=[DataRequired(), NumberRange(min=0)])
    status = SelectField("Status", choices=[
        ("Open", "Open"),
        ("Closed", "Closed"),
        ("Completed", "Completed")
    ], validators=[DataRequired()])
    submit = SubmitField("Update Trek")
