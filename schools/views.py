import re
import string
from django.db import transaction
from django.utils.text import slugify
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import School, Classroom, ClassroomUser
from .serializers import (
    SchoolSerializer,
    ClassroomSerializer,
    ClassroomDetailSerializer,
    ClassroomUserSerializer,
    BulkClassroomUserSerializer
)
from .permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from users.models import User, UserRole


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'city', 'country']
    ordering_fields = ['name', 'city']
    ordering = ['name']

    @action(detail=True, methods=['post'], url_path='import-teachers-excel')
    def import_teachers_excel(self, request, pk=None):
        """
        Import teachers from Excel file.
        Expected columns: first_name, last_name, email (optional), phone_number (optional), username (optional)
        """
        school = self.get_object()

        # Check if file is provided
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Excel file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        excel_file = request.FILES['file']
        default_password = request.data.get('default_password', None)

        # Validate file extension
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'File must be an Excel file (.xlsx or .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import openpyxl
        except ImportError:
            return Response(
                {'error': 'openpyxl library is required. Install it with: pip install openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Load workbook
            workbook = openpyxl.load_workbook(excel_file, read_only=True)
            worksheet = workbook.active

            # Find header row
            headers = {}
            header_row = None
            for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
                if row and any(cell and str(cell).strip().lower() in ['first_name', 'last_name'] for cell in row):
                    # Found header row
                    for col_idx, cell_value in enumerate(row, start=1):
                        if cell_value:
                            header_key = str(cell_value).strip().lower()
                            headers[header_key] = col_idx
                    header_row = row_idx
                    break

            if not headers:
                return Response(
                    {'error': 'Could not find header row with required columns: first_name, last_name'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate required columns
            required_columns = ['first_name', 'last_name']
            missing_columns = [
                col for col in required_columns if col not in headers]
            if missing_columns:
                return Response(
                    {'error': f'Missing required columns: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Default password for all created users
            if not (default_password and str(default_password).strip()):
                default_password = 'qwerty123'

            # Process rows
            results = {
                'created_teachers': 0,
                'errors': [],
                'default_password': default_password
            }

            with transaction.atomic():
                # Process data rows
                for row_idx, row in enumerate(worksheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                    # Skip empty rows
                    if not any(cell for cell in row):
                        continue

                    # Extract data
                    first_name = str(row[headers['first_name'] - 1]).strip(
                    ) if headers['first_name'] <= len(row) and row[headers['first_name'] - 1] else None
                    last_name = str(row[headers['last_name'] - 1]).strip(
                    ) if headers['last_name'] <= len(row) and row[headers['last_name'] - 1] else None
                    email = str(row[headers['email'] - 1]).strip() if 'email' in headers and headers['email'] <= len(
                        row) and row[headers['email'] - 1] else None
                    phone_number = str(row[headers['phone_number'] - 1]).strip(
                    ) if 'phone_number' in headers and headers['phone_number'] <= len(row) and row[headers['phone_number'] - 1] else None
                    username = str(row[headers['username'] - 1]).strip(
                    ) if 'username' in headers and headers['username'] <= len(row) and row[headers['username'] - 1] else None

                    # Validate required fields
                    if not first_name or not last_name:
                        results['errors'].append({
                            'row': row_idx,
                            'error': 'Missing required fields: first_name or last_name'
                        })
                        continue

                    # Generate username if not provided
                    if not username:
                        username = self._generate_username(
                            first_name, last_name, school)

                    # Generate email if not provided
                    if not email:
                        email = f"{username}@{school.name.lower().replace(' ', '')}.local"

                    # Check if user already exists
                    existing_user = User.objects.filter(
                        username=username).first()
                    if existing_user:
                        results['errors'].append({
                            'row': row_idx,
                            'error': f'User with username {username} already exists'
                        })
                        continue

                    # Check email uniqueness
                    if User.objects.filter(email=email).exists():
                        # Generate unique email
                        counter = 1
                        base_email = email
                        while User.objects.filter(email=email).exists():
                            email = f"{base_email.split('@')[0]}{counter}@{base_email.split('@')[1]}"
                            counter += 1

                    # Create user
                    try:
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=default_password,
                            role=UserRole.TEACHER,
                            first_name=first_name,
                            last_name=last_name,
                            phone_number=phone_number if phone_number else None,
                            school=school,
                            is_active=True
                        )

                        results['created_teachers'] += 1
                    except Exception as e:
                        results['errors'].append({
                            'row': row_idx,
                            'error': f'Failed to create user: {str(e)}'
                        })
                        continue

            # Format response
            response_data = {
                'success': True,
                'message': 'Import completed',
                'summary': {
                    'total_teachers': results['created_teachers'],
                    'errors_count': len(results['errors'])
                },
                'default_password': results['default_password'],
                'errors': results['errors'][:50]  # Limit to first 50 errors
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Error processing file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='import-students-excel')
    def import_students_excel(self, request, pk=None):
        """
        Import students from Excel file.
        Expected columns: class_name, first_name, last_name, email (optional), phone_number (optional),
        parent_username (optional, per row). If parent_username column is missing/empty, form field is used.
        Optional form field: parent_username — default for rows without parent_username in Excel.
        Query/body: preview=1 — only parse and return counts (no DB writes).
        """
        school = self.get_object()
        is_preview = request.data.get('preview') in ('1', 'true', True)

        # Check if file is provided
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Excel file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        excel_file = request.FILES['file']
        default_password = request.data.get('default_password', None)
        default_parent_username = (request.data.get('parent_username') or '').strip() or None

        # Validate file extension
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'File must be an Excel file (.xlsx or .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import openpyxl
        except ImportError:
            return Response(
                {'error': 'openpyxl library is required. Install it with: pip install openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Load workbook
            workbook = openpyxl.load_workbook(excel_file, read_only=True)
            worksheet = workbook.active

            # Find header row
            headers = {}
            header_row = None
            for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
                if row and any(cell and str(cell).strip().lower() in ['class_name', 'first_name', 'last_name'] for cell in row):
                    # Found header row
                    for col_idx, cell_value in enumerate(row, start=1):
                        if cell_value:
                            header_key = str(cell_value).strip().lower()
                            headers[header_key] = col_idx
                    header_row = row_idx
                    break

            if not headers:
                return Response(
                    {'error': 'Could not find header row with required columns: class_name, first_name, last_name'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate required columns
            required_columns = ['class_name', 'first_name', 'last_name']
            missing_columns = [
                col for col in required_columns if col not in headers]
            if missing_columns:
                return Response(
                    {'error': f'Missing required columns: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Per-row parent: use column parent_username or form default
            def row_parent_username(row, row_len):
                if 'parent_username' in headers and headers['parent_username'] <= row_len and row[headers['parent_username'] - 1]:
                    return str(row[headers['parent_username'] - 1]).strip() or default_parent_username
                return default_parent_username

            # Preview: parse only, return counts (no DB writes)
            if is_preview:
                preview_rows = []
                students_new = 0
                students_existing = 0
                parent_usernames_seen = set()
                parents_new_count = 0
                parents_existing_count = 0
                preview_errors = []
                for row_idx, row in enumerate(worksheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                    if not any(cell for cell in row):
                        continue
                    class_name = str(row[headers['class_name'] - 1]).strip() if headers['class_name'] <= len(row) and row[headers['class_name'] - 1] else None
                    first_name = str(row[headers['first_name'] - 1]).strip() if headers['first_name'] <= len(row) and row[headers['first_name'] - 1] else None
                    last_name = str(row[headers['last_name'] - 1]).strip() if headers['last_name'] <= len(row) and row[headers['last_name'] - 1] else None
                    if not class_name or not first_name or not last_name:
                        preview_errors.append({'row': row_idx, 'error': 'Missing class_name, first_name or last_name'})
                        continue
                    grade, letter = self._parse_class_name(class_name)
                    if not grade or not letter:
                        preview_errors.append({'row': row_idx, 'error': f'Invalid class_name: {class_name}'})
                        continue
                    username = self._generate_username(first_name, last_name, school)
                    student_exists = User.objects.filter(username=username).first() is not None
                    if student_exists:
                        students_existing += 1
                    else:
                        students_new += 1
                    p_username = row_parent_username(row, len(row))
                    parent_status = None
                    if p_username:
                        if p_username not in parent_usernames_seen:
                            parent_usernames_seen.add(p_username)
                            par = User.objects.filter(username=p_username, role=UserRole.PARENT).first()
                            if par:
                                parents_existing_count += 1
                                parent_status = 'existing'
                            elif User.objects.filter(username=p_username).exists():
                                parent_status = 'exists_not_parent'
                            else:
                                parents_new_count += 1
                                parent_status = 'new'
                        else:
                            par = User.objects.filter(username=p_username, role=UserRole.PARENT).first()
                            parent_status = 'existing' if par else 'new'
                    preview_rows.append({
                        'row': row_idx,
                        'class_name': class_name,
                        'first_name': first_name,
                        'last_name': last_name,
                        'student_status': 'existing' if student_exists else 'new',
                        'parent_username': p_username or None,
                        'parent_status': parent_status,
                    })
                return Response({
                    'preview': True,
                    'summary': {
                        'students_new': students_new,
                        'students_existing': students_existing,
                        'parents_new': parents_new_count,
                        'parents_existing': parents_existing_count,
                        'rows_count': len(preview_rows),
                        'errors_count': len(preview_errors),
                    },
                    'rows': preview_rows[:100],
                    'errors': preview_errors[:50],
                }, status=status.HTTP_200_OK)

            # Default password for all created students and new parents
            if not (default_password and str(default_password).strip()):
                default_password = 'qwerty123'

            # Cache: username -> parent User (for per-row parent_username)
            parent_cache = {}
            created_parent_passwords = {}

            def get_or_create_parent(p_username):
                if not p_username:
                    return None, None
                if p_username in parent_cache:
                    return parent_cache[p_username], created_parent_passwords.get(p_username)
                par = User.objects.filter(username=p_username, role=UserRole.PARENT).first()
                if par:
                    parent_cache[p_username] = par
                    return par, None
                existing = User.objects.filter(username=p_username).first()
                if existing:
                    return None, 'not_parent'  # signal error
                pwd = default_password
                parent_email = f'{p_username}@parent.local'
                n = 1
                while User.objects.filter(email=parent_email).exists():
                    parent_email = f'{p_username}{n}@parent.local'
                    n += 1
                par = User.objects.create_user(
                    username=p_username, email=parent_email, password=pwd,
                    role=UserRole.PARENT, first_name='', last_name='', is_active=True
                )
                parent_cache[p_username] = par
                created_parent_passwords[p_username] = pwd
                return par, pwd

            # Process rows
            results = {
                'created_classrooms': {},
                'created_students': {},
                'errors': [],
                'default_password': default_password
            }

            with transaction.atomic():
                # Process data rows
                for row_idx, row in enumerate(worksheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                    # Skip empty rows
                    if not any(cell for cell in row):
                        continue

                    # Extract data
                    class_name = str(row[headers['class_name'] - 1]).strip(
                    ) if headers['class_name'] <= len(row) and row[headers['class_name'] - 1] else None
                    first_name = str(row[headers['first_name'] - 1]).strip(
                    ) if headers['first_name'] <= len(row) and row[headers['first_name'] - 1] else None
                    last_name = str(row[headers['last_name'] - 1]).strip(
                    ) if headers['last_name'] <= len(row) and row[headers['last_name'] - 1] else None
                    email = str(row[headers['email'] - 1]).strip() if 'email' in headers and headers['email'] <= len(
                        row) and row[headers['email'] - 1] else None
                    phone_number = str(row[headers['phone_number'] - 1]).strip(
                    ) if 'phone_number' in headers and headers['phone_number'] <= len(row) and row[headers['phone_number'] - 1] else None
                    row_parent = row_parent_username(row, len(row))

                    # Validate required fields
                    if not class_name or not first_name or not last_name:
                        results['errors'].append({
                            'row': row_idx,
                            'error': 'Missing required fields: class_name, first_name, or last_name'
                        })
                        continue

                    # Parse class_name to extract grade and letter
                    grade, letter = self._parse_class_name(class_name)
                    if not grade or not letter:
                        results['errors'].append({
                            'row': row_idx,
                            'error': f'Invalid class_name format: {class_name}. Expected format: "1A", "2Б", etc.'
                        })
                        continue

                    # Get or create classroom
                    classroom, created = Classroom.objects.get_or_create(
                        school=school,
                        grade=grade,
                        letter=letter,
                        # Default language, can be made configurable
                        defaults={'language': 'ru'}
                    )

                    if created:
                        if class_name not in results['created_classrooms']:
                            results['created_classrooms'][class_name] = 0
                    else:
                        if class_name not in results['created_classrooms']:
                            results['created_classrooms'][class_name] = 0

                    # Generate username if not provided
                    username = None
                    if 'username' in headers and headers['username'] <= len(row) and row[headers['username'] - 1]:
                        username = str(row[headers['username'] - 1]).strip()

                    if not username:
                        username = self._generate_username(
                            first_name, last_name, school)

                    # Generate email if not provided
                    if not email:
                        email = f"{username}@{school.name.lower().replace(' ', '')}.local"

                    # Check if user already exists
                    existing_user = User.objects.filter(
                        username=username).first()
                    if existing_user:
                        # User exists, check if already in this classroom
                        existing_classroom_user = ClassroomUser.objects.filter(
                            classroom=classroom,
                            user=existing_user
                        ).first()
                        if existing_classroom_user:
                            results['errors'].append({
                                'row': row_idx,
                                'error': f'Student {first_name} {last_name} is already in classroom {class_name}'
                            })
                            continue
                        else:
                            # Add existing user to classroom
                            ClassroomUser.objects.create(
                                classroom=classroom, user=existing_user)
                            if row_parent:
                                par_user, _ = get_or_create_parent(row_parent)
                                if par_user == None and _ == 'not_parent':
                                    results['errors'].append({
                                        'row': row_idx,
                                        'error': f'User "{row_parent}" exists but is not a parent'
                                    })
                                elif par_user and existing_user not in par_user.children.all():
                                    par_user.children.add(existing_user)
                            results['created_students'][class_name] = results['created_students'].get(
                                class_name, 0) + 1
                            continue

                    # Check email uniqueness
                    if User.objects.filter(email=email).exists():
                        # Generate unique email
                        counter = 1
                        base_email = email
                        while User.objects.filter(email=email).exists():
                            email = f"{base_email.split('@')[0]}{counter}@{base_email.split('@')[1]}"
                            counter += 1

                    # Create user
                    try:
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=default_password,
                            role=UserRole.STUDENT,
                            first_name=first_name,
                            last_name=last_name,
                            phone_number=phone_number if phone_number else None,
                            school=school,
                            is_active=True
                        )

                        # Create classroom user relationship
                        ClassroomUser.objects.create(
                            classroom=classroom, user=user)
                        if row_parent:
                            par_user, _ = get_or_create_parent(row_parent)
                            if par_user is None and _ == 'not_parent':
                                results['errors'].append({
                                    'row': row_idx,
                                    'error': f'User "{row_parent}" exists but is not a parent'
                                })
                            elif par_user:
                                par_user.children.add(user)

                        results['created_students'][class_name] = results['created_students'].get(
                            class_name, 0) + 1
                    except Exception as e:
                        results['errors'].append({
                            'row': row_idx,
                            'error': f'Failed to create user: {str(e)}'
                        })
                        continue

            # Format response
            response_data = {
                'success': True,
                'message': 'Import completed',
                'summary': {
                    'total_classrooms': len(results['created_classrooms']),
                    'total_students': sum(results['created_students'].values()),
                    'errors_count': len(results['errors'])
                },
                'classrooms': [
                    {
                        'class_name': class_name,
                        'students_count': count
                    }
                    for class_name, count in results['created_students'].items()
                ],
                'default_password': results['default_password'],
                'errors': results['errors'][:50]  # Limit to first 50 errors
            }
            if created_parent_passwords:
                response_data['created_parents'] = [
                    {'username': uname, 'password': pwd}
                    for uname, pwd in created_parent_passwords.items()
                ]

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Error processing file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_class_name(self, class_name):
        """
        Parse class_name like "1A", "2Б", "11Г" into (grade, letter)
        Returns (grade, letter) or (None, None) if invalid
        """
        if not class_name:
            return None, None

        # Remove whitespace
        class_name = class_name.strip()

        # Try to match pattern: number(s) followed by letter(s)
        match = re.match(r'^(\d+)([A-ZА-ЯЁа-яё]+)$', class_name, re.IGNORECASE)
        if match:
            grade_str = match.group(1)
            letter = match.group(2).upper()

            try:
                grade = int(grade_str)
                if 0 <= grade <= 12:
                    # Take only first letter if multiple letters provided
                    letter = letter[0]
                    return grade, letter
            except ValueError:
                pass

        return None, None

    def _transliterate_cyrillic_to_latin(self, text):
        """
        Transliterate Cyrillic (Russian + Kazakh) text to Latin.
        Supports Kazakh-specific letters: Ә, Ғ, Қ, Ң, Ө, Ұ, Ү, Һ, І
        """
        if not text:
            return ''

        # Transliteration mapping: Cyrillic -> Latin
        translit_map = {
            # Russian letters
            'А': 'A', 'а': 'a',
            'Б': 'B', 'б': 'b',
            'В': 'V', 'в': 'v',
            'Г': 'G', 'г': 'g',
            'Д': 'D', 'д': 'd',
            'Е': 'E', 'е': 'e',
            'Ё': 'Yo', 'ё': 'yo',
            'Ж': 'Zh', 'ж': 'zh',
            'З': 'Z', 'з': 'z',
            'И': 'I', 'и': 'i',
            'Й': 'Y', 'й': 'y',
            'К': 'K', 'к': 'k',
            'Л': 'L', 'л': 'l',
            'М': 'M', 'м': 'm',
            'Н': 'N', 'н': 'n',
            'О': 'O', 'о': 'o',
            'П': 'P', 'п': 'p',
            'Р': 'R', 'р': 'r',
            'С': 'S', 'с': 's',
            'Т': 'T', 'т': 't',
            'У': 'U', 'у': 'u',
            'Ф': 'F', 'ф': 'f',
            'Х': 'Kh', 'х': 'kh',
            'Ц': 'Ts', 'ц': 'ts',
            'Ч': 'Ch', 'ч': 'ch',
            'Ш': 'Sh', 'ш': 'sh',
            'Щ': 'Shch', 'щ': 'shch',
            'Ъ': '', 'ъ': '',  # Hard sign - remove
            'Ы': 'Y', 'ы': 'y',
            'Ь': '', 'ь': '',  # Soft sign - remove
            'Э': 'E', 'э': 'e',
            'Ю': 'Yu', 'ю': 'yu',
            'Я': 'Ya', 'я': 'ya',

            # Kazakh-specific letters
            'Ә': 'A', 'ә': 'a',  # A with diaeresis
            'Ғ': 'Gh', 'ғ': 'gh',  # G with stroke
            'Қ': 'Q', 'қ': 'q',  # K with descender
            'Ң': 'Ng', 'ң': 'ng',  # N with descender
            'Ө': 'O', 'ө': 'o',  # O with diaeresis
            'Ұ': 'U', 'ұ': 'u',  # U with stroke
            'Ү': 'U', 'ү': 'u',  # U with diaeresis
            'Һ': 'H', 'һ': 'h',  # H with descender
            'І': 'I', 'і': 'i',  # I with diaeresis
        }

        result = []
        for char in text:
            if char in translit_map:
                result.append(translit_map[char])
            elif char.isalnum() or char in ['-', '_', '.']:
                # Keep Latin letters, numbers, and common separators
                result.append(char)
            else:
                # Replace other characters with empty string or underscore
                result.append('')

        return ''.join(result)

    def _generate_username(self, first_name, last_name, school):
        """
        Generate unique username from first_name and last_name
        Format: lastname.firstname.number
        Supports Cyrillic (Russian + Kazakh) transliteration to Latin
        """
        # Transliterate Cyrillic to Latin
        last_name_translit = self._transliterate_cyrillic_to_latin(
            last_name).lower() if last_name else 'student'
        first_name_translit = self._transliterate_cyrillic_to_latin(
            first_name).lower() if first_name else 'x'

        # Remove any remaining non-alphanumeric characters except dots and hyphens
        allowed_chars = string.ascii_lowercase + string.digits + '.-'
        last_name_slug = ''.join(
            c for c in last_name_translit if c in allowed_chars)[:15]
        first_name_slug = ''.join(
            c for c in first_name_translit if c in allowed_chars)[:1]

        # Ensure we have valid slugs
        if not last_name_slug:
            last_name_slug = 'student'
        if not first_name_slug:
            first_name_slug = 'x'

        base_username = f"{last_name_slug}.{first_name_slug}"
        username = base_username
        counter = 1

        # Ensure uniqueness
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter:03d}"
            counter += 1

        return username


class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.select_related(
        'school').prefetch_related('classroom_users__user').all()
    serializer_class = ClassroomSerializer
    # Superadmins see и управляют всеми классами,
    # schooladmin — только классами своей школы
    permission_classes = [IsSchoolAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['school', 'grade', 'language']
    search_fields = ['letter', 'school__name']
    ordering_fields = ['grade', 'letter', 'school__name']
    ordering = ['school__name', 'grade', 'letter']

    def get_serializer_class(self):
        # Use detailed serializer for retrieve action (get single classroom)
        if self.action == 'retrieve':
            return ClassroomDetailSerializer
        return ClassroomSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        # Ограничиваем schooladmin только своей школой
        if getattr(user, "role", None) == UserRole.SCHOOLADMIN and user.school_id:
            queryset = queryset.filter(school_id=user.school_id)
        return queryset

    @action(detail=True, methods=['post'], url_path='add-student')
    def add_student(self, request, pk=None):
        """Add a single student to a classroom"""
        classroom = self.get_object()
        student_id = request.data.get('student_id')

        if not student_id:
            return Response(
                {'error': 'student_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if student is already in a classroom
        existing_classroom = ClassroomUser.objects.filter(user=student).first()
        if existing_classroom:
            return Response(
                {'error': f'Student is already in classroom {existing_classroom.classroom}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add student to classroom
        classroom_user = ClassroomUser.objects.create(
            classroom=classroom,
            user=student
        )

        return Response(
            {
                'message': 'Student added successfully',
                'classroom_user_id': classroom_user.id
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='remove-student')
    def remove_student(self, request, pk=None):
        """Remove a single student from a classroom"""
        classroom = self.get_object()
        student_id = request.data.get('student_id')

        if not student_id:
            return Response(
                {'error': 'student_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Find the ClassroomUser entry
            classroom_user = ClassroomUser.objects.get(
                classroom=classroom,
                user_id=student_id
            )
            classroom_user.delete()

            return Response(
                {'message': 'Student removed successfully'},
                status=status.HTTP_200_OK
            )
        except ClassroomUser.DoesNotExist:
            return Response(
                {'error': 'Student is not in this classroom'},
                status=status.HTTP_404_NOT_FOUND
            )


class ClassroomUserViewSet(viewsets.ModelViewSet):
    queryset = ClassroomUser.objects.select_related('classroom', 'user').all()
    serializer_class = ClassroomUserSerializer
    # Управление составом классов: супер‑ и школьные админы
    permission_classes = [IsSchoolAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['classroom', 'user']
    search_fields = ['user__username', 'user__email', 'classroom__letter']
    ordering_fields = ['user__username',
                       'classroom__grade', 'classroom__letter']
    ordering = ['classroom__school__name', 'classroom__grade',
                'classroom__letter', 'user__username']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "role", None) == UserRole.SCHOOLADMIN and user.school_id:
            queryset = queryset.filter(classroom__school_id=user.school_id)
        return queryset

    @action(detail=False, methods=['post'], url_path='bulk-add')
    def bulk_add(self, request):
        """Bulk add users to a classroom"""
        serializer = BulkClassroomUserSerializer(data=request.data)
        if serializer.is_valid():
            classroom_users = serializer.save()
            response_serializer = ClassroomUserSerializer(
                classroom_users, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], url_path='bulk-remove')
    def bulk_remove(self, request):
        """Bulk remove users from a classroom"""
        classroom_id = request.data.get('classroom_id')
        user_ids = request.data.get('user_ids', [])

        if not classroom_id:
            return Response({'error': 'classroom_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = ClassroomUser.objects.filter(
            classroom_id=classroom_id,
            user_id__in=user_ids
        ).delete()

        return Response({'deleted_count': deleted_count}, status=status.HTTP_200_OK)
