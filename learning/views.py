from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, NumberFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
import zipfile
import io
import os
from .models import (
    Resource, Assignment, AssignmentAttachment, Submission, SubmissionAttachment,
    Grade, ManualGrade, GradeWeight, Attendance, AttendanceRecord, AttendanceStatus,
)
from .serializers import (
    ResourceSerializer, ResourceTreeSerializer, AssignmentSerializer, AssignmentAttachmentSerializer,
    SubmissionSerializer, SubmissionAttachmentSerializer, GradeSerializer, BulkGradeSerializer,
    ManualGradeSerializer, GradeWeightSerializer, GradeWeightBulkSerializer,
    AttendanceSerializer, AttendanceCreateSerializer, AttendanceUpdateSerializer,
    StudentAttendanceHistorySerializer, AttendanceMetricsSerializer,
)
from .role_permissions import RoleBasedPermission
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from users.models import UserRole, User
from .models import Event
from .serializers import EventSerializer

from datetime import date, timedelta, datetime
from django.utils import timezone
from .models import EventType


class AssignmentFilterSet(FilterSet):
    """Custom filterset for Assignment to allow filtering by subject_group"""
    subject_group = NumberFilter(field_name='course_section__subject_group', lookup_expr='exact')
    
    class Meta:
        model = Assignment
        fields = ['course_section', 'teacher', 'subject_group']


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.select_related('course_section', 'parent_resource').all()
    serializer_class = ResourceSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course_section', 'type', 'parent_resource']
    search_fields = ['title', 'description']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def create(self, request, *args, **kwargs):
        """Override create method to add debugging for 400 errors"""
        print(f"Resource creation request data: {request.data}")
        print(f"Request user: {request.user}")
        print(f"User role: {request.user.role}")
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            print("Serializer is valid, creating resource...")
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            print(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see resources for their courses
        if user.role == UserRole.STUDENT:
            # Get student's classrooms
            student_classrooms = user.classroom_users.values_list('classroom', flat=True)
            # Filter resources that belong to course sections in the student's classrooms
            # IMPORTANT: Students should NOT see template sections (where subject_group is null)
            queryset = queryset.filter(
                course_section__subject_group__classroom__in=student_classrooms,
                course_section__subject_group__isnull=False  # Exclude template sections
            )
        # Parents can see resources for their children's courses
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            children_classrooms = Q()
            for child_id in children_ids:
                child = User.objects.get(id=child_id)
                child_classrooms = child.classroom_users.values_list('classroom', flat=True)
                children_classrooms |= Q(course_section__subject_group__classroom__in=child_classrooms)
            queryset = queryset.filter(
                children_classrooms,
                course_section__subject_group__isnull=False
            )
        # Teachers can see resources for their subject groups
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(course_section__subject_group__teacher=user)
        # School admins can see resources from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(course_section__subject_group__classroom__school=user.school)
        # Superadmins can see all resources (default queryset)
        
        # By default, only show root resources (no parent)
        if self.action == 'list' and 'show_all' not in self.request.query_params:
            queryset = queryset.filter(parent_resource__isnull=True)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        """Bulk update resource positions.
        Body: [{"id": <id>, "position": <pos>}, ...]
        """
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
        objs = Resource.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        Resource.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})
    
    @action(detail=False, methods=['get'], url_path='all')
    def all_resources(self, request):
        """Get all resources for a course section (including children)"""
        course_section_id = request.query_params.get('course_section_id')
        if not course_section_id:
            return Response({'error': 'course_section_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        resources = Resource.objects.filter(
            course_section_id=course_section_id
        ).order_by('position', 'id')
        
        serializer = ResourceSerializer(resources, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        """Get resource tree for a course section (root resources with nested children)"""
        course_section_id = request.query_params.get('course_section_id')
        if not course_section_id:
            return Response({'error': 'course_section_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get root resources (no parent)
        root_resources = Resource.objects.filter(
            course_section_id=course_section_id,
            parent_resource__isnull=True
        ).order_by('position', 'id')
        
        serializer = ResourceTreeSerializer(root_resources, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """Move resource to different position or parent"""
        resource = self.get_object()
        new_position = request.data.get('position', resource.position)
        new_parent_id = request.data.get('parent_id')
        
        if new_parent_id is not None:
            try:
                new_parent = Resource.objects.get(id=new_parent_id)
                if new_parent.course_section != resource.course_section:
                    return Response({'error': 'Parent must be in same course section'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                resource.parent_resource = new_parent
            except Resource.DoesNotExist:
                return Response({'error': 'Parent resource not found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            resource.parent_resource = None
        
        resource.position = new_position
        resource.save()
        
        serializer = ResourceSerializer(resource, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='unlink-from-template')
    def unlink_from_template(self, request, pk=None):
        """
        Unlink this resource from its template so it will no longer be auto-synced.
        """
        resource = self.get_object()
        resource.is_unlinked_from_template = True
        resource.save(update_fields=['is_unlinked_from_template'])
        serializer = ResourceSerializer(resource, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='relink-to-template')
    def relink_to_template(self, request, pk=None):
        """
        Relink this resource to its template so it will be auto-synced again.
        """
        resource = self.get_object()
        if not resource.template_resource:
            return Response(
                {'error': 'This resource is not linked to any template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        resource.is_unlinked_from_template = False
        resource.save(update_fields=['is_unlinked_from_template'])
        serializer = ResourceSerializer(resource, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='sync-status')
    def sync_status(self, request, pk=None):
        """
        Check if resource is in sync with its template.
        Returns sync status for admin users.
        """
        resource = self.get_object()
        
        if not resource.template_resource:
            return Response({
                'is_linked': False,
                'is_unlinked': False,
                'is_outdated': False,
                'message': 'Resource is not linked to any template'
            })
        
        template = resource.template_resource
        is_unlinked = resource.is_unlinked_from_template
        
        # Check if resource is outdated (compare key fields with template)
        is_outdated = False
        outdated_fields = []
        
        if not is_unlinked:
            if resource.title != template.title:
                is_outdated = True
                outdated_fields.append('title')
            if resource.description != template.description:
                is_outdated = True
                outdated_fields.append('description')
            if resource.url != template.url:
                is_outdated = True
                outdated_fields.append('url')
            if resource.type != template.type:
                is_outdated = True
                outdated_fields.append('type')
            # Check file - compare file names/paths
            if template.file and resource.file:
                if str(template.file) != str(resource.file):
                    is_outdated = True
                    outdated_fields.append('file')
            elif template.file and not resource.file:
                is_outdated = True
                outdated_fields.append('file')
        
        return Response({
            'is_linked': True,
            'is_unlinked': is_unlinked,
            'is_outdated': is_outdated,
            'outdated_fields': outdated_fields,
            'template_id': template.id,
            'message': 'outdated' if is_outdated else ('unlinked' if is_unlinked else 'synced')
        })

    @action(detail=False, methods=['post'], url_path='create-directory-with-files')
    def create_directory_with_files(self, request):
        """
        Create a directory resource with multiple files as children.
        Expected payload:
        - course_section: int
        - title: str
        - files: list of files (multipart/form-data)
        """
        try:
            course_section_id = request.data.get('course_section')
            title = request.data.get('title')
            files = request.FILES.getlist('files')
            
            if not course_section_id or not title:
                return Response(
                    {'error': 'course_section and title are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the directory resource first
            directory_data = {
                'course_section': course_section_id,
                'type': 'directory',
                'title': title,
            }
            
            directory_serializer = self.get_serializer(data=directory_data)
            if not directory_serializer.is_valid():
                return Response(directory_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            directory = directory_serializer.save()
            directory_id = directory.id
            
            created_files = []
            
            # Create child file resources
            for file in files:
                file_data = {
                    'course_section': course_section_id,
                    'type': 'file',
                    'title': file.name,
                    'file': file,
                    'parent_resource': directory_id,
                }
                
                file_serializer = self.get_serializer(data=file_data)
                if file_serializer.is_valid():
                    file_resource = file_serializer.save()
                    created_files.append({
                        'id': file_resource.id,
                        'title': file_resource.title,
                        'file': file_resource.file.url if file_resource.file else None,
                    })
                else:
                    # If file creation fails, log error but continue
                    print(f"Error creating file {file.name}: {file_serializer.errors}")
            
            # Return directory with created files
            directory_response = self.get_serializer(directory).data
            directory_response['created_files'] = created_files
            directory_response['files_count'] = len(created_files)
            
            return Response(directory_response, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"Error creating directory with files: {str(e)}")
            return Response(
                {'error': 'Failed to create directory with files'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='add-files-to-directory')
    def add_files_to_directory(self, request):
        """
        Add multiple files to an existing directory.
        Expected payload:
        - directory_id: int (ID of existing directory)
        - course_section: int
        - files: list of files (multipart/form-data)
        """
        try:
            directory_id = request.data.get('directory_id')
            course_section_id = request.data.get('course_section')
            files = request.FILES.getlist('files')
            
            if not directory_id or not course_section_id:
                return Response(
                    {'error': 'directory_id and course_section are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the directory exists and user has permission
            try:
                directory = Resource.objects.get(id=directory_id, type='directory')
            except Resource.DoesNotExist:
                return Response(
                    {'error': 'Directory not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            created_files = []
            
            # Create child file resources
            for file in files:
                file_data = {
                    'course_section': course_section_id,
                    'type': 'file',
                    'title': file.name,
                    'file': file,
                    'parent_resource': directory_id,
                }
                
                file_serializer = self.get_serializer(data=file_data)
                if file_serializer.is_valid():
                    file_resource = file_serializer.save()
                    created_files.append({
                        'id': file_resource.id,
                        'title': file_resource.title,
                        'file': file_resource.file.url if file_resource.file else None,
                    })
                else:
                    # If file creation fails, log error but continue
                    print(f"Error creating file {file.name}: {file_serializer.errors}")
            
            # Return success response with created files info
            response_data = {
                'directory_id': directory_id,
                'directory_title': directory.title,
                'created_files': created_files,
                'files_count': len(created_files),
                'message': f'Successfully added {len(created_files)} file(s) to directory'
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"Error adding files to directory: {str(e)}")
            return Response(
                {'error': 'Failed to add files to directory'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='download-zip')
    def download_directory_zip(self, request, pk=None):
        """
        Download all files in a directory as a ZIP file.
        """
        
        try:
            # Get the directory resource
            directory = self.get_object()
            if directory.type != 'directory':
                return Response(
                    {'error': 'Resource is not a directory'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get all files in the directory (including nested files)
            def get_all_files(resource, file_list=None, base_path=''):
                if file_list is None:
                    file_list = []
                
                if resource.type == 'file' and resource.file:
                    file_list.append({
                        'path': os.path.join(base_path, resource.title),
                        'file': resource.file
                    })
                elif resource.type == 'directory':
                    for child in resource.children.all():
                        get_all_files(child, file_list, os.path.join(base_path, resource.title))
                
                return file_list
            
            all_files = get_all_files(directory)
            
            if not all_files:
                return Response(
                    {'error': 'Directory is empty'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in all_files:
                    try:
                        # Read file content
                        file_path = file_info['file'].path
                        if os.path.exists(file_path):
                            with open(file_path, 'rb') as f:
                                zip_file.writestr(file_info['path'], f.read())
                        else:
                            # File doesn't exist on disk, skip it
                            continue
                    except Exception as e:
                        print(f"Error adding file {file_info['path']} to ZIP: {str(e)}")
                        continue
            
            zip_buffer.seek(0)
            
            # Create HTTP response
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{directory.title}.zip"'
            response['Content-Length'] = len(zip_buffer.getvalue())
            
            return response
            
        except Exception as e:
            print(f"Error creating ZIP file: {str(e)}")
            return Response(
                {'error': 'Failed to create ZIP file'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related('course_section', 'teacher').prefetch_related('attachments').all()
    serializer_class = AssignmentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AssignmentFilterSet
    search_fields = ['title', 'description']
    ordering_fields = ['due_at', 'title']
    ordering = ['due_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see assignments for their courses
        if user.role == UserRole.STUDENT:
            student_classrooms = user.classroom_users.values_list('classroom', flat=True)
            # Filter assignments that belong to course sections in the student's classrooms
            # IMPORTANT: Students should NOT see template sections (where subject_group is null)
            queryset = queryset.filter(
                course_section__subject_group__classroom__in=student_classrooms,
                course_section__subject_group__isnull=False  # Exclude template sections
            )
        # Parents can see assignments for their children's courses
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            children_classrooms = Q()
            for child_id in children_ids:
                child = User.objects.get(id=child_id)
                child_classrooms = child.classroom_users.values_list('classroom', flat=True)
                children_classrooms |= Q(course_section__subject_group__classroom__in=child_classrooms)
            queryset = queryset.filter(
                children_classrooms,
                course_section__subject_group__isnull=False
            )
        # Teachers can see assignments they created
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(teacher=user)
        # School admins can see assignments from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(course_section__subject_group__classroom__school=user.school)
        # Superadmins can see all assignments (default queryset)
        
        return queryset
    
    def get_permissions(self):
        """
        Override permissions to allow students to read assignments from their courses
        but restrict create/update/delete operations
        """
        if self.action in ['list', 'retrieve']:
            # Allow all authenticated users to read assignments
            permission_classes = [permissions.IsAuthenticated]
        else:
            # Use role-based permissions for create/update/delete
            permission_classes = [RoleBasedPermission]
        
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'], url_path='unlink-from-template')
    def unlink_from_template(self, request, pk=None):
        """
        Unlink this assignment from its template so it will no longer be auto-synced.
        """
        assignment = self.get_object()
        assignment.is_unlinked_from_template = True
        assignment.save(update_fields=['is_unlinked_from_template'])
        serializer = AssignmentSerializer(assignment, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='relink-to-template')
    def relink_to_template(self, request, pk=None):
        """
        Relink this assignment to its template so it will be auto-synced again.
        """
        assignment = self.get_object()
        if not assignment.template_assignment:
            return Response(
                {'error': 'This assignment is not linked to any template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        assignment.is_unlinked_from_template = False
        assignment.save(update_fields=['is_unlinked_from_template'])
        serializer = AssignmentSerializer(assignment, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='sync-status')
    def sync_status(self, request, pk=None):
        """
        Check if assignment is in sync with its template.
        Returns sync status for admin users.
        """
        assignment = self.get_object()
        
        if not assignment.template_assignment:
            return Response({
                'is_linked': False,
                'is_unlinked': False,
                'is_outdated': False,
                'message': 'Assignment is not linked to any template'
            })
        
        template = assignment.template_assignment
        is_unlinked = assignment.is_unlinked_from_template
        
        # Check if assignment is outdated (compare key fields with template)
        is_outdated = False
        outdated_fields = []
        
        if not is_unlinked:
            if assignment.title != template.title:
                is_outdated = True
                outdated_fields.append('title')
            if assignment.description != template.description:
                is_outdated = True
                outdated_fields.append('description')
            if assignment.max_grade != template.max_grade:
                is_outdated = True
                outdated_fields.append('max_grade')
            # Check file - compare file names/paths
            if template.file and assignment.file:
                if str(template.file) != str(assignment.file):
                    is_outdated = True
                    outdated_fields.append('file')
            elif template.file and not assignment.file:
                is_outdated = True
                outdated_fields.append('file')
        
        return Response({
            'is_linked': True,
            'is_unlinked': is_unlinked,
            'is_outdated': is_outdated,
            'outdated_fields': outdated_fields,
            'template_id': template.id,
            'message': 'outdated' if is_outdated else ('unlinked' if is_unlinked else 'synced')
        })

    @action(detail=True, methods=['post'], url_path='sync-from-template')
    def sync_from_template(self, request, pk=None):
        """
        Sync this assignment with its template.
        Only available for superadmins.
        """
        from schools.permissions import IsSuperAdmin
        from django.utils import timezone
        from datetime import timedelta, datetime
        
        if not IsSuperAdmin().has_permission(request, self):
            return Response(
                {'error': 'Only superadmins can sync individual assignments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = self.get_object()
        
        if not assignment.template_assignment:
            return Response(
                {'error': 'Assignment is not linked to any template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if assignment.is_unlinked_from_template:
            return Response(
                {'error': 'Assignment is unlinked from template and cannot be synced'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        template = assignment.template_assignment
        derived_sec = assignment.course_section
        
        # Calculate due_at based on template-relative fields if available
        due_at = template.due_at
        if (
            derived_sec.start_date
            and template.template_offset_days_from_section_start is not None
            and template.template_due_time is not None
        ):
            due_date = derived_sec.start_date + timedelta(
                days=template.template_offset_days_from_section_start
            )
            due_at = datetime.combine(
                due_date,
                template.template_due_time,
                tzinfo=timezone.get_current_timezone(),
            )
        
        # Update assignment fields from template
        assignment.title = template.title
        assignment.description = template.description
        assignment.due_at = due_at
        assignment.max_grade = template.max_grade
        if template.file:
            assignment.file = template.file
        assignment.save(update_fields=[
            'title', 'description', 'due_at', 'max_grade', 'file'
        ])
        
        # Sync attachments
        existing_attachments = list(assignment.attachments.all())
        template_attachments = list(template.attachments.all().order_by("position", "id"))
        
        # Remove attachments that no longer exist in template
        for existing_att in existing_attachments:
            if not any(
                ta.position == existing_att.position and
                ta.type == existing_att.type
                for ta in template_attachments
            ):
                existing_att.delete()
        
        # Create or update attachments
        for att in template_attachments:
            existing_att = assignment.attachments.filter(
                position=att.position,
                type=att.type
            ).first()
            
            if existing_att:
                existing_att.title = att.title
                existing_att.content = att.content
                existing_att.file_url = att.file_url
                if att.file and not existing_att.file:
                    existing_att.file = att.file
                existing_att.save()
            else:
                AssignmentAttachment.objects.create(
                    assignment=assignment,
                    type=att.type,
                    title=att.title,
                    content=att.content,
                    file_url=att.file_url,
                    file=att.file,
                    position=att.position,
                )
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)


class AssignmentAttachmentViewSet(viewsets.ModelViewSet):
    queryset = AssignmentAttachment.objects.select_related('assignment').all()
    serializer_class = AssignmentAttachmentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assignment', 'type']
    search_fields = ['title', 'content']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see attachments for assignments in their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(assignment__course_section__subject_group__course__in=student_courses)
        # Teachers can see attachments for their assignments
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(assignment__teacher=user)
        # School admins can see attachments from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(assignment__course_section__subject_group__classroom__school=user.school)
        # Superadmins can see all attachments (default queryset)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
        objs = AssignmentAttachment.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        AssignmentAttachment.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create attachments for an assignment"""
        assignment_id = request.data.get('assignment_id')
        attachments_data = request.data.get('attachments', [])
        
        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_attachments = []
        for attachment_data in attachments_data:
            attachment_data['assignment'] = assignment_id
            serializer = AssignmentAttachmentSerializer(data=attachment_data)
            if serializer.is_valid():
                attachment = serializer.save()
                created_attachments.append(attachment)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        response_serializer = AssignmentAttachmentSerializer(created_attachments, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.select_related('assignment', 'student').prefetch_related('attachments').all()
    serializer_class = SubmissionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assignment', 'student']
    search_fields = ['student__username', 'student__email']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see their own submissions
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Parents can see submissions of their children
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            queryset = queryset.filter(student_id__in=children_ids)
        # Teachers can see submissions for their assignments only
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(assignment__teacher=user)
        # School admins can see submissions from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(student__school=user.school)
        # Superadmins can see all submissions (default queryset)
        
        return queryset
    
    def perform_create(self, serializer):
        # Automatically set the student to the authenticated user
        serializer.save(student=self.request.user)


class SubmissionAttachmentViewSet(viewsets.ModelViewSet):
    queryset = SubmissionAttachment.objects.select_related('submission').all()
    serializer_class = SubmissionAttachmentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['submission', 'type']
    search_fields = ['title', 'content']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see attachments for their own submissions
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(submission__student=user)
        # Teachers can see attachments for submissions to their assignments
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(submission__assignment__teacher=user)
        # School admins can see attachments from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(submission__student__school=user.school)
        # Superadmins can see all attachments (default queryset)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
        objs = SubmissionAttachment.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        SubmissionAttachment.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create attachments for a submission"""
        submission_id = request.data.get('submission_id')
        attachments_data = request.data.get('attachments', [])
        
        if not submission_id:
            return Response({'error': 'submission_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_attachments = []
        for attachment_data in attachments_data:
            attachment_data['submission'] = submission_id
            serializer = SubmissionAttachmentSerializer(data=attachment_data)
            if serializer.is_valid():
                attachment = serializer.save()
                created_attachments.append(attachment)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        response_serializer = SubmissionAttachmentSerializer(created_attachments, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related('submission', 'graded_by').all()
    serializer_class = GradeSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['submission', 'graded_by']
    search_fields = ['submission__student__username', 'feedback']
    ordering_fields = ['graded_at', 'grade_value']
    ordering = ['-graded_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see grades for their own submissions
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(submission__student=user)
        # Parents can see grades for their children's submissions
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            queryset = queryset.filter(submission__student_id__in=children_ids)
        # Teachers can see grades for submissions to their assignments
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(submission__assignment__teacher=user)
        # School admins can see grades from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(submission__student__school=user.school)
        # Superadmins can see all grades (default queryset)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-grade')
    def bulk_grade(self, request):
        """Bulk grade multiple submissions"""
        serializer = BulkGradeSerializer(data=request.data, many=True)
        if serializer.is_valid():
            grades = []
            for item in serializer.validated_data:
                submission = Submission.objects.get(id=item['submission_id'])
                grade, created = Grade.objects.get_or_create(
                    submission=submission,
                    defaults={
                        'graded_by': request.user,
                        'grade_value': item['grade_value'],
                        'feedback': item.get('feedback', ''),
                    }
                )
                if not created:
                    grade.grade_value = item['grade_value']
                    grade.feedback = item.get('feedback', '')
                    grade.graded_by = request.user
                    grade.save()
                grades.append(grade)
            
            response_serializer = GradeSerializer(grades, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManualGradeViewSet(viewsets.ModelViewSet):
    queryset = ManualGrade.objects.select_related(
        'student', 'subject_group', 'course_section', 'graded_by'
    ).all()
    serializer_class = ManualGradeSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['student', 'subject_group', 'course_section', 'grade_type']
    ordering_fields = ['graded_at', 'value']
    ordering = ['-graded_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            queryset = queryset.filter(student_id__in=children_ids)
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(subject_group__teacher=user)
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(subject_group__classroom__school=user.school)
        return queryset

    def perform_create(self, serializer):
        serializer.save(graded_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='grade-book')
    def grade_book(self, request):
        """
        Журнал оценок: задания + тесты + ручные оценки в одном списке.
        Параметры: subject_group (обязателен), student_id (опционально — иначе все ученики группы).
        """
        from assessments.models import Test, Attempt

        subject_group_id = request.query_params.get('subject_group')
        student_id = request.query_params.get('student_id')
        user = request.user

        if not subject_group_id:
            return Response(
                {'error': 'subject_group is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from courses.models import SubjectGroup
            sg = SubjectGroup.objects.get(pk=subject_group_id)
        except SubjectGroup.DoesNotExist:
            return Response({'error': 'Subject group not found'}, status=status.HTTP_404_NOT_FOUND)

        if user.role == UserRole.STUDENT:
            if not sg.classroom.classroom_users.filter(user=user).exists():
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            student_ids = [user.id]
        elif user.role == UserRole.PARENT:
            children_ids = list(user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True))
            if not children_ids:
                return Response({'results': []})
            student_ids = list(
                sg.classroom.classroom_users.filter(user_id__in=children_ids).values_list('user_id', flat=True)
            )
            if not student_ids:
                return Response({'results': []})
        elif user.role == UserRole.TEACHER:
            if sg.teacher_id != user.id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            student_ids = list(
                sg.classroom.classroom_users.filter(user__role=UserRole.STUDENT).values_list('user_id', flat=True)
            ) if not student_id else [int(student_id)]
        elif user.role == UserRole.SCHOOLADMIN:
            if sg.classroom.school_id != user.school_id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            student_ids = list(
                sg.classroom.classroom_users.filter(user__role=UserRole.STUDENT).values_list('user_id', flat=True)
            ) if not student_id else [int(student_id)]
        else:
            student_ids = list(
                sg.classroom.classroom_users.filter(user__role=UserRole.STUDENT).values_list('user_id', flat=True)
            ) if not student_id else [int(student_id)]

        section_ids = list(sg.sections.values_list('id', flat=True))
        results = []

        grades = Grade.objects.filter(
            submission__student_id__in=student_ids,
            submission__assignment__course_section_id__in=section_ids,
        ).select_related('submission__assignment', 'submission__student', 'graded_by')
        for g in grades:
            sub = g.submission
            asg = sub.assignment
            results.append({
                'source_type': 'assignment',
                'source_id': asg.id,
                'student_id': sub.student_id,
                'student_username': sub.student.username,
                'title': asg.title,
                'value': g.grade_value,
                'max_value': asg.max_grade,
                'graded_at': g.graded_at,
                'feedback': g.feedback,
                'graded_by_username': g.graded_by.username,
            })

        attempts = Attempt.objects.filter(
            student_id__in=student_ids,
            test__course_section_id__in=section_ids,
            is_completed=True,
        ).select_related('test', 'student').prefetch_related('test__questions')
        for a in attempts:
            max_pts = a.max_score or (sum(q.points for q in a.test.questions.all()) if a.test.questions.exists() else 100)
            if not max_pts:
                max_pts = 100
            results.append({
                'source_type': 'test',
                'source_id': a.test_id,
                'student_id': a.student_id,
                'student_username': a.student.username,
                'title': a.test.title,
                'value': a.score or 0,
                'max_value': max_pts or 100,
                'graded_at': a.submitted_at or a.started_at,
                'feedback': None,
                'graded_by_username': None,
            })

        manual = ManualGrade.objects.filter(
            student_id__in=student_ids,
            subject_group_id=sg.id,
        ).select_related('student', 'graded_by')
        for m in manual:
            results.append({
                'source_type': 'manual',
                'source_id': m.id,
                'student_id': m.student_id,
                'student_username': m.student.username,
                'title': m.title or m.get_grade_type_display(),
                'value': m.value,
                'max_value': m.max_value,
                'graded_at': m.graded_at,
                'feedback': m.feedback,
                'graded_by_username': m.graded_by.username,
                'grade_type': m.grade_type,
            })

        results.sort(key=lambda x: x['graded_at'] or timezone.now(), reverse=True)
        return Response({'results': results})

    @action(detail=False, methods=['get'], url_path='student-summary')
    def student_summary(self, request):
        """
        Сводка оценок ученика по всем его предметам.

        Параметры:
        - student_id (обязателен для родителя/учителя/админа, для ученика можно не передавать)
        """
        from courses.models import SubjectGroup
        from assessments.models import Attempt

        user = request.user
        student_id = request.query_params.get('student_id')

        # Определяем целевого ученика
        if user.role == UserRole.STUDENT:
            target_student_id = user.id if not student_id else int(student_id)
            if target_student_id != user.id:
                return Response(
                    {'error': 'Students can only view their own summary'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif user.role == UserRole.PARENT:
            if not student_id:
                return Response(
                    {'error': 'student_id is required for parent'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            target_student_id = int(student_id)
            if not user.children.filter(id=target_student_id, role=UserRole.STUDENT).exists():
                return Response(
                    {'error': 'You can only view summary for your own children'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            if not student_id:
                return Response(
                    {'error': 'student_id is required'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            target_student_id = int(student_id)

        # Находим все subject_group, где учится ученик
        subject_groups = SubjectGroup.objects.filter(
            classroom__classroom_users__user_id=target_student_id
        ).select_related('course', 'classroom').distinct()

        summary = []

        for sg in subject_groups:
            # Ручные оценки -> приводим к процентам
            manual_qs = ManualGrade.objects.filter(
                student_id=target_student_id,
                subject_group=sg,
            )
            manual_values = []
            for mg in manual_qs:
                if mg.value is not None and mg.max_value:
                    manual_values.append((mg.value / mg.max_value) * 100.0)

            # Оценки за задания -> тоже в процентах относительно max_grade
            # Фильтруем по course_section__subject_group, так как у Assignment нет прямого FK на SubjectGroup
            grades_qs = Grade.objects.filter(
                submission__student_id=target_student_id,
                submission__assignment__course_section__subject_group_id=sg.id,
            ).select_related('submission__assignment')

            assignment_values = []
            for g in grades_qs:
                if g.grade_value is not None:
                    assignment = getattr(g.submission, "assignment", None)
                    max_grade = getattr(assignment, "max_grade", None) if assignment else None
                    if max_grade:
                        assignment_values.append((g.grade_value / max_grade) * 100.0)

            # Оценки за тесты (берём процент как есть)
            attempts = Attempt.objects.filter(
                student_id=target_student_id,
                test__course_section__subject_group=sg,
                is_completed=True,
            )
            attempt_values = [a.percentage for a in attempts if a.percentage is not None]

            # Все значения теперь в процентах (0–100)
            all_values = manual_values + assignment_values + attempt_values
            avg = sum(all_values) / len(all_values) if all_values else None

            summary.append(
                {
                    'subject_group_id': sg.id,
                    'course_name': sg.course.name,
                    'classroom_name': str(sg.classroom),
                    'average': avg,
                    'manual_count': len(manual_values),
                    'assignment_grades_count': len(assignment_values),
                    'test_attempts_count': len(attempt_values),
                }
            )

        return Response({'results': summary})


class GradeWeightViewSet(viewsets.ModelViewSet):
    queryset = GradeWeight.objects.select_related('subject_group').all()
    serializer_class = GradeWeightSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['subject_group', 'source_type']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(subject_group__classroom__classroom_users__user=user)
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            queryset = queryset.filter(subject_group__classroom__classroom_users__user_id__in=children_ids)
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(subject_group__teacher=user)
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(subject_group__classroom__school=user.school)
        return queryset.distinct()

    @action(detail=False, methods=['post'], url_path='set-weights')
    def set_weights(self, request):
        """
        Сохранить все три веса одним запросом (сумма должна быть 100%).
        Тело: { "subject_group": id, "assignment": 0, "test": 30, "manual": 70 }.
        """
        serializer = GradeWeightBulkSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        from courses.models import SubjectGroup
        try:
            subject_group = SubjectGroup.objects.select_related('classroom').get(pk=data['subject_group'])
        except SubjectGroup.DoesNotExist:
            return Response({'subject_group': ['Subject group not found.']}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        if user.role == UserRole.TEACHER and subject_group.teacher_id != user.id:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == UserRole.SCHOOLADMIN and subject_group.classroom.school_id != user.school_id:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        from django.db import transaction
        with transaction.atomic():
            for source_type, weight in [('assignment', data['assignment']), ('test', data['test']), ('manual', data['manual'])]:
                GradeWeight.objects.update_or_create(
                    subject_group=subject_group,
                    source_type=source_type,
                    defaults={'weight': weight},
                )
        items = GradeWeight.objects.filter(subject_group=subject_group).order_by('source_type')
        response_serializer = GradeWeightSerializer(items, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('subject_group', 'taken_by').prefetch_related('records__student').all()
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject_group', 'taken_by', 'taken_at']
    search_fields = ['subject_group__course__name', 'notes']
    ordering_fields = ['taken_at']
    ordering = ['-taken_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AttendanceUpdateSerializer
        return AttendanceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see attendance for their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(subject_group__course__in=student_courses)
        # Teachers can see attendance for their subject groups
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(subject_group__teacher=user)
        # School admins can see attendance from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(subject_group__classroom__school=user.school)
        # Parents can see attendance only for their children
        elif user.role == UserRole.PARENT:
            # Get all classrooms where the user's children study
            children = user.children.filter(role=UserRole.STUDENT)
            from schools.models import Classroom
            child_classrooms = Classroom.objects.filter(
                classroom_users__user__in=children
            ).distinct()
            queryset = queryset.filter(subject_group__classroom__in=child_classrooms)
        # Superadmins can see all attendance (default queryset)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(taken_by=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='student-history')
    def student_history(self, request):
        """Get attendance history for a specific student"""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Check permissions and build queryset depending on role
        if user.role == UserRole.STUDENT:
            if str(user.id) != str(student_id):
                return Response(
                    {'error': 'You can only view your own attendance history'},
                    status=status.HTTP_403_FORBIDDEN
                )
            records = AttendanceRecord.objects.filter(
                student_id=student_id
            ).select_related(
                'attendance__subject_group__course',
                'attendance__subject_group__classroom',
                'attendance__taken_by'
            )
        elif user.role == UserRole.PARENT:
            # Parents can only see attendance for their own children
            if not user.children.filter(id=student_id, role=UserRole.STUDENT).exists():
                return Response(
                    {'error': 'You can only view attendance for your own children'},
                    status=status.HTTP_403_FORBIDDEN
                )
            records = AttendanceRecord.objects.filter(
                student_id=student_id
            ).select_related(
                'attendance__subject_group__course',
                'attendance__subject_group__classroom',
                'attendance__taken_by'
            )
        elif user.role == UserRole.TEACHER:
            # Teachers can only see students from their subject groups
            teacher_subject_groups = user.subject_groups.values_list('id', flat=True)
            records = AttendanceRecord.objects.filter(
                student_id=student_id,
                attendance__subject_group__in=teacher_subject_groups
            ).select_related(
                'attendance__subject_group__course',
                'attendance__subject_group__classroom',
                'attendance__taken_by'
            )
        elif user.role == UserRole.SCHOOLADMIN:
            # School admins can see students from their school
            records = AttendanceRecord.objects.filter(
                student_id=student_id,
                attendance__subject_group__classroom__school=user.school
            ).select_related(
                'attendance__subject_group__course',
                'attendance__subject_group__classroom',
                'attendance__taken_by'
            )
        else:
            # Superadmin can see all
            records = AttendanceRecord.objects.filter(
                student_id=student_id
            ).select_related(
                'attendance__subject_group__course',
                'attendance__subject_group__classroom',
                'attendance__taken_by'
            )
        
        serializer = StudentAttendanceHistorySerializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics(self, request):
        """Get attendance metrics for different user roles"""
        user = request.user
        subject_group_id = request.query_params.get('subject_group_id')
        
        if user.role == UserRole.STUDENT:
            return Response({'error': 'Students cannot access metrics'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Build base queryset based on user role
        if user.role == UserRole.TEACHER:
            queryset = Attendance.objects.filter(subject_group__teacher=user)
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = Attendance.objects.filter(subject_group__classroom__school=user.school)
        else:  # Superadmin
            queryset = Attendance.objects.all()
        
        # Filter by subject group if specified
        if subject_group_id:
            queryset = queryset.filter(subject_group_id=subject_group_id)
        
        # Calculate metrics
        metrics_data = []
        
        if subject_group_id:
            # Single subject group metrics
            attendance = queryset.first()
            if attendance:
                metrics_data.append({
                    'subject_group_name': str(attendance.subject_group),
                    'classroom_name': str(attendance.subject_group.classroom),
                    'course_name': attendance.subject_group.course.name,
                    'total_sessions': queryset.count(),
                    'present_count': sum(a.present_count for a in queryset),
                    'excused_count': sum(a.excused_count for a in queryset),
                    'not_present_count': sum(a.not_present_count for a in queryset),
                    'attendance_percentage': round(
                        sum(a.attendance_percentage for a in queryset) / queryset.count() if queryset.count() > 0 else 0, 2
                    )
                })
        else:
            # Multiple subject groups metrics
            subject_groups = queryset.values('subject_group').distinct()
            
            for sg_data in subject_groups:
                sg_id = sg_data['subject_group']
                sg_attendances = queryset.filter(subject_group_id=sg_id)
                
                if sg_attendances.exists():
                    first_attendance = sg_attendances.first()
                    metrics_data.append({
                        'subject_group_name': str(first_attendance.subject_group),
                        'classroom_name': str(first_attendance.subject_group.classroom),
                        'course_name': first_attendance.subject_group.course.name,
                        'total_sessions': sg_attendances.count(),
                        'present_count': sum(a.present_count for a in sg_attendances),
                        'excused_count': sum(a.excused_count for a in sg_attendances),
                        'not_present_count': sum(a.not_present_count for a in sg_attendances),
                        'attendance_percentage': round(
                            sum(a.attendance_percentage for a in sg_attendances) / sg_attendances.count() if sg_attendances.count() > 0 else 0, 2
                        )
                    })
        
        serializer = AttendanceMetricsSerializer(metrics_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='mark-attendance')
    def mark_attendance(self, request, pk=None):
        """Mark attendance for all students in a subject group"""
        attendance = self.get_object()
        records_data = request.data.get('records', [])
        
        # Clear existing records
        attendance.records.all().delete()
        
        # Create new records
        for record_data in records_data:
            AttendanceRecord.objects.create(
                attendance=attendance,
                student_id=record_data['student_id'],
                status=record_data['status'],
                notes=record_data.get('notes', '')
            )
        
        serializer = AttendanceSerializer(attendance, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='subject-group-students')
    def subject_group_students(self, request):
        """Get students for a subject group to mark attendance"""
        subject_group_id = request.query_params.get('subject_group_id')
        if not subject_group_id:
            return Response({'error': 'subject_group_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from courses.models import SubjectGroup
            subject_group = SubjectGroup.objects.get(id=subject_group_id)
        except SubjectGroup.DoesNotExist:
            return Response({'error': 'Subject group not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        user = request.user
        if user.role == UserRole.TEACHER and subject_group.teacher != user:
            return Response({'error': 'You can only view students for your own subject groups'}, 
                          status=status.HTTP_403_FORBIDDEN)
        elif user.role == UserRole.SCHOOLADMIN and subject_group.classroom.school != user.school:
            return Response({'error': 'You can only view students from your school'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get students in the classroom
        students = subject_group.classroom.classroom_users.filter(
            user__role=UserRole.STUDENT
        ).select_related('user').values(
            'user__id', 'user__username', 'user__first_name', 'user__last_name', 'user__email'
        )
        
        return Response(list(students))



from datetime import date, timedelta


def academic_year_end_for(reference_date: date) -> date:
	# Return May 25 for the academic year containing reference_date (Sep 1 to May 25)
	if reference_date.month >= 9:
		start_year = reference_date.year
	else:
		start_year = reference_date.year - 1
	return date(start_year + 1, 5, 25)


from .serializers import RecurringEventCreateSerializer


class EventViewSet(viewsets.ModelViewSet):
	queryset = Event.objects.select_related(
		'school', 'subject_group__course', 'subject_group__classroom__school', 'course_section__subject_group__course', 'created_by'
	).prefetch_related('target_users').all()
	serializer_class = EventSerializer
	permission_classes = [RoleBasedPermission]
	filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
	filterset_fields = ['type', 'school', 'subject_group', 'course_section', 'target_audience']
	search_fields = ['title', 'description']
	ordering_fields = ['start_at', 'end_at', 'title']
	ordering = ['start_at', 'id']
	
	def get_queryset(self):
		queryset = super().get_queryset()
		user = self.request.user
		
		if user.role == UserRole.STUDENT:
			student_school = user.school
			student_subject_groups = user.classroom_users.values_list('classroom__subject_groups', flat=True)
			queryset = queryset.filter(
				Q(school=student_school, target_audience='all') |
				Q(subject_group__in=student_subject_groups) |
				Q(target_users=user)
			)
		elif user.role == UserRole.TEACHER:
			teacher_school = user.school
			teacher_subject_groups = user.subject_groups.values_list('id', flat=True)
			queryset = queryset.filter(
				Q(school=teacher_school) & (Q(target_audience='all') | Q(target_audience='teachers')) |
				Q(subject_group__in=teacher_subject_groups) |
				Q(target_users=user)
			)
		elif user.role == UserRole.SCHOOLADMIN:
			queryset = queryset.filter(school=user.school)
		# Superadmin: all
		
		start_date = self.request.query_params.get('start_date')
		end_date = self.request.query_params.get('end_date')
		if start_date:
			queryset = queryset.filter(start_at__date__gte=start_date)
		if end_date:
			queryset = queryset.filter(start_at__date__lte=end_date)
		
		return queryset.distinct()
	
	def get_permissions(self):
		if self.action in ['create', 'update', 'partial_update', 'destroy']:
			return [IsSchoolAdminOrSuperAdmin()]
		return [RoleBasedPermission()]

	def perform_create(self, serializer):
		serializer.save(created_by=self.request.user)

	@action(detail=False, methods=['post'], url_path='create-recurring')
	def create_recurring(self, request):
		serializer = RecurringEventCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		
		title = data['title']
		description = data.get('description', '')
		location = data.get('location', '')
		is_all_day = data.get('is_all_day', False)
		
		start_date_val: date = data['start_date']
		end_date_val: date | None = data.get('end_date')
		if not end_date_val:
			end_date_val = academic_year_end_for(start_date_val)
		
		weekdays = set(data['weekdays'])  # 0=Mon ... 6=Sun
		start_time = data['start_time']
		end_time = data['end_time']
		
		subject_group_id = data.get('subject_group')
		course_section_id = data.get('course_section')
		school_id = data.get('school')
		
		# Build date range occurrences
		current = start_date_val
		events_to_create = []
		while current <= end_date_val:
			if current.weekday() in weekdays:
				start_at_dt = datetime.combine(current, start_time, tzinfo=timezone.get_current_timezone())
				end_at_dt = datetime.combine(current, end_time, tzinfo=timezone.get_current_timezone())
				events_to_create.append(Event(
					title=title,
					description=description,
					type=EventType.LESSON,
					start_at=start_at_dt,
					end_at=end_at_dt,
					is_all_day=is_all_day,
					location=location,
					school_id=school_id,
					subject_group_id=subject_group_id,
					course_section_id=course_section_id,
					created_by=request.user,
				))
			current += timedelta(days=1)
		
		created = Event.objects.bulk_create(events_to_create)
		return Response({'created': len(created)}, status=status.HTTP_201_CREATED)