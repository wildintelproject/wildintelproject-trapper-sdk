"""Accounts and the research project that every test instance has (Trapper v1 and v2).

Run inside the app container by ``uv run cli trapper up``: ``python manage.py shell < accounts.py``. It can be
run again: what exists is updated (the passwords are set again), nothing is duplicated. The last line it prints is
``SEED_JSON:{...}``, which the command reads (tokens and the primary key of the research project).
"""
import json

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token

from trapper.apps.research.models import ResearchProject, ResearchProjectRole

PASSWORD = "wildintel-sdk-test"

# username, staff, superuser, role in the research project (1 admin, 2 expert, 3 collaborator)
ACCOUNTS = [
    ("sdktest", True, True, 1),     # the user the SDK tests call the API as
    ("rp_staff", True, True, 1),    # staff: the v2 imports go through the admin
    ("rp_user", False, False, 3),   # an ordinary user
    ("ana", False, False, 2),
    ("luis", False, False, 3),
    ("plainuser", False, False, None),   # in no project
]

User = get_user_model()
tokens = {}
users = {}
for username, staff, superuser, _ in ACCOUNTS:
    user, _ = User.objects.get_or_create(username=username)
    user.email = f"{username}@example.org"
    user.first_name = username.replace("_", " ").title()
    user.is_staff, user.is_superuser, user.is_active = staff, superuser, True
    user.set_password(PASSWORD)
    user.save()
    users[username] = user
    tokens[username] = Token.objects.get_or_create(user=user)[0].key

# the research project: approved, owned by sdktest (the fields that a version does not have are left out)
fields = {f.name for f in ResearchProject._meta.get_fields() if getattr(f, "concrete", False)}
values = {
    "name": "SDK test project",
    "description": "Research project of the SDK test instance.",
    "abstract": "Created by `cli trapper up`.",
    "owner": users["sdktest"],
    "status": True,
    "status_date": timezone.now(),
}
project, _ = ResearchProject.objects.get_or_create(
    acronym="SDKT", defaults={k: v for k, v in values.items() if k in fields}
)
if "status" in fields and project.status is not True:
    project.status = True
    project.save()
for username, _, _, role in ACCOUNTS:
    if role is not None:
        ResearchProjectRole.objects.get_or_create(user=users[username], project=project, defaults={"name": role})

print("SEED_JSON:" + json.dumps({"password": PASSWORD, "tokens": tokens, "research_project": project.pk}))
