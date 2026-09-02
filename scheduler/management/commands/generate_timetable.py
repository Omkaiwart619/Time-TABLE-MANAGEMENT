import random
import time
from django.core.management.base import BaseCommand
from django.db import transaction

from scheduler.models import (
    Batch,
    Department,
    Room,
    Subject,
    Teacher,
    TimetableEntry,
)

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = [1, 2, 3, 4, 5, 6]
LAB_PAIRS = [(1, 2), (5, 6)]  # Standard 2-hour laboratory blocks


class Command(BaseCommand):
    help = "Generates a clash-free timetable instantly with strict fallback resolution."

    def handle(self, *args, **kwargs):
        start_time = time.time()

        # 1. Clear previous non-fixed timetable entries.
        # Check explicitly for a dedicated pin/lock flag ('is_fixed') to preserve user-locked entries.
        if hasattr(TimetableEntry, 'is_fixed'):
            fixed_entries = list(TimetableEntry.objects.filter(is_fixed=True))
            TimetableEntry.objects.filter(is_fixed=False).delete()
        else:
            # If no dedicated 'is_fixed' field exists, wipe all previous auto-generated entries completely.
            fixed_entries = []
            TimetableEntry.objects.all().delete()

        fixed_count = len(fixed_entries)
        self.stdout.write(
            self.style.NOTICE(f"Preserved {fixed_count} fixed entries in database.")
        )

        # 2. In-memory clash tracking pre-loaded with preserved fixed entries
        batch_schedule = {}
        teacher_schedule = {}
        room_schedule = {}

        for fe in fixed_entries:
            batch_schedule.setdefault(fe.batch_id, set()).add((fe.day, fe.period))
            if fe.teacher_id:
                teacher_schedule.setdefault(fe.teacher_id, set()).add((fe.day, fe.period))
            if fe.room_id:
                room_schedule.setdefault(fe.room_id, set()).add((fe.day, fe.period))

        all_rooms = list(Room.objects.all())
        classrooms = (
            [r for r in all_rooms if getattr(r, 'room_type', 'classroom') == 'classroom']
            or all_rooms
        )
        labs = (
            [r for r in all_rooms if getattr(r, 'room_type', '') == 'lab']
            or all_rooms
        )

        default_teacher = Teacher.objects.first()
        default_room = all_rooms[0] if all_rooms else None

        if not default_room:
            self.stdout.write(self.style.ERROR("❌ Error: No Rooms found in database."))
            return

        details = []
        overall_success = True
        entries_to_create = []

        # Convert QuerySets to lists and shuffle for varied allocation order
        departments = list(Department.objects.all())
        if not departments:
            departments = [None]
        else:
            random.shuffle(departments)

        # 3. Main Scheduling Engine
        for dept in departments:
            dept_name = dept.name if dept else "General"
            dept_batches = (
                list(Batch.objects.filter(department=dept))
                if dept
                else list(Batch.objects.all())
            )
            random.shuffle(dept_batches)

            dept_scheduled = 0
            dept_failed = 0

            for batch in dept_batches:
                b_id = batch.id
                batch_schedule.setdefault(b_id, set())

                if hasattr(batch, 'subjects'):
                    subjects = list(batch.subjects.filter(classes_per_week__gt=0))
                else:
                    subjects = list(Subject.objects.filter(batch=batch, classes_per_week__gt=0))

                # Shuffle subjects first so items with equal weekly hours don't execute in identical sequence
                random.shuffle(subjects)
                subjects.sort(
                    key=lambda s: (
                        0
                        if (
                            getattr(s, 'is_lab', False)
                            or 'lab' in s.name.lower()
                            or 'minor' in s.name.lower()
                        )
                        else 1,
                        -s.classes_per_week,
                    )
                )

                for subject in subjects:
                    teacher = subject.teacher or default_teacher
                    t_id = teacher.id if teacher else 0
                    if t_id:
                        teacher_schedule.setdefault(t_id, set())

                    s_name = subject.name.lower()
                    is_lab = (
                        getattr(subject, 'is_lab', False)
                        or 'lab' in s_name
                        or 'minor' in s_name
                        or 'project' in s_name
                    )

                    remaining_hours = subject.classes_per_week

                    while remaining_hours > 0:
                        desired_block = 2 if (is_lab and remaining_hours >= 2) else 1
                        placed = False

                        shuffled_days = list(DAYS)
                        random.shuffle(shuffled_days)

                        room_pool = list(labs if is_lab else classrooms)

                        # PASS 1: Strict Placement (Check Batch, Teacher, and Room)
                        for day in shuffled_days:
                            if desired_block == 2:
                                start_options = LAB_PAIRS[:]
                                random.shuffle(start_options)
                                slot_candidates = [[p1, p2] for p1, p2 in start_options]
                            else:
                                shuffled_periods = list(PERIODS)
                                random.shuffle(shuffled_periods)
                                slot_candidates = [[p] for p in shuffled_periods]

                            for target_periods in slot_candidates:
                                # 1. Check Batch Clash
                                if any((day, p) in batch_schedule[b_id] for p in target_periods):
                                    continue

                                # 2. Check Teacher Clash
                                if t_id and any((day, p) in teacher_schedule[t_id] for p in target_periods):
                                    continue

                                # 3. Find Available Room (Shuffle room order to balance load across rooms)
                                chosen_room = None
                                random.shuffle(room_pool)
                                for r in room_pool:
                                    room_schedule.setdefault(r.id, set())
                                    if not any((day, p) in room_schedule[r.id] for p in target_periods):
                                        chosen_room = r
                                        break

                                if not chosen_room:
                                    continue

                                # Reserve and Stage Entry
                                for p in target_periods:
                                    entries_to_create.append(
                                        TimetableEntry(
                                            batch=batch,
                                            subject=subject,
                                            teacher=teacher,
                                            room=chosen_room,
                                            day=day,
                                            period=p,
                                            is_published=True,
                                        )
                                    )
                                    batch_schedule[b_id].add((day, p))
                                    if t_id:
                                        teacher_schedule[t_id].add((day, p))
                                    room_schedule[chosen_room.id].add((day, p))
                                    dept_scheduled += 1

                                placed = True
                                remaining_hours -= desired_block
                                break

                            if placed:
                                break

                        # PASS 2: Single-Slot Fallback
                        if not placed and desired_block == 2:
                            for day in shuffled_days:
                                shuffled_periods = list(PERIODS)
                                random.shuffle(shuffled_periods)

                                for p in shuffled_periods:
                                    if (day, p) in batch_schedule[b_id]:
                                        continue
                                    if t_id and (day, p) in teacher_schedule[t_id]:
                                        continue

                                    chosen_room = None
                                    random.shuffle(room_pool)
                                    for r in room_pool:
                                        room_schedule.setdefault(r.id, set())
                                        if (day, p) not in room_schedule[r.id]:
                                            chosen_room = r
                                            break

                                    if not chosen_room:
                                        continue

                                    entries_to_create.append(
                                        TimetableEntry(
                                            batch=batch,
                                            subject=subject,
                                            teacher=teacher,
                                            room=chosen_room,
                                            day=day,
                                            period=p,
                                            is_published=True,
                                        )
                                    )
                                    batch_schedule[b_id].add((day, p))
                                    if t_id:
                                        teacher_schedule[t_id].add((day, p))
                                    room_schedule[chosen_room.id].add((day, p))
                                    dept_scheduled += 1

                                    placed = True
                                    remaining_hours -= 1
                                    break

                                if placed:
                                    break

                        if not placed:
                            dept_failed += 1
                            remaining_hours = 0
                            break

            if dept_failed > 0:
                overall_success = False
                details.append(
                    (
                        dept_name,
                        False,
                        f"Scheduled {dept_scheduled} slots, {dept_failed} failed due to constraint limits",
                    )
                )
            else:
                details.append(
                    (dept_name, True, f"Successfully scheduled {dept_scheduled} slots")
                )

        # 4. Save to Database in Atomic Transaction
        with transaction.atomic():
            TimetableEntry.objects.bulk_create(entries_to_create)

        elapsed = round(time.time() - start_time, 2)

        # 5. Output Results Summary
        self.stdout.write("\n--- Per-Department Results ---")
        for dept_name, dept_success, info in details:
            if dept_success:
                self.stdout.write(self.style.SUCCESS(f"  {dept_name}: OK - {info}"))
            else:
                self.stdout.write(self.style.ERROR(f"  {dept_name}: FAILED - {info}"))

        self.stdout.write("")
        if overall_success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Generation completed successfully for all departments in {elapsed}s!"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Generation completed with isolated department failures in {elapsed}s."
                )
            )

        total_entries = TimetableEntry.objects.count()
        generated_entries = len(entries_to_create)

        self.stdout.write(
            f"\nTotal entries in database: {total_entries} "
            f"({fixed_count} Fixed + {generated_entries} Generated)"
        )