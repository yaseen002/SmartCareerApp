# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    resumes = db.relationship('Resume', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Extracted resume text
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analysis_results = db.relationship('AnalysisResult', back_populates='resume', uselist=False)

    def __repr__(self):
        return f"<Resume {self.filename} for User {self.user_id}>"


class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ats_score = db.Column(db.Integer)
    key_skills = db.Column(db.Text)  # JSON string
    strengths = db.Column(db.Text)  # JSON string
    missing_sections = db.Column(db.Text)  # JSON string
    improvements = db.Column(db.Text)  # JSON string
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resume = db.relationship('Resume', back_populates='analysis_results')

    def __repr__(self):
        return f"<AnalysisResult for Resume {self.resume_id}>"
    
class CoverLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    company_info = db.Column(db.Text)  # Optional
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='cover_letters')
    resume = db.relationship('Resume', backref='cover_letters')

    def __repr__(self):
        return f"<CoverLetter for {self.job_title} by User {self.user_id}>"
    
class InterviewPrep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text)  # JSON: ["questions_with_answers", "focus_areas"]
    content = db.Column(db.Text, nullable=False)  # AI-generated content
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='interview_preps')
    resume = db.relationship('Resume', backref='interview_preps')

    def __repr__(self):
        return f"<InterviewPrep for {self.job_title} by User {self.user_id}>"