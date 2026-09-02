"""
Run with: python manage.py seed_day8

Loads Day 8 data (1st, 2nd, 3rd, 4th year CSE + M.Tech) in one safe, repeatable script.
Uses update_or_create to safely populate teachers, rooms, and subjects.
Enforces 2-hour minimum duration blocks for all lab subjects.
"""
from django.core.management.base import BaseCommand
from scheduler.models import Department, Batch, Teacher, Room, Subject


class Command(BaseCommand):
    help = 'Seeds Day 8 data: CSE 1st/2nd/3rd/4th year + M.Tech (Lab hours set to 2 hrs min)'

    def handle(self, *args, **kwargs):
        # Fetch or create CSE department
        cse, _ = Department.objects.get_or_create(code='CSE', defaults={'name': 'Computer Science & Engineering'})

        # ---------------- Update existing teacher caps ----------------
        Teacher.objects.filter(name='Dr. Amar Pandey').update(max_classes_per_week=13)
        Teacher.objects.filter(name='Dr. Manjit Jaiswal').update(max_classes_per_week=14)
        self.stdout.write(self.style.SUCCESS('Updated existing teacher caps.'))

        # ---------------- Batches ----------------
        batches_data = [
            (1, '1'),      # CSE-1 (1st Year)
            (1, '2'),      # CSE-2 (1st Year)
            (2, 'A'),      # 2nd Year
            (3, 'B1'),     # 3rd Year B1
            (3, 'B2'),     # 3rd Year B2
            (4, 'A'),      # 4th Year
            (5, 'MTech-I') # M.Tech 1st Year
        ]
        for year_num, sec in batches_data:
            Batch.objects.get_or_create(department=cse, year=year_num, section=sec)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(batches_data)} CSE batches exist.'))

        # ---------------- Rooms ----------------
        rooms_data = [
            ("F-03", "classroom"),
            ("F13", "lab"),
            ("F26", "lab"),
            ("F-02", "classroom"),
            ("F04-3rdYr-B2", "classroom"),
            ("F27", "lab"),
            ("Mech-Building-CSE7th", "classroom"),
        ]
        for rname, rtype in rooms_data:
            Room.objects.get_or_create(name=rname, defaults={'room_type': rtype})
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(rooms_data)} rooms exist.'))

        # ---------------- Teachers ----------------
        names_and_caps = {
            'Dr. Amar Pandey': 13,
            'Dr. Manjit Jaiswal': 14,
            'Dr. Vinay Kumar': 3,
            'Mr. Suraj Sharma': 11,
            'Mr. Amit Chandanan': 6,
            'Dr. Devendra Kumar Singh': 6,
            'Mr. Nishant Behar': 7,
            'Dr. Princy Matlani': 6,
            'Mr. Manish Shrivastava': 8,
            'Mrs. Nishi Yadav': 6,
            'Dr. Pushpendra Kumar Chandra': 5,
            'Mr. Amit Kumar Baghel': 6,
            'Mrs. Raksha Pandey': 9,
            'Dr. Satish Negi': 7,
            'Dr. Kapil Nagwanshi': 10,
            'Dr. Vaibhav Kant Singh': 6,
            'Dr. Upasana Sinha': 3,
            'Mr. Manjunath Swamy': 3,
            'Dr. Alok Kumar Singh Kushwaha': 3,
        }
        for name, cap in names_and_caps.items():
            teacher = Teacher.objects.filter(name=name, department=cse).first()
            if not teacher:
                Teacher.objects.create(name=name, department=cse, max_classes_per_week=cap)
            else:
                teacher.max_classes_per_week = cap
                teacher.save()

        self.stdout.write(self.style.SUCCESS(f'Ensured {len(names_and_caps)} teachers exist.'))

        # ---------------- Fetch batch instances ----------------
        b_yr1_cse1, _ = Batch.objects.get_or_create(department=cse, year=1, section='1')
        b_yr1_cse2, _ = Batch.objects.get_or_create(department=cse, year=1, section='2')
        b_yr2 = Batch.objects.get(department=cse, year=2, section='A')
        b_yr3_b1 = Batch.objects.get(department=cse, year=3, section='B1')
        b_yr3_b2 = Batch.objects.get(department=cse, year=3, section='B2')
        b_yr4 = Batch.objects.get(department=cse, year=4, section='A')
        b_mtech = Batch.objects.get(department=cse, year=5, section='MTech-I')

        # ---------------- Subjects ----------------
        subjects_list = [
            # 2nd Year -> Total: 20 hrs
            ("Mathematics III", "Dr. Amar Pandey", 3, False, "F-03", b_yr2),
            ("Internet and Web Technology", "Dr. Vinay Kumar", 3, False, "F-03", b_yr2),
            ("Internet of Things", "Mr. Suraj Sharma", 3, False, "F-03", b_yr2),
            ("IoT Lab", "Mr. Suraj Sharma", 2, True, "F13", b_yr2),
            ("Computer Organization & Architecture", "Mr. Amit Chandanan", 2, False, "F-03", b_yr2),
            ("Digital Logic & Design", "Dr. Devendra Kumar Singh", 3, False, "F-03", b_yr2),
            ("IT Workshop", "Mr. Nishant Behar", 4, False, "F-03", b_yr2),
            ("IT Workshop Lab", "Mr. Nishant Behar", 2, True, "F26", b_yr2),

            # 3rd Year - B1 -> Total: 19 hrs
            ("Parallel Computing (B1)", "Dr. Manjit Jaiswal", 4, False, "F-02", b_yr3_b1),
            ("PC Lab (B1)", "Dr. Manjit Jaiswal", 2, True, "F26", b_yr3_b1),
            ("RDBMS (B1)", "Dr. Princy Matlani", 4, False, "F-02", b_yr3_b1),
            ("RDBMS Lab (B1)", "Dr. Princy Matlani", 2, True, "F27", b_yr3_b1),
            ("FLAT (B1)", "Mrs. Nishi Yadav", 3, False, "F-02", b_yr3_b1),
            ("Microprocessor (B1)", "Mr. Amit Kumar Baghel", 3, False, "F-02", b_yr3_b1),
            ("Software Engineering (B1)", "Mrs. Raksha Pandey", 3, False, "F-02", b_yr3_b1),

            # 3rd Year - B2 -> Total: 18 hrs
            ("Parallel Computing (B2)", "Dr. Manjit Jaiswal", 4, False, "F04-3rdYr-B2", b_yr3_b2),
            ("PC Lab (B2)", "Dr. Manjit Jaiswal", 2, True, "F26", b_yr3_b2),
            ("RDBMS (B2)", "Mr. Manish Shrivastava", 3, False, "F04-3rdYr-B2", b_yr3_b2),
            ("RDBMS Lab (B2)", "Mr. Manish Shrivastava", 2, True, "F27", b_yr3_b2),
            ("FLAT (B2)", "Dr. Pushpendra Kumar Chandra", 3, False, "F04-3rdYr-B2", b_yr3_b2),
            ("Microprocessor (B2)", "Mr. Amit Kumar Baghel", 3, False, "F04-3rdYr-B2", b_yr3_b2),
            ("Software Engineering (B2)", "Dr. Devendra Kumar Singh", 3, False, "F04-3rdYr-B2", b_yr3_b2),

            # 4th Year -> Total: 18 hrs
            ("TCP/IP Networking", "Dr. Satish Negi", 3, False, "Mech-Building-CSE7th", b_yr4),
            ("Data Mining", "Mrs. Nishi Yadav", 3, False, "Mech-Building-CSE7th", b_yr4),
            ("Cloud Computing", "Dr. Kapil Nagwanshi", 2, False, "Mech-Building-CSE7th", b_yr4),
            ("Cloud Computing Lab", "Dr. Kapil Nagwanshi", 2, True, "F27", b_yr4),
            ("Compiler Design", "Mrs. Raksha Pandey", 4, False, "Mech-Building-CSE7th", b_yr4),
            ("Compiler Design Lab", "Mrs. Raksha Pandey", 2, True, "F26", b_yr4),
            ("Software Defined Networking", "Dr. Pushpendra Kumar Chandra", 1, False, "Mech-Building-CSE7th", b_yr4),
            ("Seminar", "Dr. Vaibhav Kant Singh", 3, False, "Mech-Building-CSE7th", b_yr4),

            # M.Tech I Sem -> Total: 24 hrs
            ("Advanced Algorithms", "Dr. Upasana Sinha", 3, False, "F13", b_mtech),
            ("Big Data Analytics", "Mr. Manjunath Swamy", 3, False, "F13", b_mtech),
            ("Advanced AI", "Dr. Kapil Nagwanshi", 4, False, "F13", b_mtech),
            ("Advanced AI Lab", "Dr. Kapil Nagwanshi", 2, True, "F13", b_mtech),
            ("Research Methodology & IPR", "Dr. Alok Kumar Singh Kushwaha", 3, False, "F13", b_mtech),
            ("Tech Innovation & Startup Ecosystem", "Mr. Suraj Sharma", 3, False, "F13", b_mtech),
            ("Intelligent Transportation Systems", "Dr. Satish Negi", 4, False, "F13", b_mtech),
            ("Cyber Security", "Mr. Manish Shrivastava", 3, False, "F13", b_mtech),
        ]

        created_count = 0
        updated_count = 0

        for sname, tname, hrs, is_lab, rname, batch in subjects_list:
            teacher = Teacher.objects.filter(name=tname).first()
            if not teacher:
                teacher = Teacher.objects.create(name=tname, department=cse, max_classes_per_week=12)

            room = Room.objects.filter(name=rname).first()

            # Enforce continuous 2-hour minimum lab duration block logic
            final_hrs = 2 if is_lab and hrs < 2 else hrs

            defaults_dict = {
                'department': cse,
                'teacher': teacher,
                'classes_per_week': final_hrs,
                'is_lab': is_lab,
            }

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
            f'Done. {created_count} subjects created, {updated_count} updated out of {len(subjects_list)} total.'
        ))