"""
Run with: python manage.py seed_day9_civil

Loads Civil Engineering department: 2nd, 3rd, and 4th year (3rd/5th/7th semester).
Idempotent - safe to re-run.
Enforces 2-hour minimum duration blocks for all lab subjects.

KNOWN SIMPLIFICATIONS (flagged, not silently guessed):
1. "Engineering Mathematics" (3rd sem) has no listed teacher in the source data.
   Not added as a Subject below - add it yourself once you identify the teacher.
2. BMC (3rd sem) is shown as jointly taught by Ms. Preeti Singh / Prof. R.K. Choubey
   in the real timetable. Using Prof. R.K. Choubey as the system's single teacher.
3. CACE Lab (5th sem) is jointly taught by Ms. Ayushi Nayak / Dr. Sonal Banchhor
   (batch-split in reality). Using Ms. Ayushi Nayak as the system's single teacher.
"""
from django.core.management.base import BaseCommand
from scheduler.models import Department, Batch, Teacher, Room, Subject


class Command(BaseCommand):
    help = 'Seeds Day 9 data: Civil Engineering department (Lab hours set to 2 hrs min)'

    def handle(self, *args, **kwargs):
        # ---------------- Department ----------------
        civil, _ = Department.objects.get_or_create(code='CIVIL', defaults={'name': 'Civil Engineering'})

        # ---------------- Batches ----------------
        batches_data = [
            (2, 'A'),  # 3rd sem
            (3, 'A'),  # 5th sem
            (4, 'A'),  # 7th sem
        ]
        for year_num, sec in batches_data:
            Batch.objects.get_or_create(department=civil, year=year_num, section=sec)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(batches_data)} Civil batches exist.'))

        # ---------------- Rooms ----------------
        rooms_data = [
            ("G-9", "classroom"),
            ("F-9 (Civil)", "classroom"),
            ("F-10 (Civil)", "classroom"),
            ("Civil Survey Lab", "lab"),
            ("Civil FM Lab", "lab"),
            ("Civil HE Lab", "lab"),
            ("Civil CACE Lab", "lab"),
            ("Civil Structural Detailing Lab", "lab"),
        ]
        for rname, rtype in rooms_data:
            Room.objects.get_or_create(name=rname, defaults={'room_type': rtype})
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(rooms_data)} Civil rooms exist.'))

        # ---------------- Teachers ----------------
        names_and_caps = {
            'Dr. Nikhil K. Verma': 11,
            'Dr. Sonal Banchhor': 6,
            'Dr. Prakhar Modi': 9,
            'Ms. Ayushi Nayak': 15,
            'Dr. Kundan Meshram': 3,
            'Dr. Ashish K. Parashar': 6,
            'Dr. V.V.S.S. Kumar Dadi': 6,
            'Dr. Balbir K. Pandey': 3,
            'Dr. Adheesh K. Vivek': 8,
            'Ms. Preeti Singh': 6,
            'Dr. Bijoli Mondal': 3,
            'Mr. Vinod Kumar': 3,
            'Mr. Rochak Pandey': 5,
            'Prof. R. K. Choubey': 3,
        }
        for name, cap in names_and_caps.items():
            teacher = Teacher.objects.filter(name=name, department=civil).first()
            if not teacher:
                Teacher.objects.create(name=name, department=civil, max_classes_per_week=cap)
            else:
                teacher.max_classes_per_week = cap
                teacher.save()

        self.stdout.write(self.style.SUCCESS(f'Ensured {len(names_and_caps)} Civil teachers exist.'))

        # ---------------- Fetch batch instances ----------------
        b_3rd = Batch.objects.get(department=civil, year=2, section='A')
        b_5th = Batch.objects.get(department=civil, year=3, section='A')
        b_7th = Batch.objects.get(department=civil, year=4, section='A')

        # ---------------- Subjects ----------------
        # (name, teacher_name, classes_per_week, is_lab, room_name, batch)
        subjects_list = [
            # 3rd Semester (Room G-9) - Engineering Mathematics deliberately NOT included, see docstring
            ("Building Materials and Construction", "Prof. R. K. Choubey", 3, False, "G-9", b_3rd),
            ("Geology & Basic / Open Elective", "Mr. Vinod Kumar", 3, False, "G-9", b_3rd),
            ("Surveying & Geomatics", "Mr. Rochak Pandey", 3, False, "G-9", b_3rd),
            ("Survey Lab", "Mr. Rochak Pandey", 2, True, "Civil Survey Lab", b_3rd),
            ("Strength of Materials", "Ms. Ayushi Nayak", 4, False, "G-9", b_3rd),
            ("Fluid Mechanics - I", "Dr. Ashish K. Parashar", 4, False, "G-9", b_3rd),
            ("Fluid Mechanics Lab", "Dr. Prakhar Modi", 2, True, "Civil FM Lab", b_3rd),

            # 5th Semester (Room F-9)
            ("Design of Concrete Structures", "Dr. V.V.S.S. Kumar Dadi", 6, False, "F-9 (Civil)", b_5th),
            ("Environmental Engineering I", "Dr. Bijoli Mondal", 3, False, "F-9 (Civil)", b_5th),
            ("Structural Analysis II", "Ms. Preeti Singh", 3, False, "F-9 (Civil)", b_5th),
            ("Highway Engineering", "Dr. Adheesh K. Vivek", 4, False, "F-9 (Civil)", b_5th),
            ("Highway Engineering Lab", "Dr. Adheesh K. Vivek", 2, True, "Civil HE Lab", b_5th),
            ("Concrete Technology / CPPS", "Dr. Nikhil K. Verma", 3, False, "F-9 (Civil)", b_5th),
            ("Geotechnical Engineering I", "Dr. Balbir K. Pandey", 3, False, "F-9 (Civil)", b_5th),
            ("CACE Lab", "Ms. Ayushi Nayak", 3, True, "Civil CACE Lab", b_5th),

            # 7th Semester (Room F-10)
            ("Construction Engineering & Architecture", "Dr. Nikhil K. Verma", 6, False, "F-10 (Civil)", b_7th),
            ("Pre-Stressed Concrete", "Dr. Sonal Banchhor", 3, False, "F-10 (Civil)", b_7th),
            ("Environmental Engineering / Hydrology", "Dr. Prakhar Modi", 5, False, "F-10 (Civil)", b_7th),
            ("Railways & Airport Engineering", "Dr. Kundan Meshram", 3, False, "F-10 (Civil)", b_7th),
            ("Water Resources Engineering II", "Dr. Ashish K. Parashar", 2, False, "F-10 (Civil)", b_7th),
            ("Structural Detailing Lab", "Ms. Ayushi Nayak", 2, True, "Civil Structural Detailing Lab", b_7th),
        ]

        created_count = 0
        updated_count = 0

        for sname, tname, hrs, is_lab, rname, batch in subjects_list:
            # Safe teacher retrieval/creation
            teacher = Teacher.objects.filter(name=tname, department=civil).first()
            if not teacher:
                teacher = Teacher.objects.filter(name=tname).first()
            if not teacher:
                teacher = Teacher.objects.create(name=tname, department=civil, max_classes_per_week=12)

            # Safe room retrieval
            room = Room.objects.filter(name=rname).first()

            # Enforce continuous 2-hour minimum lab duration block logic
            final_hrs = 2 if is_lab and hrs < 2 else hrs

            defaults_dict = {
                'department': civil,
                'teacher': teacher,
                'classes_per_week': final_hrs,
                'is_lab': is_lab,
            }

            # Map room attribute dynamically based on model definition
            if hasattr(Subject, 'required_room') and room:
                defaults_dict['required_room'] = room
            elif hasattr(Subject, 'room') and room:
                defaults_dict['room'] = room

            obj, created = Subject.objects.update_or_create(
                name=sname,
                batch=batch,
                defaults=defaults_dict
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. {created_count} created, {updated_count} updated out of {len(subjects_list)} total Civil subjects.'
        ))
        self.stdout.write(self.style.WARNING(
            'Reminder: Engineering Mathematics (3rd sem) was NOT added - no teacher was '
            'identified in the source data. Add it manually once confirmed.'
        ))