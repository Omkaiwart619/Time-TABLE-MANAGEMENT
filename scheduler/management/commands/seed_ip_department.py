"""
Run with: python manage.py seed_ip_department

Loads Industrial & Production Engineering (IPE) department: 2nd, 3rd, and 4th year (3rd/5th/7th semester).
Idempotent - safe to re-run.
Enforces 2-hour minimum duration blocks for all lab subjects.
"""
from django.core.management.base import BaseCommand
from scheduler.models import Department, Batch, Teacher, Room, Subject


class Command(BaseCommand):
    help = 'Seeds data for Industrial & Production Engineering department (Lab hours set to 2 hrs min)'

    def handle(self, *args, **kwargs):
        # ---------------- Department ----------------
        ipe_dept, _ = Department.objects.get_or_create(
            code='IPE', defaults={'name': 'Industrial & Production Engineering'}
        )

        # ---------------- Batches ----------------
        batches_data = [
            (2, 'A'),  # 3rd sem
            (3, 'A'),  # 5th sem
            (4, 'A'),  # 7th sem
        ]
        for year_num, sec in batches_data:
            Batch.objects.get_or_create(department=ipe_dept, year=year_num, section=sec)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(batches_data)} IPE batches exist.'))

        # ---------------- Rooms ----------------
        rooms_data = [
            ("F-09 (IPE)", "classroom"),
            ("F-11 (IPE)", "classroom"),
            ("F-10 (IPE)", "classroom"),
            ("G-10 (IPE)", "classroom"),
            ("IPE Theory of Machines Lab", "lab"),
            ("IPE Mechanics of Materials Lab", "lab"),
            ("IPE Machining and Machine Tool Lab", "lab"),
            ("IPE Modeling & Simulation Lab", "lab"),
            ("IPE CIM Lab", "lab"),
        ]
        for rname, rtype in rooms_data:
            Room.objects.get_or_create(name=rname, defaults={'room_type': rtype})
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(rooms_data)} IPE rooms exist.'))

        # ---------------- Teachers ----------------
        names_and_caps = {
            'Prof. S C Srivastava': 12,
            'Mr. C. P. Dewangan': 12,
            'Dr. S. C. Gajbhiye': 12,
            'Dr. Manish Oraon': 12,
            'Mr. Kawal Lal Kurrey': 12,
            'Mr. Anurag Singh': 12,
            'Dr. Kailash Kumar Borkar': 12,
            'Mrs. Arpita Roychoudhury': 12,
            'Dr. Nitin Kumar Sahu': 12,
            'Dr. Atul Kumar Sahu': 12,
            'Mr. Somnath Singroul': 12,
            'Dr. Parveen Kumar': 12,
            'Dr. Leeladhar Rajput': 12,
            'Mrs. Disha Dewangan': 12,
            'New Faculty': 12,
        }
        for name, cap in names_and_caps.items():
            teacher = Teacher.objects.filter(name=name, department=ipe_dept).first()
            if not teacher:
                Teacher.objects.create(name=name, department=ipe_dept, max_classes_per_week=cap)
            else:
                teacher.max_classes_per_week = cap
                teacher.save()

        self.stdout.write(self.style.SUCCESS(f'Ensured {len(names_and_caps)} IPE teachers exist.'))

        # ---------------- Fetch batch instances ----------------
        b_3rd = Batch.objects.get(department=ipe_dept, year=2, section='A')
        b_5th = Batch.objects.get(department=ipe_dept, year=3, section='A')
        b_7th = Batch.objects.get(department=ipe_dept, year=4, section='A')

        # ---------------- Subjects ----------------
        # (name, teacher_name, classes_per_week, is_lab, room_name, batch)
        subjects_list = [
            # 3rd Semester (Room F-09) -> Total: 22 hrs
            ("Theory of Machines", "Dr. Kailash Kumar Borkar", 3, False, "F-09 (IPE)", b_3rd),
            ("Engineering Thermodynamics", "Mr. Anurag Singh", 3, False, "F-09 (IPE)", b_3rd),
            ("Intro to Industrial Engg / Open Elective", "Dr. Atul Kumar Sahu", 3, False, "F-09 (IPE)", b_3rd),
            ("Material Science and Metallurgy", "Mr. Somnath Singroul", 3, False, "F-09 (IPE)", b_3rd),
            ("Mechanics of Materials", "Dr. Leeladhar Rajput", 3, False, "F-09 (IPE)", b_3rd),
            ("Business Comm. & Professional Skills", "New Faculty", 3, False, "F-09 (IPE)", b_3rd),
            ("Theory of Machines Lab", "Dr. Kailash Kumar Borkar", 2, True, "IPE Theory of Machines Lab", b_3rd),
            ("Mechanics of Materials Lab", "Dr. Leeladhar Rajput", 2, True, "IPE Mechanics of Materials Lab", b_3rd),

            # 5th Semester (Room F-11) -> Total: 21 hrs
            ("Machining and Machine Tool", "Mrs. Arpita Roychoudhury", 3, False, "F-11 (IPE)", b_5th),
            ("Organization Management", "Mr. C. P. Dewangan", 3, False, "F-11 (IPE)", b_5th),
            ("Managerial Economics", "Mr. Anurag Singh", 3, False, "F-11 (IPE)", b_5th),
            ("Lean Manufacturing", "Mr. Somnath Singroul", 3, False, "F-11 (IPE)", b_5th),
            ("Operation Research", "Prof. S C Srivastava", 3, False, "F-11 (IPE)", b_5th),
            ("Machine Design", "Mr. Kawal Lal Kurrey", 2, False, "F-11 (IPE)", b_5th),
            ("Machining and Machine Tool Lab", "Mrs. Arpita Roychoudhury", 2, True, "IPE Machining and Machine Tool Lab", b_5th),
            ("Modeling & Simulation Lab", "Mr. Anurag Singh", 2, True, "IPE Modeling & Simulation Lab", b_5th),

            # 7th Semester (Room F-10) -> Total: 19 hrs
            ("Marketing Management", "Dr. S. C. Gajbhiye", 3, False, "F-10 (IPE)", b_7th),
            ("Advanced Manufacturing Processes", "Dr. Nitin Kumar Sahu", 3, False, "F-10 (IPE)", b_7th),
            ("Quality & Maintenance Management", "Dr. Kailash Kumar Borkar", 3, False, "F-10 (IPE)", b_7th),
            ("Computer Integrated Manufacturing", "Dr. Parveen Kumar", 3, False, "F-10 (IPE)", b_7th),
            ("Production Planning and Control", "Dr. Atul Kumar Sahu", 3, False, "F-10 (IPE)", b_7th),
            ("CIM Lab", "Dr. Parveen Kumar", 2, True, "IPE CIM Lab", b_7th),
            ("Industrial Training Seminar", "Dr. Parveen Kumar", 2, True, "F-10 (IPE)", b_7th),
        ]

        created_count = 0
        updated_count = 0

        for sname, tname, hrs, is_lab, rname, batch in subjects_list:
            # Safe Teacher Lookup / Creation
            teacher = Teacher.objects.filter(name=tname, department=ipe_dept).first()
            if not teacher:
                teacher = Teacher.objects.filter(name=tname).first()
            if not teacher:
                teacher = Teacher.objects.create(name=tname, department=ipe_dept, max_classes_per_week=12)

            # Safe Room Lookup
            room = Room.objects.filter(name=rname).first()

            # Enforce continuous 2-hour minimum lab duration block logic
            final_hrs = 2 if is_lab and hrs < 2 else hrs

            defaults_dict = {
                'department': ipe_dept,
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
            f'Done. {created_count} created, {updated_count} updated out of {len(subjects_list)} total IPE subjects.'
        ))