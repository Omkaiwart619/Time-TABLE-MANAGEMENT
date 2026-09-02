"""
Run with: python manage.py seed_ece_department

Seeds data for Electronics & Communication Engineering (ECE) department across 1st, 2nd, 3rd, and 4th years,
plus safeguards for EE-2A and EE-3A cross-department references.
Enforces 2-hour minimum duration blocks for all lab subjects.
"""
from django.core.management.base import BaseCommand
from scheduler.models import Department, Batch, Teacher, Room, Subject


class Command(BaseCommand):
    help = 'Seeds data for Electronics & Communication Engineering department & EE batches (Lab hours set to 2 hrs min)'

    def handle(self, *args, **kwargs):
        # ---------------- Departments ----------------
        ece_dept, _ = Department.objects.get_or_create(
            code='ECE', defaults={'name': 'Electronics & Communication Engineering'}
        )
        ee_dept, _ = Department.objects.get_or_create(
            code='EE', defaults={'name': 'Electrical Engineering'}
        )

        # ---------------- ECE Batches ----------------
        ece_batches_data = [
            (1, 'A'),  # 1st Year (ECE-1)
            (1, 'B'),  # 1st Year (ECE-2)
            (2, 'A'),  # 3rd Sem
            (3, 'A'),  # 5th Sem (Sec A)
            (3, 'B'),  # 5th Sem (Sec B)
            (4, 'A'),  # 7th Sem
        ]
        for year_num, sec in ece_batches_data:
            Batch.objects.get_or_create(department=ece_dept, year=year_num, section=sec)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(ece_batches_data)} ECE batches exist.'))

        # ---------------- EE Batches (EE 2A & EE 3A) ----------------
        ee_batches_data = [
            (2, '2A'), # EE 2A
            (3, '3A'), # EE 3A
        ]
        for year_num, sec in ee_batches_data:
            Batch.objects.get_or_create(department=ee_dept, year=year_num, section=sec)
        self.stdout.write(self.style.SUCCESS('Ensured EE-2A and EE-3A batches exist.'))

        # ---------------- Rooms ----------------
        rooms_data = [
            ("CR-01 (Electronics)", "classroom"),
            ("CR-02 (ECE)", "classroom"),
            ("CR-04 (ECE)", "classroom"),
            ("CR-05 (ECE)", "classroom"),
            ("ECE Seminar Hall / CR-07", "classroom"),
            ("ECE Electronics Devices Lab", "lab"),
            ("ECE Digital Logic Design Lab", "lab"),
            ("ECE LIC Lab", "lab"),
            ("ECE Microprocessor Lab", "lab"),
        ]
        for rname, rtype in rooms_data:
            Room.objects.get_or_create(name=rname, defaults={'room_type': rtype})
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(rooms_data)} ECE rooms exist.'))

        # ---------------- Teachers ----------------
        teachers_data = {
            'Dr. Soma Das': 12,
            'Dr. Sudakar Singh Chauhan': 12,
            'Dr. Pankaj Shankar Srivastava': 12,
            'Dr. Nipun K. Mishra': 12,
            'Dr. Rajiv Dey': 12,
            'Dr. Dharmendra Kumar': 12,
            'Dr. Bhanu Pratap Singh Dohare': 12,
            'Mrs. Bhawna Shukla': 12,
            'Mrs. Beaulah Nath': 12,
            'Mrs. Pragati Patharia': 12,
            'Mr. Deepak K. Rathore': 12,
            'Mr. Shrawan K. Patel': 12,
            'Mrs. Nikita Kashyap': 12,
            'Dr. Anil K. Soni': 12,
            'Mr. Chandan Tamrakar': 12,
            'Dr. Ruchi Tripathi': 12,
            'Dr. Anita Khanna': 12,
            'Dr. Manoj Gupta': 12,
            'Mr. Sumeet Kumar Gupta': 12,
            'Mr. Jitendra Bhardwaj': 12,
            'Dr. Ganesh Shukla': 12,
            'Mrs. Praveena Rajput': 12,
            'Dr. Brijendra Paswan': 12,
            'Mrs. Aradhana Soni': 12,
            'Dr. M P Sharma': 12,
            'English Faculty': 12,
            'ECE Faculty': 12,
        }
        for name, cap in teachers_data.items():
            teacher = Teacher.objects.filter(name=name).first()
            if not teacher:
                Teacher.objects.create(
                    name=name,
                    department=ece_dept,
                    max_classes_per_week=cap
                )
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(teachers_data)} ECE teachers exist.'))

        # ---------------- Fetch Batch Instances ----------------
        b_1st_a = Batch.objects.get(department=ece_dept, year=1, section='A')
        b_3rd = Batch.objects.get(department=ece_dept, year=2, section='A')
        b_5th_a = Batch.objects.get(department=ece_dept, year=3, section='A')
        b_5th_b = Batch.objects.get(department=ece_dept, year=3, section='B')
        b_7th = Batch.objects.get(department=ece_dept, year=4, section='A')

        # ---------------- Subjects List ----------------
        subjects_list = [
            # 1st Semester (ECE-1) -> Total: 16 hrs
            ("Basic Electrical Engineering", "Mr. Sumeet Kumar Gupta", 4, False, "CR-01 (Electronics)", b_1st_a),
            ("Engineering Mathematics I", "Dr. Brijendra Paswan", 4, False, "CR-01 (Electronics)", b_1st_a),
            ("Intro to Information Tech", "Mrs. Aradhana Soni", 3, False, "CR-01 (Electronics)", b_1st_a),
            ("Engineering Physics", "Dr. M P Sharma", 3, False, "CR-01 (Electronics)", b_1st_a),
            ("English for Communication", "English Faculty", 2, False, "CR-01 (Electronics)", b_1st_a),

            # 3rd Semester (Room CR-04) -> Total: 19 hrs
            ("Industrial Engineering", "Dr. Ganesh Shukla", 3, False, "CR-04 (ECE)", b_3rd),
            ("Electronics Devices", "Mr. Chandan Tamrakar", 3, False, "CR-04 (ECE)", b_3rd),
            ("Digital Logic Design", "Dr. Dharmendra Kumar", 3, False, "CR-04 (ECE)", b_3rd),
            ("Transmission Lines and EM Waves", "Dr. Soma Das", 3, False, "CR-04 (ECE)", b_3rd),
            ("Open Elective", "Mr. Deepak K. Rathore", 3, False, "CR-04 (ECE)", b_3rd),
            ("Electronics Devices Lab", "Mr. Chandan Tamrakar", 2, True, "ECE Electronics Devices Lab", b_3rd),
            ("Digital Logic Design Lab", "Dr. Dharmendra Kumar", 2, True, "ECE Digital Logic Design Lab", b_3rd),

            # 5th Semester - Section A (Room CR-02) -> Total: 25 slots
            ("Linear Integrated Circuits (Sec A)", "Dr. Soma Das", 4, False, "CR-02 (ECE)", b_5th_a),
            ("Microprocessor & Microcontroller (Sec A)", "Mrs. Pragati Patharia", 3, False, "CR-02 (ECE)", b_5th_a),
            ("Information Theory and Coding (Sec A)", "Dr. Ruchi Tripathi", 3, False, "CR-02 (ECE)", b_5th_a),
            ("Antenna for Wireless Comm. (Sec A)", "Dr. Nipun K. Mishra", 3, False, "CR-02 (ECE)", b_5th_a),
            ("Digital Image Processing (Sec A)", "Mrs. Nikita Kashyap", 3, False, "CR-02 (ECE)", b_5th_a),
            ("Introduction to AI/ML (Sec A)", "Mr. Jitendra Bhardwaj", 3, False, "CR-02 (ECE)", b_5th_a),
            ("LIC Lab (Sec A)", "Dr. Soma Das", 2, True, "ECE LIC Lab", b_5th_a),
            ("Microprocessor Lab (Sec A)", "Mrs. Pragati Patharia", 2, True, "ECE Microprocessor Lab", b_5th_a),
            ("Mini Project-2 (Sec A)", "ECE Faculty", 2, True, "CR-02 (ECE)", b_5th_a),

            # 5th Semester - Section B (Room Seminar Hall / CR-07) -> Total: 25 slots
            ("Linear Integrated Circuits (Sec B)", "Mrs. Praveena Rajput", 4, False, "ECE Seminar Hall / CR-07", b_5th_b),
            ("Microprocessor & Microcontroller (Sec B)", "Mrs. Pragati Patharia", 3, False, "ECE Seminar Hall / CR-07", b_5th_b),
            ("Information Theory and Coding (Sec B)", "Dr. Ruchi Tripathi", 3, False, "ECE Seminar Hall / CR-07", b_5th_b),
            ("Mobile Communication & Networks (Sec B)", "Dr. Pankaj Shankar Srivastava", 3, False, "ECE Seminar Hall / CR-07", b_5th_b),
            ("Digital Image Processing (Sec B)", "Mrs. Nikita Kashyap", 3, False, "ECE Seminar Hall / CR-07", b_5th_b),
            ("Introduction to AI/ML (Sec B)", "Mr. Jitendra Bhardwaj", 3, False, "ECE Seminar Hall / CR-07", b_5th_b),
            ("LIC Lab (Sec B)", "Mrs. Praveena Rajput", 2, True, "ECE LIC Lab", b_5th_b),
            ("Microprocessor Lab (Sec B)", "Dr. Rajiv Dey", 2, True, "ECE Microprocessor Lab", b_5th_b),
            ("Mini Project-2 (Sec B)", "ECE Faculty", 2, True, "ECE Seminar Hall / CR-07", b_5th_b),

            # 7th Semester (Room CR-05) -> Total: 25 slots
            ("Internet of Things", "Dr. Rajiv Dey", 3, False, "CR-05 (ECE)", b_7th),
            ("Radar & Satellite Communication", "Dr. Pankaj Shankar Srivastava", 3, False, "CR-05 (ECE)", b_7th),
            ("Advance Digital VLSI Design", "Dr. Bhanu Pratap Singh Dohare", 3, False, "CR-05 (ECE)", b_7th),
            ("Microwave Technology", "Mr. Shrawan K. Patel", 3, False, "CR-05 (ECE)", b_7th),
            ("Biomedical Signal Processing", "Mrs. Beaulah Nath", 3, False, "CR-05 (ECE)", b_7th),
            ("MOOC Elective", "ECE Faculty", 3, False, "CR-05 (ECE)", b_7th),
            ("Seminar on Industrial Training", "ECE Faculty", 2, True, "CR-05 (ECE)", b_7th),
            ("Minor Project", "ECE Faculty", 3, True, "CR-05 (ECE)", b_7th),
        ]

        created_count = 0
        updated_count = 0

        for sname, tname, hrs, is_lab, rname, batch in subjects_list:
            teacher = Teacher.objects.filter(name=tname).first()
            room = Room.objects.filter(name=rname).first()

            # Enforce continuous 2-hour minimum lab duration block logic
            final_hrs = 2 if is_lab and hrs < 2 else hrs

            defaults_dict = {
                'department': ece_dept,
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
            f'Done. {created_count} created, {updated_count} updated out of {len(subjects_list)} total ECE subjects.'
        ))