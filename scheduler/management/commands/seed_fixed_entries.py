"""
Management Command: seed_fixed_entries

Description:
Seeds fixed, non-overwritable timetable entries strictly based on the
'Special & Fixed Academic Classes Summary' specification document across ECE, CSE, IT, EE, and IPE.
"""

import re
from django.core.management.base import BaseCommand
from django.db import transaction
from scheduler.models import (
    Department,
    Batch,
    Subject,
    Teacher,
    Room,
    TimetableEntry,
)

PERIOD_TIME_MAP = {
    1: ("10:00", "11:00"),
    2: ("11:00", "12:00"),
    3: ("12:00", "13:00"),
    4: ("14:00", "15:00"),
    5: ("15:00", "16:00"),
    6: ("16:00", "17:00"),
}


class Command(BaseCommand):
    help = "Seeds fixed timetable entries mapped strictly to the Special & Fixed Academic Classes Data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting fixed entries seeding process..."))

        with transaction.atomic():
            entry_fields = [f.name for f in TimetableEntry._meta.get_fields()]
            has_period_field = "period" in entry_fields
            has_time_fields = "start_time" in entry_fields and "end_time" in entry_fields

            def get_available_teacher(dept, day, period, preferred_name=None):
                booked_teacher_ids = set(TimetableEntry.objects.filter(
                    day=day, period=period
                ).values_list("teacher_id", flat=True))

                # First try the preferred teacher, but ONLY if they are not already booked
                if preferred_name:
                    preferred_teacher = Teacher.objects.filter(
                        name__icontains=preferred_name
                    ).exclude(id__in=booked_teacher_ids).first()
                    
                    if preferred_teacher:
                        return preferred_teacher

                # If preferred teacher is booked (or none specified), find any available teacher in the department
                avail_teacher = (
                    Teacher.objects.filter(department=dept)
                    .exclude(id__in=booked_teacher_ids)
                    .first()
                )
                
                # Ultimate fallback: Any available teacher in the whole college
                if not avail_teacher:
                    avail_teacher = Teacher.objects.exclude(id__in=booked_teacher_ids).first()
                    
                return avail_teacher

            def get_available_room(day, period, room_number_str=None, room_type="classroom"):
                if room_number_str:
                    room = Room.objects.filter(name__icontains=room_number_str).first()
                    if room:
                        return room

                booked_room_ids = TimetableEntry.objects.filter(
                    day=day, period=period, room__isnull=False
                ).values_list("room_id", flat=True)

                avail_room = (
                    Room.objects.filter(room_type=room_type)
                    .exclude(id__in=booked_room_ids)
                    .first()
                )
                if not avail_room:
                    avail_room = Room.objects.exclude(id__in=booked_room_ids).first()
                return avail_room

            fallback_room = Room.objects.first()
            total_seeded = 0

            batches = Batch.objects.select_related("department").all()

            for batch in batches:
                dept = batch.department
                dept_code = dept.code.upper() if dept else ""
                
                # Dynamic Semester Detection
                sem = None
                raw_sem = getattr(batch, "semester", None)
                if raw_sem is not None:
                    try:
                        sem = int(raw_sem)
                    except ValueError:
                        pass
                
                if sem is None:
                    batch_str = str(batch)
                    match = re.search(r'(\d+)', batch_str)
                    if match:
                        sem = int(match.group(1))

                specs = []

                # --- 1st Semester Specs (ECE, CSE, IT, EE) ---
                if sem == 1 or "1" in str(getattr(batch, "name", "")):
                    specs.append({
                        "name": "Mentor-Mentee",
                        "code": f"MM-{dept_code}-{batch.id}",
                        "day": "Friday",
                        "periods": [6],
                        "teacher_hint": None,
                        "room_hint": "F-11" if dept_code == "IT" else ("2" if dept_code == "EE" else None),
                        "is_lab": False,
                    })

                    teacher_hint = None
                    if dept_code == "ECE":
                        teacher_hint = "Chandan"
                    elif dept_code == "CSE":
                        teacher_hint = "Princy"
                    elif dept_code == "IT":
                        teacher_hint = "Ankit"
                    elif dept_code == "EE":
                        teacher_hint = "Chandan"

                    specs.append({
                        "name": "NSS (National Service Scheme)",
                        "code": f"NSS-{dept_code}-{batch.id}",
                        "day": "Friday",
                        "periods": [4, 5],
                        "teacher_hint": teacher_hint,
                        "room_hint": "F-12" if dept_code == "IT" else None,
                        "is_lab": False,
                    })

                # --- 5th Semester Specs ---
                elif sem == 5 or "5" in str(getattr(batch, "name", "")):
                    if dept_code == "ECE":
                        specs.append({
                            "name": "Mini Project-2",
                            "code": f"MP2-ECE-{batch.id}",
                            "day": "Thursday",
                            "periods": [1, 2, 5, 6],
                            "teacher_hint": None,
                            "room_hint": "CR-02",
                            "is_lab": True,
                        })

                # --- 7th Semester Specs ---
                elif sem == 7 or "7" in str(getattr(batch, "name", "")):
                    if dept_code == "ECE":
                        specs.append({
                            "name": "Minor Project",
                            "code": f"MINPROJ-ECE-{batch.id}",
                            "day": "Tuesday",
                            "periods": [1, 2, 5, 6],
                            "teacher_hint": None,
                            "room_hint": "CR-05",
                            "is_lab": True,
                        })
                        specs.append({
                            "name": "Seminar on Industrial Training (SoIT)",
                            "code": f"SOIT-ECE-{batch.id}",
                            "day": "Wednesday",
                            "periods": [5, 6],
                            "teacher_hint": None,
                            "room_hint": "CR-05",
                            "is_lab": False,
                        })
                    elif dept_code == "IPE":
                        specs.append({
                            "name": "Industrial Training Seminar (ITS)",
                            "code": f"ITS-IPE-{batch.id}",
                            "day": "Wednesday",
                            "periods": [4],
                            "teacher_hint": "Parveen",
                            "room_hint": "F-10",
                            "is_lab": False,
                        })

                # --- Execute Seeding ---
                for spec in specs:
                    for p in spec["periods"]:
                        lookup_kwargs = {"batch": batch, "day": spec["day"]}
                        if has_period_field:
                            lookup_kwargs["period"] = p

                        if TimetableEntry.objects.filter(**lookup_kwargs).exists():
                            continue

                        teacher = get_available_teacher(dept, spec["day"], p, spec["teacher_hint"])
                        room = get_available_room(
                            spec["day"], p, spec["room_hint"], "lab" if spec["is_lab"] else "classroom"
                        )

                        if not teacher:
                            continue

                        subject, _ = Subject.objects.get_or_create(
                            code=spec["code"],
                            defaults={
                                "name": spec["name"],
                                "department": dept,
                                "batch": batch,
                                "teacher": teacher,
                                "is_lab": spec["is_lab"],
                                "classes_per_week": 0,
                            },
                        )

                        if subject.classes_per_week != 0:
                            subject.classes_per_week = 0
                            subject.save()

                        entry_kwargs = {
                            "subject": subject,
                            "teacher": teacher,
                            "room": room or fallback_room,
                            "batch": batch,
                            "day": spec["day"],
                            "is_published": True,
                        }

                        if has_period_field:
                            entry_kwargs["period"] = p

                        if has_time_fields:
                            start_t, end_t = PERIOD_TIME_MAP.get(p, ("10:00", "11:00"))
                            entry_kwargs["start_time"] = start_t
                            entry_kwargs["end_time"] = end_t

                        TimetableEntry.objects.create(**entry_kwargs)
                        total_seeded += 1
                        self.stdout.write(
                            f"  + Seeded: [{dept_code}] {batch} - {subject.name} on {spec['day']} P{p}"
                        )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully seeded {total_seeded} special/fixed academic entries!"
                )
            )