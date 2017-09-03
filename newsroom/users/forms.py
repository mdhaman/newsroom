from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, BooleanField, TextAreaField
from wtforms import SelectField
from wtforms.validators import DataRequired, Email


class UserForm(FlaskForm):

    user_types = [('administrator', 'Administrator'),
                  ('public', 'Public'),
                  ('internal', 'Internal')]

    id = HiddenField('Id')
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Telephone', validators=[DataRequired()])
    user_type = SelectField('User Type', choices=user_types)
    company = SelectField('Company', coerce=str)
    signup_details = TextAreaField('Sign Up Details', validators=[])
    is_validated = BooleanField('Email Validated', validators=[])
    is_enabled = BooleanField('Account Enabled', validators=[])
    is_approved = BooleanField('Account Approved', validators=[])
