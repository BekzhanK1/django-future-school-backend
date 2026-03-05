import os
import fitz  # PyMuPDF
from openai import OpenAI
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
from .models_ktp import (
    AcademicPlan, PlanSubjectGroup, PlanQuarterDetail,
    Section, LearningObjective, Lesson
)
from .models_academic_year import Quarter
from .models import Course, SubjectGroup
from .schemas_ktp import KtpExtractionResponse

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_file: UploadedFile) -> str:
    """Extracts all text from an uploaded PDF file."""
    text = ""
    pdf_file.seek(0)
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    for page in pdf_document:
        text += page.get_text("text") + "\n"
    return text

def parse_ktp_with_openai(text: str) -> KtpExtractionResponse:
    """Sends extracted text to OpenAI and demands a structured JSON response."""
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert educational data extraction assistant. "
                    "Extract the Calendar-Thematic Plan (KTP) details from the provided text. "
                    "Ensure you correctly capture standard lessons as well as summative assessments "
                    "(COP/СОР and COCH/СОЧ). Set `is_summative` to true for assessments. "
                    "Infer and convert dates to YYYY-MM-DD format based on the academic year. "
                    "Ensure objective codes are properly isolated into lists of strings."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ],
        response_format=KtpExtractionResponse,
        temperature=0.1
    )
    print(response.choices[0].message.parsed)
    return response.choices[0].message.parsed


def process_ktp_pdf(pdf_file: UploadedFile, subject_group_id: str = None) -> AcademicPlan:
    """
    Main orchestration function:
    1. Extracts PDF text.
    2. Parses with OpenAI.
    3. Saves structured data to DB.
    """
    text = extract_text_from_pdf(pdf_file)
    parsed_ktp = parse_ktp_with_openai(text)
    
    return save_parsed_ktp_to_db(parsed_ktp, subject_group_id)


@transaction.atomic
def save_parsed_ktp_to_db(parsed_data: KtpExtractionResponse, subject_group_id: str = None) -> AcademicPlan:
    """
    Persists the structured KTP data into the Django models safely using transactions.
    """
    metadata = parsed_data.plan_metadata
    
    # Resolve SubjectGroup first if provided to get the exact Course
    subject_group = None
    course = None
    
    if subject_group_id:
        try:
            subject_group = SubjectGroup.objects.get(id=subject_group_id)
            course = subject_group.course
        except SubjectGroup.DoesNotExist:
            pass

    # Fallback to AI-parsed metadata if no exact Course was found
    if not course:
        if metadata.course_id:
            try:
                course = Course.objects.get(id=metadata.course_id)
            except Course.DoesNotExist:
                course, _ = Course.objects.get_or_create(
                    name=metadata.course_name,
                    defaults={'course_code': metadata.course_name[:20].upper(), 'grade': 0}
                )
        else:
            course, _ = Course.objects.get_or_create(
                name=metadata.course_name,
                defaults={'course_code': metadata.course_name[:20].upper(), 'grade': 0}
            )

    # 1. Create Academic Plan
    plan = AcademicPlan.objects.create(
        course=course,
        teacher_name=metadata.teacher_name,
        academic_year=metadata.academic_year,
        school_name=metadata.school_name
    )

    # 2. Attach Subject Group
    if subject_group:
        PlanSubjectGroup.objects.create(plan=plan, subject_group=subject_group)

    # 4. Create Quarters and Details
    for quarter_data in parsed_data.quarters_details:
        # Find the global Quarter matching the index for this academic year string
        # Since AcademicYear is a string in AcademicPlan, we need to match the actual model
        # Assuming the AcademicYear model name matches the string (e.g., "2025-2026")
        from .models_academic_year import AcademicYear
        
        ac_year = AcademicYear.objects.filter(name=metadata.academic_year).first()
        if not ac_year:
            # Create a placeholder if it doesn't exist
            ac_year = AcademicYear.objects.create(
                name=metadata.academic_year,
                start_date=f"{metadata.academic_year[:4]}-09-01",
                end_date=f"{metadata.academic_year[-4:]}-05-25"
            )
            
        global_quarter, _ = Quarter.objects.get_or_create(
            academic_year=ac_year,
            quarter_index=quarter_data.quarter_number,
            defaults={
                'start_date': ac_year.start_date, # Placeholder
                'end_date': ac_year.end_date      # Placeholder
            }
        )
        
        plan_quarter = PlanQuarterDetail.objects.create(
            plan=plan,
            quarter=global_quarter,
            sor_count=quarter_data.sor_count,
            soch_count=quarter_data.soch_count,
            total_hours=quarter_data.total_hours
        )

        # 5. Create Sections
        for s_idx, section_data in enumerate(quarter_data.sections):
            section = Section.objects.create(
                plan_quarter_detail=plan_quarter,
                section_name=section_data.section_name,
                order=s_idx
            )

            # 6. Create Lessons
            for lesson_data in section_data.lessons:
                lesson = Lesson.objects.create(
                    section=section,
                    lesson_number=lesson_data.lesson_number,
                    topic=lesson_data.topic,
                    hours=lesson_data.hours,
                    scheduled_date=lesson_data.date_iso if lesson_data.date_iso else None,
                    is_summative=lesson_data.is_summative
                )

                # 7. Map Learning Objectives
                for code in lesson_data.objective_codes:
                    if code.strip():
                        objective, _ = LearningObjective.objects.get_or_create(
                            code=code.strip(),
                            defaults={'description': 'Automatically extracted objective'}
                        )
                        lesson.objectives.add(objective)

    return plan
