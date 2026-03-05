from typing import List, Optional
from pydantic import BaseModel, Field


class PlanMetadataSchema(BaseModel):
    course_name: str = Field(description="Name of the course/subject, e.g., 'Русский язык'")
    course_id: Optional[int] = Field(default=None, description="Course ID if explicitly available, usually null")
    academic_year: str = Field(description="Academic year string, e.g., '2025-2026'")
    teacher_name: str = Field(description="Full name of the teacher")
    school_name: str = Field(description="Name of the school")
    total_hours: int = Field(description="Total number of hours for the course across the entire year")


class LessonSchema(BaseModel):
    lesson_number: int = Field(description="Sequential number of the lesson within the section/quarter")
    topic: str = Field(description="Topic or title of the lesson")
    hours: int = Field(description="Number of academic hours allocated to this lesson (usually 1 or 2)")
    date_iso: Optional[str] = Field(description="Scheduled date in YYYY-MM-DD format based on the academic year. If not specified, leave null")
    is_summative: bool = Field(default=False, description="True if this lesson represents a summative assessment like СОР or СОЧ")
    objective_codes: List[str] = Field(description="List of learning objective codes, e.g., ['5.1.1.1', '5.1.3.1']")


class SectionSchema(BaseModel):
    section_name: str = Field(description="Name or title of the section, e.g., 'Раздел 1. Культура: язык и общение'")
    lessons: List[LessonSchema] = Field(description="List of lessons belonging to this section")


class QuarterSchema(BaseModel):
    quarter_number: int = Field(description="Quarter index from 1 to 4")
    total_hours: int = Field(description="Total academic hours allocated for this quarter")
    sor_count: int = Field(description="Number of СОРs in this quarter based on the explanatory notes")
    soch_count: int = Field(description="Number of СОЧs in this quarter based on the explanatory notes")
    sections: List[SectionSchema] = Field(description="List of sections taught within this quarter")


class KtpExtractionResponse(BaseModel):
    """
    Root structure expected from OpenAI when parsing a KTP document.
    """
    plan_metadata: PlanMetadataSchema
    target_groups: List[str] = Field(description="List of target classes/groups, e.g., ['5 В', '5 C']")
    quarters_details: List[QuarterSchema] = Field(description="Detailed breakdown of content by quarters")
