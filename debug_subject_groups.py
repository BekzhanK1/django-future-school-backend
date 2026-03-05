import os
import django
import sys

sys.path.append("/home/bekzhan/Code/Personal/future-school/future-school-backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "future_school.settings")
django.setup()

from courses.models import SubjectGroup, Course
from users.models import User

groups = SubjectGroup.objects.all()
for index, g in enumerate(groups[:5]):
    print(f"[{g.id}] Course: {g.course.id if g.course else 'None'}, Teacher: {g.teacher.id if g.teacher else 'None'}")
