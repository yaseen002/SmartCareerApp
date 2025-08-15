import requests
import os
import time
import random

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables.")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"


def call_gemini(prompt, model="gemini-1.5-flash", max_retries=3):
    """
    Calls Gemini API with retry logic on 503 errors.
    """
    url = GEMINI_API_URL.format(model=model)
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 32,
            "topP": 0.9,
            "maxOutputTokens": 1024
        }
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=headers, params=params, json=data)

            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']

            elif response.status_code == 503:
                if attempt < max_retries:
                    # Exponential backoff with jitter
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    print(f"503 Overloaded. Retrying in {wait:.2f}s... (Attempt {attempt + 1})")
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError("Gemini API is overloaded. Please try again later.")

            else:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise RuntimeError(f"API request failed: {str(e)}")
            time.sleep(2 ** attempt)  # Retry on network issues

    raise RuntimeError("Max retries exceeded.")


# -------------------------------
# AI-Powered Career Functions
# -------------------------------

def analyze_resume(resume_text):
    prompt = f"""
    Analyze the following resume and return a JSON object with:
    - "ats_score": number (1-10)
    - "key_skills": array of strings
    - "strengths": array of strings
    - "missing_sections": array of strings
    - "improvements": array of {{"issue": "...", "suggestion": "..."}}

    Return ONLY valid JSON. No extra text.

    Example:
    {{
      "ats_score": 8,
      "key_skills": ["Python", "Flask"],
      "strengths": ["Strong backend experience"],
      "missing_sections": ["Summary"],
      "improvements": [
        {{"issue": "Weak bullet points", "suggestion": "Use action verbs..."}}
      ]
    }}

    Resume:
    {resume_text[:10000]}
    """
    return call_gemini(prompt)


def generate_cover_letter(resume_text, job_description, company_info="Not provided"):
    """
    Generates a personalized cover letter using resume, job description, and optional company info.
    """
    prompt = f"""
    Write a professional and compelling cover letter for a candidate applying to a role.
    Match the tone to the company and role. Highlight relevant experience and enthusiasm.

    Resume Summary:
    {resume_text[:8000]}

    Job Description:
    {job_description[:5000]}

    About the Company:
    {company_info}

    Make the letter concise, 3-4 paragraphs, and end with a call to action.
    """
    return call_gemini(prompt)


# def  generate_interview_prep(resume_text, job_title, job_description, options):
#     """
#     Generates structured interview prep content in JSON format.
#     """
#     prompt = f"""
#     You are an AI career coach. Analyze the user's resume and the job description below.
#     Return a structured JSON object with the following fields:

#     {{
#       "job_title": string,
#       "company": string,
#       "summary": string,
#       "sections": array of {{
#         "title": string,
#         "content": string (concise, 2-3 sentences)
#       }},
#       "key_skills": array of {{
#         "skill": string,
#         "advice": string,
#         "example_prompt": string (e.g., "Tell me about a time you used {skill}")
#       }},
#       "behavioral_questions": array of {{
#         "question": string,
#         "tip": string
#       }},
#       "questions_to_ask": array of string,
#       "final_tip": string
#     }}

#     Rules:
#     - Return ONLY valid JSON. No extra text.
#     - Keep content professional and concise.
#     - Tailor advice to the user's resume and job description.

#     Resume:
#     {resume_text[:8000]}

#     Job Title:
#     {job_title}

#     Job Description:
#     {job_description[:5000]}
#     """
#     return call_gemini(prompt)

def generate_interview_prep(resume_text, job_title, job_description, options):
    prompt = f"""
    Analyze the resume and job description below.
    Return a JSON object with:
    - job_title
    - company
    - summary (1 sentence)
    - key_skills: [{{"skill": "...", "advice": "..."}}] (max 5 skills)
    - behavioral_questions: [{{"question": "...", "tip": "..."}}] (max 5)
    - questions_to_ask: [string] (max 5)

    Rules:
    - Return ONLY the JSON object.
    - No extra text before or after.
    - Keep all content very concise.
    - Escape quotes properly.
    - No trailing commas.
    - Do not use markdown.

    Resume: {resume_text[:6000]}  # Limit input size
    Job Title: {job_title}
    Job Description: {job_description[:3000]}
    Selected Options: {', '.join(options)}
    """
    return call_gemini(prompt)