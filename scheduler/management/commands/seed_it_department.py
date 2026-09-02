"""
Run with: python manage.py seed_it_department

Loads Information Technology department: 2nd, 3rd, and 4th year (3rd/5th/7th semester).
Idempotent - safe to re-run.
Enforces 2-hour minimum duration blocks for all lab subjects.
"""
from django.core.management.base import BaseCommand
from scheduler.models import Department, Batch, Teacher, Room, Subject


class Command(BaseCommand):
    help = 'Seeds data for Information Technology department (Lab hours set to 2 hrs min)'

    def handle(self, *args, **kwargs):
        # ---------------- Department ----------------
        it_dept, _ = Department.objects.get_or_create(
            code='IT', defaults={'name': 'Information Technology'}
        )

        # ---------------- Batches ----------------
        batches_data = [
            (2, 'A'),  # 3rd sem Sec A
            (2, 'B'),  # 3rd sem Sec B
            (3, 'A'),  # 5th sem Sec A
            (3, 'B'),  # 5th sem Sec B
            (4, 'A'),  # 7th sem
        ]
        for year_num, sec in batches_data:
            Batch.objects.get_or_create(department=it_dept, year=year_num, section=sec)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(batches_data)} IT batches exist.'))

        # ---------------- Rooms ----------------
        rooms_data = [
            ("F-11 (IT)", "classroom"),
            ("F-12 (IT)", "classroom"),
            ("F-6 (IT)", "classroom"),
            ("F-7 (IT)", "classroom"),
            ("G-05 (IT)", "classroom"),
            ("F-10 (IPE)", "classroom"),
            ("IT Programming Lab 1", "lab"),
            ("IT Programming Lab 2", "lab"),
        ]
        for rname, rtype in rooms_data:
            Room.objects.get_or_create(name=rname, defaults={'room_type': rtype})
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(rooms_data)} IT rooms exist.'))

        # ---------------- Teachers ----------------
        names_and_caps = {
            'Dr. C P Dhuri': 12,
            'Dr. Amar Pandey': 12,
            'Dr. Rohit Raja': 12,
            'Dr. Rajesh Mahule': 12,
            'Mr. Suhel Ahmed': 12,
            'Dr. Koteshwar Rao': 12,
            'Dr. Pankaj Chandra': 12,
            'Dr. Abhishek Jain': 12,
            'Dr. Amit Kumar Dewangan': 12,
            'Mr. Anand Prakash Rawal': 12,
            'Mr. Ashish Sharma': 12,
            'Dr. Santosh Soni': 14,
            'Mr. Deepak Netam': 12,
            'Dr. Manoj Gupta': 12,
        }
        for name, cap in names_and_caps.items():
            teacher = Teacher.objects.filter(name=name, department=it_dept).first()
            if not teacher:
                Teacher.objects.create(name=name, department=it_dept, max_classes_per_week=cap)
            else:
                teacher.max_classes_per_week = cap
                teacher.save()

        self.stdout.write(self.style.SUCCESS(f'Ensured {len(names_and_caps)} IT teachers exist.'))

        # ---------------- Fetch batch instances ----------------
        b_3rd_a = Batch.objects.get(department=it_dept, year=2, section='A')
        b_3rd_b = Batch.objects.get(department=it_dept, year=2, section='B')
        b_5th_a = Batch.objects.get(department=it_dept, year=3, section='A')
        b_5th_b = Batch.objects.get(department=it_dept, year=3, section='B')
        b_7th_a = Batch.objects.get(department=it_dept, year=4, section='A')

        # ---------------- Subjects ----------------
        # (name, teacher_name, classes_per_week, is_lab, room_name, batch)
        subjects_list = [
            # 3rd Semester - Sec A (Room F-6)
            ("Mathematics III", "Dr. Amar Pandey", 3, False, "F-6 (IT)", b_3rd_a),
            ("Digital Electronics / COA", "Dr. Rohit Raja", 3, False, "F-6 (IT)", b_3rd_a),
            ("Object Oriented Programming", "Dr. Rajesh Mahule", 3, False, "F-6 (IT)", b_3rd_a),
            ("Data Structures & Algorithms", "Dr. Koteshwar Rao", 3, False, "F-6 (IT)", b_3rd_a),
            ("Data Structures Lab", "Dr. Koteshwar Rao", 2, True, "IT Programming Lab 1", b_3rd_a),
            ("OOP Lab", "Dr. Rajesh Mahule", 2, True, "IT Programming Lab 2", b_3rd_a),

            # 3rd Semester - Sec B (Room F-7)
            ("Mathematics III", "Dr. Amar Pandey", 3, False, "F-7 (IT)", b_3rd_b),
            ("Digital Electronics / COA", "Dr. Rohit Raja", 3, False, "F-7 (IT)", b_3rd_b),
            ("Object Oriented Programming", "Mr. Suhel Ahmed", 3, False, "F-7 (IT)", b_3rd_b),
            ("Data Structures & Algorithms", "Dr. Pankaj Chandra", 3, False, "F-7 (IT)", b_3rd_b),
            ("Data Structures Lab", "Dr. Pankaj Chandra", 2, True, "IT Programming Lab 1", b_3rd_b),
            ("OOP Lab", "Mr. Suhel Ahmed", 2, True, "IT Programming Lab 2", b_3rd_b),

            # 5th Semester - Sec A (Room F-11)
            ("FLAT", "Dr. Amit Kumar Dewangan", 3, False, "F-11 (IT)", b_5th_a),
            ("Machine Learning", "Dr. Abhishek Jain", 3, False, "F-11 (IT)", b_5th_a),
            ("Database Management Systems", "Mr. Anand Prakash Rawal", 3, False, "F-11 (IT)", b_5th_a),
            ("Soft Computing (Elective III)", "Dr. Rohit Raja", 3, False, "F-11 (IT)", b_5th_a),
            ("Wireless Sensor Networks (Elective IV)", "Dr. Santosh Soni", 3, False, "F-11 (IT)", b_5th_a),
            ("DBMS Lab", "Mr. Anand Prakash Rawal", 2, True, "IT Programming Lab 1", b_5th_a),
            ("ML Lab", "Dr. Abhishek Jain", 2, True, "IT Programming Lab 2", b_5th_a),

            # 5th Semester - Sec B (Room F-12)
            ("FLAT", "Dr. Amit Kumar Dewangan", 3, False, "F-12 (IT)", b_5th_b),
            ("Machine Learning", "Dr. Amit Kumar Dewangan", 3, False, "F-12 (IT)", b_5th_b),
            ("Database Management Systems", "Mr. Ashish Sharma", 3, False, "F-12 (IT)", b_5th_b),
            ("Soft Computing (Elective III)", "Dr. Rohit Raja", 3, False, "F-12 (IT)", b_5th_b),
            ("Wireless Sensor Networks (Elective IV)", "Dr. Santosh Soni", 3, False, "F-12 (IT)", b_5th_b),
            ("DBMS Lab", "Mr. Ashish Sharma", 2, True, "IT Programming Lab 1", b_5th_b),
            ("ML Lab", "Dr. Amit Kumar Dewangan", 2, True, "IT Programming Lab 2", b_5th_b),

            # 7th Semester (Room G-05 & F-10)
            ("Cyber Security", "Dr. Santosh Soni", 3, False, "G-05 (IT)", b_7th_a),
            ("Deep Learning", "Mr. Deepak Netam", 3, False, "G-05 (IT)", b_7th_a),
            ("DE-VIII AIoT", "Dr. Amar Pandey", 3, False, "G-05 (IT)", b_7th_a),
            ("DE-VII ECI", "Dr. Santosh Soni", 3, False, "F-10 (IPE)", b_7th_a),
            ("Cyber Security Lab", "Dr. Santosh Soni", 2, True, "IT Programming Lab 1", b_7th_a),
            ("Deep Learning Lab", "Mr. Deepak Netam", 2, True, "IT Programming Lab 2", b_7th_a),
        ]

        created_count = 0
        updated_count = 0

        for sname, tname, hrs, is_lab, rname, batch in subjects_list:
            # Safe teacher lookup across departments
            teacher = Teacher.objects.filter(name=tname, department=it_dept).first()
            if not teacher:
                teacher = Teacher.objects.filter(name=tname).first()
            if not teacher:
                teacher = Teacher.objects.create(name=tname, department=it_dept, max_classes_per_week=12)

            # Safe room lookup
            room = Room.objects.filter(name=rname).first()

            # Enforce continuous 2-hour minimum lab duration block logic
            final_hrs = 2 if is_lab and hrs < 2 else hrs

            defaults_dict = {
                'department': it_dept,
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
            f'Done. {created_count} created, {updated_count} updated out of {len(subjects_list)} total IT subjects.'
        ))