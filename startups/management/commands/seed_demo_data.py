from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from announcements.models import Announcement
from operations.models import Booking, Event, Resource
from startups.models import Idea, Meeting, Milestone, Phase, Startup
from users.models import Profile

User = get_user_model()


def _set_role(user, role):
    if hasattr(user, "profile"):
        user.profile.role = role
        user.profile.save()
    else:
        Profile.objects.create(user=user, role=role)


class Command(BaseCommand):
    help = "Seeds demo data for all roles: admin, mentor, founders, investor, plus sample startups/ideas/meetings/announcements/events/resources/bookings."

    def handle(self, *args, **options):
        # --- Phases ---
        phases_data = [
            {"name": "Ideation", "order": 1},
            {"name": "Validation", "order": 2},
            {"name": "MVP", "order": 3},
            {"name": "Growth", "order": 4},
            {"name": "Maturity", "order": 5},
        ]
        phases = {}
        for data in phases_data:
            phase, _ = Phase.objects.get_or_create(name=data["name"], defaults={"order": data["order"]})
            phases[data["name"]] = phase
        self.stdout.write(self.style.SUCCESS("Phases ready."))

        # --- Users ---
        def get_or_create_user(username, email, password, role, is_staff=False, is_superuser=False):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_staff": is_staff, "is_superuser": is_superuser},
            )
            if created:
                user.set_password(password)
                user.save()
            _set_role(user, role)
            return user

        admin_user = get_or_create_user(
            "admin", "admin@aau.edu.et", "AdminPass123!", "admin", is_staff=True, is_superuser=True
        )
        profile_admin = get_or_create_user("commsadmin", "comms@aau.edu.et", "CommsPass123!", "admin")
        mentor = get_or_create_user("mentor_alem", "mentor@aau.edu.et", "MentorPass123!", "mentor")
        founder1 = get_or_create_user("founder_selam", "selam@aau.edu.et", "FounderPass123!", "student")
        founder2 = get_or_create_user("founder_biniam", "biniam@aau.edu.et", "FounderPass123!", "student")
        investor = get_or_create_user("investor_demo", "investor@aau.edu.et", "InvestorPass123!", "investor")

        self.stdout.write(self.style.SUCCESS("Users ready:"))
        for u, label in [
            (admin_user, "Django admin (staff/superuser)"),
            (profile_admin, "Profile-role admin (announcements only)"),
            (mentor, "Mentor"),
            (founder1, "Founder"),
            (founder2, "Founder"),
            (investor, "Investor"),
        ]:
            self.stdout.write(f"  {label}: username={u.username}")

        # --- Startups ---
        startup1, _ = Startup.objects.get_or_create(
            name="EthioPay Solutions",
            defaults={
                "description": "Mobile payment platform for rural Ethiopia.",
                "founder": founder1,
                "current_phase": phases["MVP"],
            },
        )
        startup2, _ = Startup.objects.get_or_create(
            name="AgriTech Ethiopia",
            defaults={
                "description": "Precision agriculture tools for smallholder farmers.",
                "founder": founder2,
                "current_phase": phases["Validation"],
            },
        )
        self.stdout.write(self.style.SUCCESS("Startups ready."))

        # --- Ideas (pending + approved) ---
        Idea.objects.get_or_create(
            title="EduConnect",
            defaults={
                "description": "Peer-to-peer tutoring marketplace for university students.",
                "owner": founder2,
                "status": "pending",
                "problem_statement": "Students struggle to find affordable, reliable tutors.",
                "solution": "A marketplace connecting students with vetted peer tutors.",
            },
        )
        Idea.objects.get_or_create(
            title="EthioPay Solutions",
            defaults={
                "description": "Mobile payment platform for rural Ethiopia.",
                "owner": founder1,
                "status": "approved",
                "startup": startup1,
            },
        )
        self.stdout.write(self.style.SUCCESS("Ideas ready."))

        # --- Milestones ---
        Milestone.objects.get_or_create(
            startup=startup1,
            phase=phases["MVP"],
            title="Launch pilot in 2 rural regions",
            defaults={"due_date": timezone.now().date() + timedelta(days=30)},
        )
        Milestone.objects.get_or_create(
            startup=startup2,
            phase=phases["Validation"],
            title="Complete 20 farmer interviews",
            defaults={"due_date": timezone.now().date() + timedelta(days=14), "completed": True},
        )
        self.stdout.write(self.style.SUCCESS("Milestones ready."))

        # --- Meetings ---
        Meeting.objects.get_or_create(
            startup=startup1,
            mentor=mentor,
            title="Weekly Progress Review",
            defaults={
                "description": "Discuss milestones and blockers.",
                "link": "https://meet.google.com/demo-link",
            },
        )
        self.stdout.write(self.style.SUCCESS("Meetings ready."))

        # --- Announcements ---
        Announcement.objects.get_or_create(
            title="Welcome to the AAU Startups Portal",
            defaults={
                "content": "This portal is now live. Submit your idea to get started!",
                "type": "announcement",
                "is_pinned": True,
                "author": admin_user.username,
            },
        )
        Announcement.objects.get_or_create(
            title="Pitch Night — Applications Open",
            defaults={
                "content": "Apply now for a chance to pitch in front of local investors.",
                "type": "important",
                "author": profile_admin.username,
            },
        )
        self.stdout.write(self.style.SUCCESS("Announcements ready."))

        # --- Events / Resources / Bookings ---
        event, _ = Event.objects.get_or_create(
            title="Pitch Night",
            defaults={
                "description": "Monthly pitch competition for AAU startups.",
                "event_date": timezone.now() + timedelta(days=14),
                "location": "AAU Innovation Center, Main Hall",
            },
        )
        resource, _ = Resource.objects.get_or_create(
            name="Innovation Lab",
            defaults={
                "description": "Fully equipped workspace with high-speed internet.",
                "type": "workspace",
                "capacity": 20,
                "availability": "available",
            },
        )
        Booking.objects.get_or_create(
            resource=resource,
            user=founder1,
            defaults={
                "purpose": "Team sprint planning session",
                "start_time": timezone.now() + timedelta(days=2),
                "end_time": timezone.now() + timedelta(days=2, hours=2),
                "status": "pending",
            },
        )
        self.stdout.write(self.style.SUCCESS("Events/Resources/Bookings ready."))

        self.stdout.write(self.style.SUCCESS("\nDemo data seeding complete."))
