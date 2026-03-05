"""Flask-WTF form definitions with full validation."""
from __future__ import annotations
import re
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField,
    TextAreaField, FloatField, IntegerField, DateField, SubmitField, DecimalField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange,
    Optional, ValidationError, Regexp
)


# ─────────────────────────────────────────────────────────────────────────────
# Auth forms
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    email = StringField("Email", validators=[
        DataRequired(), Email(), Length(max=255)
    ])
    phone = StringField("Phone Number", validators=[
        Optional(), Length(max=20),
        Regexp(r"^\+?[\d\s\-]{7,20}$", message="Enter a valid phone number.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired(), Length(min=8, max=128)
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match.")
    ])
    submit = SubmitField("Create Account")

    def validate_password(self, field):
        pw = field.data
        if not re.search(r"[A-Z]", pw):
            raise ValidationError("Must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", pw):
            raise ValidationError("Must contain at least one lowercase letter.")
        if not re.search(r"\d", pw):
            raise ValidationError("Must contain at least one digit.")
        if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]", pw):
            raise ValidationError("Must contain at least one special character.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[
        DataRequired(), Email(), Length(max=255)
    ])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[
        DataRequired(), Length(min=8, max=128)
    ])
    confirm_password = PasswordField("Confirm New Password", validators=[
        DataRequired(), EqualTo("new_password", message="Passwords must match.")
    ])
    submit = SubmitField("Change Password")

    def validate_new_password(self, field):
        pw = field.data
        if not re.search(r"[A-Z]", pw):
            raise ValidationError("Must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", pw):
            raise ValidationError("Must contain at least one lowercase letter.")
        if not re.search(r"\d", pw):
            raise ValidationError("Must contain at least one digit.")
        if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]", pw):
            raise ValidationError("Must contain at least one special character.")


class ProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    phone = StringField("Phone Number", validators=[
        Optional(), Length(max=20),
        Regexp(r"^\+?[\d\s\-]{7,20}$", message="Enter a valid phone number.")
    ])
    submit = SubmitField("Update Profile")


# ─────────────────────────────────────────────────────────────────────────────
# Vehicle forms
# ─────────────────────────────────────────────────────────────────────────────

FUEL_TYPES = [("petrol", "Petrol"), ("diesel", "Diesel"),
              ("electric", "Electric"), ("hybrid", "Hybrid")]
TRANSMISSIONS = [("automatic", "Automatic"), ("manual", "Manual")]
VEHICLE_STATUSES = [("available", "Available"), ("maintenance", "Under Maintenance")]


class VehicleForm(FlaskForm):
    name = StringField("Vehicle Name", validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    model = StringField("Model / Year", validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    plate_number = StringField("Plate Number", validators=[
        DataRequired(), Length(min=3, max=20),
        Regexp(r"^[A-Za-z0-9\s\-]+$", message="Use letters, numbers, spaces or hyphens only.")
    ])
    price_per_day = DecimalField("Price per Day (KES)", places=2, validators=[
        DataRequired(), NumberRange(min=1, max=1_000_000)
    ])
    capacity = IntegerField("Seating Capacity", validators=[
        DataRequired(), NumberRange(min=1, max=100)
    ])
    fuel_type = SelectField("Fuel Type", choices=FUEL_TYPES, validators=[DataRequired()])
    transmission = SelectField("Transmission", choices=TRANSMISSIONS, validators=[DataRequired()])
    status = SelectField("Status", choices=VEHICLE_STATUSES, validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    image = FileField("Vehicle Image", validators=[
        Optional(),
        FileAllowed(["png", "jpg", "jpeg", "webp"], "Images only.")
    ])
    submit = SubmitField("Save Vehicle")


# ─────────────────────────────────────────────────────────────────────────────
# Booking forms
# ─────────────────────────────────────────────────────────────────────────────

class BookingForm(FlaskForm):
    start_date = DateField("Pick-up Date", validators=[DataRequired()])
    end_date = DateField("Return Date", validators=[DataRequired()])
    notes = TextAreaField("Additional Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Request Booking")

    def validate_end_date(self, field):
        if self.start_date.data and field.data:
            if field.data <= self.start_date.data:
                raise ValidationError("Return date must be after pick-up date.")


class BookingActionForm(FlaskForm):
    """Admin approve/reject booking."""
    action = SelectField("Action", choices=[
        ("approved", "Approve"),
        ("rejected", "Reject"),
    ], validators=[DataRequired()])
    admin_notes = TextAreaField("Admin Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Submit Decision")
