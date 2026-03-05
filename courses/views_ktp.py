from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .services_ktp import process_ktp_pdf
from .models_ktp import AcademicPlan, PlanSubjectGroup, PlanQuarterDetail, Section, LearningObjective, Lesson
from .serializers_ktp import (
    AcademicPlanSerializer,
    PlanSubjectGroupSerializer,
    PlanQuarterDetailSerializer,
    SectionSerializer,
    LearningObjectiveSerializer,
    LessonSerializer,
)

class AcademicPlanViewSet(viewsets.ModelViewSet):
    queryset = AcademicPlan.objects.all()
    serializer_class = AcademicPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            qs = qs.filter(course_id=course_id)
            
        subject_group_id = self.request.query_params.get('subject_group_id')
        if subject_group_id:
            qs = qs.filter(plan_subject_groups__subject_group_id=subject_group_id)
            
        return qs

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def parse_pdf(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No PDF file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        pdf_file = request.FILES['file']
        if not pdf_file.name.lower().endswith('.pdf'):
            return Response({'error': 'File must be a PDF'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            subject_group_id = request.data.get('subject_group_id')
            plan = process_ktp_pdf(pdf_file, subject_group_id)
            # Serialize the resulting plan
            serializer = self.get_serializer(plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def link_subject_groups(self, request, pk=None):
        plan = self.get_object()
        subject_group_ids = request.data.get('subject_group_ids', [])
        
        from .models import SubjectGroup
        for sg_id in subject_group_ids:
            sg = SubjectGroup.objects.filter(id=sg_id).first()
            if sg:
                PlanSubjectGroup.objects.get_or_create(plan=plan, subject_group=sg)
                
        return Response({'status': 'linked successfully'})


class PlanSubjectGroupViewSet(viewsets.ModelViewSet):
    queryset = PlanSubjectGroup.objects.all()
    serializer_class = PlanSubjectGroupSerializer
    permission_classes = [IsAuthenticated]


class PlanQuarterDetailViewSet(viewsets.ModelViewSet):
    queryset = PlanQuarterDetail.objects.all()
    serializer_class = PlanQuarterDetailSerializer
    permission_classes = [IsAuthenticated]


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]


class LearningObjectiveViewSet(viewsets.ModelViewSet):
    queryset = LearningObjective.objects.all()
    serializer_class = LearningObjectiveSerializer
    permission_classes = [IsAuthenticated]


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
