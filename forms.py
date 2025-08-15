# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


# File Upload Form
class ResumeUploadForm(FlaskForm):
    resume = FileField('Upload Resume (PDF)', validators=[DataRequired()])
    submit = SubmitField('Analyze Resume')

# Cover Letter Form
class CoverLetterForm(FlaskForm):
    job_description = TextAreaField(
        'Job Description',
        validators=[DataRequired()],
        render_kw={"rows": 8, "placeholder": "Paste the job description here..."}
    )
    submit = SubmitField('Generate Cover Letter')

# Interview Prep Form
class InterviewPrepForm(FlaskForm):
    job_role = StringField(
        'Target Job Role',
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Data Analyst, Software Engineer"}
    )
    submit = SubmitField('Generate Questions')

class CoverLetterForm(FlaskForm):
    job_title = StringField(
        'Job Title',
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Software Engineer"}
    )
    job_description = TextAreaField(
        'Job Description',
        validators=[DataRequired()],
        render_kw={"rows": 6, "placeholder": "Paste the full job description..."}
    )
    company_info = TextAreaField(
        'About Company (Optional)',
        render_kw={"rows": 4, "placeholder": "e.g., A tech startup focused on AI tools"}
    )
    submit = SubmitField('Generate Cover Letter')