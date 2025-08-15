from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os
import json
import re
from models import db, User, Resume, AnalysisResult, CoverLetter

# Step 1: Create the Flask app
app = Flask(__name__)
app.config.from_object('config.Config')  # Load config

# Step 2: Initialize CSRF and Login Manager
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."

# Step 3: Import db and models AFTER app is created
from models import db, User, Resume  # Resume added

# Step 4: Initialize the database with the app
db.init_app(app)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    from forms import RegistrationForm
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template('auth/register.html', form=form)

        user = User(email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    from forms import LoginForm
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            session.permanent = True
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash("Invalid email or password.", "error")

    return render_template('auth/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# ===========================
# Resume Analysis Routes
# ===========================
@app.route('/resume/analyze', methods=['GET', 'POST'])
@login_required
def resume_analysis():
    from forms import ResumeUploadForm
    from utils.pdf_parser import extract_text_from_pdf
    from utils.gemini_client import analyze_resume
    import os
    import re

    form = ResumeUploadForm()

    if request.method == 'POST':
        if not request.is_json and 'resume' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['resume']
        if not file or file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDFs allowed"}), 400

        upload_dir = os.path.join('uploads', str(current_user.id))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)

        try:
            raw_text = extract_text_from_pdf(file_path)
            ai_raw = analyze_resume(raw_text)

            # Parse AI JSON
            try:
                ai_data = json.loads(ai_raw)
            except json.JSONDecodeError:
                match = re.search(r'\{.*\}', ai_raw, re.DOTALL)
                if not match:
                    raise ValueError("No valid JSON in AI response")
                ai_data = json.loads(match.group())

            # Save to DB
            resume = Resume.query.filter_by(user_id=current_user.id).first()
            if resume:
                resume.filename = file.filename
                resume.content = raw_text
            else:
                resume = Resume(filename=file.filename, content=raw_text, user_id=current_user.id)
                db.session.add(resume)
            db.session.flush()

            analysis = AnalysisResult.query.filter_by(resume_id=resume.id).first()
            if not analysis:
                analysis = AnalysisResult(resume_id=resume.id)
                db.session.add(analysis)

            analysis.ats_score = ai_data.get("ats_score")
            analysis.key_skills = json.dumps(ai_data.get("key_skills", []))
            analysis.strengths = json.dumps(ai_data.get("strengths", []))
            analysis.missing_sections = json.dumps(ai_data.get("missing_sections", []))
            analysis.improvements = json.dumps(ai_data.get("improvements", []))

            db.session.commit()

            # ✅ Always return JSON for AJAX
            return jsonify({"success": True}), 200

        except Exception as e:
            db.session.rollback()
            print("Error:", str(e))  # Log to console
            return jsonify({"error": str(e)}), 500

    # Handle GET request
    existing_resume = Resume.query.filter_by(user_id=current_user.id).first()
    return render_template('resume_analysis.html', form=form, has_resume=existing_resume is not None)


@app.route('/analysis/view')
@login_required
def view_analysis():
    from models import Resume, AnalysisResult
    import json

    # Get the latest resume and its analysis
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        flash("No resume found.", "error")
        return redirect(url_for('resume_analysis'))

    analysis = AnalysisResult.query.filter_by(resume_id=resume.id).first()
    if not analysis:
        flash("No analysis available for this resume.", "error")
        return redirect(url_for('resume_analysis'))

    # Convert DB fields back to Python lists
    feedback = {
        "ats_score": analysis.ats_score,
        "key_skills": json.loads(analysis.key_skills),
        "strengths": json.loads(analysis.strengths),
        "missing_sections": json.loads(analysis.missing_sections),
        "improvements": json.loads(analysis.improvements)
    }

    return render_template(
        'analysis_view.html',
        feedback=feedback,
        resume_filename=resume.filename,
        analyzed_on=resume.updated_at or resume.created_at  # assuming you have timestamps
    )


# ===========================
# Cover Letter Generator
# ===========================

@app.route('/cover-letter', methods=['GET', 'POST'])
@login_required
def cover_letter():
    from forms import CoverLetterForm
    from models import Resume, CoverLetter
    from utils.gemini_client import generate_cover_letter
    import json

    # Check if user has a resume
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        if request.is_json:
            return jsonify({"error": "Resume required"}), 400
        return render_template('cover_letter.html', has_resume=False)

    if request.method == 'POST':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        company_info = request.form.get('company_info') or "Not provided"

        if not job_title or not job_description:
            return jsonify({"error": "Job title and description are required"}), 400

        try:
            # Generate AI cover letter
            letter = generate_cover_letter(resume.content, job_description, company_info)

            # Save to DB
            new_letter = CoverLetter(
                job_title=job_title,
                job_description=job_description,
                company_info=company_info,
                content=letter,
                user_id=current_user.id,
                resume_id=resume.id
            )
            db.session.add(new_letter)
            db.session.commit()

            return jsonify({
                "success": True,
                "letter": letter
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # GET request
    return render_template('cover_letter.html', has_resume=True)

@app.route('/cover-letters')
@login_required
def view_cover_letters():
    letters = CoverLetter.query.filter_by(user_id=current_user.id).order_by(CoverLetter.created_at.desc()).all()
    return render_template('view_cover_letters.html', cover_letters=letters)

@app.route('/cover-letter/view/<int:letter_id>')
@login_required
def view_cover_letter(letter_id):
    letter = CoverLetter.query.filter_by(id=letter_id, user_id=current_user.id).first_or_404()
    return jsonify({
        'job_title': letter.job_title,
        'content': letter.content
    })

@app.route('/cover-letter/delete/<int:letter_id>', methods=['GET'])
@login_required
def delete_cover_letter(letter_id):
    letter = CoverLetter.query.filter_by(id=letter_id, user_id=current_user.id).first_or_404()
    db.session.delete(letter)
    db.session.commit()
    flash("Cover letter deleted.", "success")
    return redirect(url_for('view_cover_letters'))

# ===========================
# Interview Preparation
# ===========================

@app.route('/interview-prep', methods=['GET', 'POST'])
@login_required
def interview_prep():
    from models import Resume, InterviewPrep
    from utils.gemini_client import generate_interview_prep
    import json
    import re

    # Check if user has a resume
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        if request.is_json:
            return jsonify({"error": "Resume required. Please upload your resume first."}), 400
        return render_template('interview_prep.html', has_resume=False)

    if request.method == 'POST':
        job_title = request.form.get('job_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        options_json = request.form.get('options', '[]')

        if not job_title:
            return jsonify({"error": "Job title is required."}), 400
        if not job_description:
            return jsonify({"error": "Job description is required."}), 400

        try:
            # Parse options
            try:
                options = json.loads(options_json)
            except json.JSONDecodeError:
                options = []

            # Call AI
            raw_ai_output = generate_interview_prep(
                resume_text=resume.content,
                job_title=job_title,
                job_description=job_description,
                options=options
            )

            # Log raw output
            print("\n=== Raw AI Output ===")
            print(raw_ai_output)
            print("=====================\n")

            # Extract JSON
            json_match = re.search(r'\{.*\}', raw_ai_output, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in AI response")

            json_str = json_match.group()

            # Try parsing
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                print("JSON parse failed. Trying repair-json...")
                try:
                    from repair_json import repair_json
                    fixed = repair_json(json_str)
                    data = json.loads(fixed)
                    print("✅ repair_json fixed it!")
                except ImportError:
                    raise ValueError("repair-json not installed and JSON is invalid")

            # ✅ Make fields optional with defaults
            final_data = {
                "job_title": data.get("job_title", job_title),
                "company": data.get("company", "the company"),
                "summary": data.get("summary", "Preparation guide generated by AI."),
                "sections": data.get("sections", []),  # ✅ Now optional
                "key_skills": data.get("key_skills", []),
                "behavioral_questions": data.get("behavioral_questions", []),
                "questions_to_ask": data.get("questions_to_ask", []),
                "final_tip": data.get("final_tip", "Practice your answers out loud and tailor them to your own experiences.")
            }

            # ✅ Save to DB
            new_prep = InterviewPrep(
                job_title=final_data["job_title"],
                job_description=job_description,
                options=options_json,
                content=json.dumps(final_data, ensure_ascii=False),
                user_id=current_user.id,
                resume_id=resume.id
            )
            db.session.add(new_prep)
            db.session.commit()

            return jsonify({
                "success": True,
                "content": json.dumps(final_data, ensure_ascii=False)
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Interview Prep Error: {str(e)}")
            return jsonify({"error": f"Failed to generate interview prep: {str(e)}"}), 500

    # GET request
    return render_template('interview_prep.html', has_resume=True)

@app.route('/interview-preps')
@login_required
def view_interview_preps():
    from models import InterviewPrep
    preps = InterviewPrep.query.filter_by(user_id=current_user.id).order_by(InterviewPrep.created_at.desc()).all()
    return render_template('view_interview_preps.html', interview_preps=preps)


@app.route('/interview-prep/view/<int:prep_id>')
@login_required
def view_interview_prep(prep_id):
    from models import InterviewPrep
    prep = InterviewPrep.query.filter_by(id=prep_id, user_id=current_user.id).first_or_404()
    try:
        import json
        data = json.loads(prep.content)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "Could not parse content"}), 500


@app.route('/interview-prep/delete/<int:prep_id>', methods=['GET'])
@login_required
def delete_interview_prep(prep_id):
    from models import InterviewPrep
    prep = InterviewPrep.query.filter_by(id=prep_id, user_id=current_user.id).first_or_404()
    db.session.delete(prep)
    db.session.commit()
    flash("Interview prep deleted.", "success")
    return redirect(url_for('view_interview_preps'))


# Create tables
with app.app_context():
    db.create_all()


# Run the app
if __name__ == '__main__':
    app.run(debug=True)