"""
Production-Grade Global CSP Timetable Generator with Per-Department Isolated Failure handling.
Preserves Fixed/Pinned Entries while correctly clearing dynamic runs.

Strictly mapped to UI Grid:
Period 1: 10-11 AM
Period 2: 11-12 PM
Period 3: 12-1 PM
Lunch:    1-2 PM
Period 4: 2-3 PM
Period 5: 3-4 PM
Period 6: 4-5 PM
"""

import random
from collections import defaultdict
from django.db import close_old_connections, connection
from .models import Department, Subject, Teacher, Room, TimetableEntry

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Exact UI timetable slot mapping
PERIOD_TIME_MAP = {
    1: ("10:00", "11:00"),  # Lab Block 1 (Hour 1) -> 10-11 AM
    2: ("11:00", "12:00"),  # Lab Block 1 (Hour 2) -> 11-12 PM
    3: ("12:00", "13:00"),  # Pre-Lunch Theory    -> 12-1 PM
    4: ("14:00", "15:00"),  # Post-Lunch Theory   -> 2-3 PM
    5: ("15:00", "16:00"),  # Lab Block 2 (Hour 1) -> 3-4 PM
    6: ("16:00", "17:00"),  # Lab Block 2 (Hour 2) -> 4-5 PM
}

PERIODS = [1, 2, 3, 4, 5, 6]

PRIORITY_LAB_PAIRS = [(1, 2), (5, 6)]
PRIORITY_THEORY_PERIODS = [1, 2, 3, 4, 5, 6]

MAX_BACKTRACK_STEPS = 500000


def _has_is_fixed_field():
    """Helper to check if TimetableEntry has an explicit 'is_fixed' boolean field."""
    field_names = [f.name for f in TimetableEntry._meta.get_fields()]
    return 'is_fixed' in field_names


def clear_generated_timetable():
    """
    Safely clears auto-generated entries.
    If 'is_fixed' exists, deletes entries where is_fixed=False.
    Otherwise, wipes all past generated entries to prevent self-lockout.
    """
    if _has_is_fixed_field():
        TimetableEntry.objects.filter(is_fixed=False).delete()
    else:
        TimetableEntry.objects.all().delete()


def generate_timetable(max_attempts=30):
    close_old_connections()
    connection.ensure_connection()

    all_departments = list(Department.objects.all())
    all_rooms = list(Room.objects.all())
    classrooms = [r for r in all_rooms if getattr(r, 'room_type', 'classroom') == 'classroom'] or all_rooms
    labs = [r for r in all_rooms if getattr(r, 'room_type', '') == 'lab'] or all_rooms
    teachers = {t.id: t for t in Teacher.objects.all()}

    all_subjects = list(
        Subject.objects.all().select_related('required_room', 'teacher', 'batch', 'department')
    )

    if not all_subjects:
        return False, "No subjects found in the database.", []

    # Filter out infeasible departments individually so valid ones can proceed
    valid_departments = []
    dept_details = []
    infeasible_dept_ids = set()

    for dept in all_departments:
        dept_subjects = [s for s in all_subjects if s.department_id == dept.id]
        if not dept_subjects:
            dept_details.append({'dept_name': dept.name, 'success': True, 'info': 'No subjects registered.'})
            continue

        is_valid, error_msg = _precheck_department_feasibility(dept_subjects, teachers)
        if not is_valid:
            infeasible_dept_ids.add(dept.id)
            dept_details.append({
                'dept_name': dept.name,
                'success': False,
                'info': error_msg
            })
        else:
            valid_departments.append(dept)

    schedulable_subjects = [s for s in all_subjects if s.department_id not in infeasible_dept_ids]

    if not schedulable_subjects:
        return False, "All departments failed feasibility checks.", dept_details

    teacher_batch_count = defaultdict(set)
    for s in schedulable_subjects:
        if s.teacher_id:
            teacher_batch_count[s.teacher_id].add(s.batch_id)

    # Unit conversion for valid subjects (classes_per_week > 0)
    units = []
    for subj in schedulable_subjects:
        if subj.classes_per_week == 0:
            continue
            
        if subj.is_lab:
            sessions = max(1, subj.classes_per_week // 2)
            for _ in range(sessions):
                units.append(subj)
        else:
            for _ in range(subj.classes_per_week):
                units.append(subj)

    def global_hardness_score(subj):
        score = 0
        if subj.is_lab:
            score += 3000
        if subj.required_room_id:
            score += 300
        if subj.teacher_id and len(teacher_batch_count[subj.teacher_id]) > 1:
            score += 150
        score += subj.classes_per_week
        return score

    units.sort(key=global_hardness_score, reverse=True)

    for attempt in range(max_attempts):
        teacher_busy = defaultdict(set)
        room_busy = defaultdict(set)
        batch_busy = defaultdict(set)
        teacher_load = defaultdict(int)
        subject_day_used = defaultdict(set)
        batch_lab_day_count = defaultdict(lambda: defaultdict(int))
        batch_day_slots = defaultdict(lambda: defaultdict(int))

        # --- PRE-LOAD PINNED / FIXED ENTRIES ONLY ---
        if _has_is_fixed_field():
            fixed_entries = TimetableEntry.objects.filter(is_fixed=True).select_related('subject')
        else:
            fixed_entries = TimetableEntry.objects.none()

        for e in fixed_entries:
            slot = (e.day, e.period if hasattr(e, 'period') else None)
            if slot[1] is None:
                continue
            if e.teacher_id:
                teacher_busy[e.teacher_id].add(slot)
                teacher_load[e.teacher_id] += 1
            if e.room_id:
                room_busy[e.room_id].add(slot)
            if e.batch_id:
                batch_busy[e.batch_id].add(slot)
                batch_day_slots[e.batch_id][e.day] += 1
                if e.subject and getattr(e.subject, 'is_lab', False):
                    batch_lab_day_count[e.batch_id][e.day] += 1

            if e.subject_id:
                subject_day_used[e.subject_id].add(e.day)

        placements = []
        step_counter = [0]

        current_units = units[:]
        if attempt > 0:
            cutoff = int(len(current_units) * 0.20)
            head = current_units[:cutoff]
            tail = current_units[cutoff:]
            random.shuffle(tail)
            current_units = head + tail

        success = _global_backtrack(
            current_units, 0, teacher_busy, room_busy, batch_busy, teacher_load,
            subject_day_used, batch_lab_day_count, batch_day_slots, teachers,
            classrooms, labs, placements, step_counter, MAX_BACKTRACK_STEPS, attempt
        )

        if success:
            clear_generated_timetable()
            _save_placements(placements)

            dept_summary = defaultdict(int)
            for p in placements:
                dept_summary[p[0].department.name] += 1

            for dept in valid_departments:
                dept_details.append({
                    'dept_name': dept.name,
                    'success': True,
                    'info': f"Timetable generated successfully ({dept_summary[dept.name]} dynamic slots assigned)."
                })

            overall_status = len(infeasible_dept_ids) == 0
            message = "All departments generated successfully!" if overall_status else "Generation completed with isolated department failures."
            return overall_status, message, dept_details

    return False, f"Global CSP Solver exceeded step limit after {max_attempts} attempts.", dept_details


def _global_backtrack(units, index, teacher_busy, room_busy, batch_busy, teacher_load,
                      subject_day_used, batch_lab_day_count, batch_day_slots, teachers,
                      classrooms, labs, placements, step_counter, max_steps, attempt):
    step_counter[0] += 1
    if step_counter[0] > max_steps:
        return False

    if index == len(units):
        return True

    subject = units[index]
    teacher = teachers.get(subject.teacher_id)
    if teacher is None:
        return False

    load_cost = 2 if subject.is_lab else 1
    if teacher_load[teacher.id] + load_cost > getattr(teacher, 'max_classes_per_week', 30):
        return False

    candidate_rooms = _get_candidate_rooms(subject, classrooms, labs)
    if not candidate_rooms:
        return False

    unused_days = [d for d in DAYS if d not in subject_day_used[subject.id]]
    candidate_days = unused_days if unused_days else DAYS[:]

    if subject.is_lab:
        candidate_days = [d for d in candidate_days if batch_lab_day_count[subject.batch_id][d] < 1]

    if attempt > 1:
        random.shuffle(candidate_days)
    else:
        candidate_days.sort(key=lambda d: batch_day_slots[subject.batch_id][d])

    # --- LAB BRANCH ---
    if subject.is_lab:
        slot_options = PRIORITY_LAB_PAIRS[:]
        if attempt > 0:
            random.shuffle(slot_options)

        for day in candidate_days:
            for p1, p2 in slot_options:
                slot1, slot2 = (day, p1), (day, p2)
                if slot1 in teacher_busy[teacher.id] or slot2 in teacher_busy[teacher.id]:
                    continue
                if slot1 in batch_busy[subject.batch_id] or slot2 in batch_busy[subject.batch_id]:
                    continue

                # Shuffle rooms per slot check to distribute load across room pool
                shuffled_rooms = candidate_rooms[:]
                if attempt > 0:
                    random.shuffle(shuffled_rooms)

                for room in shuffled_rooms:
                    if slot1 in room_busy[room.id] or slot2 in room_busy[room.id]:
                        continue

                    teacher_busy[teacher.id].update([slot1, slot2])
                    room_busy[room.id].update([slot1, slot2])
                    batch_busy[subject.batch_id].update([slot1, slot2])
                    teacher_load[teacher.id] += 2
                    subject_day_used[subject.id].add(day)
                    batch_lab_day_count[subject.batch_id][day] += 1
                    batch_day_slots[subject.batch_id][day] += 2

                    placements.append((subject, teacher, room, subject.batch_id, day, p1, p2))

                    if _global_backtrack(units, index + 1, teacher_busy, room_busy, batch_busy,
                                         teacher_load, subject_day_used, batch_lab_day_count,
                                         batch_day_slots, teachers, classrooms, labs,
                                         placements, step_counter, max_steps, attempt):
                        return True

                    teacher_busy[teacher.id].difference_update([slot1, slot2])
                    room_busy[room.id].difference_update([slot1, slot2])
                    batch_busy[subject.batch_id].difference_update([slot1, slot2])
                    teacher_load[teacher.id] -= 2
                    subject_day_used[subject.id].discard(day)
                    batch_lab_day_count[subject.batch_id][day] -= 1
                    batch_day_slots[subject.batch_id][day] -= 2
                    placements.pop()

    # --- THEORY BRANCH ---
    else:
        periods_ordered = PRIORITY_THEORY_PERIODS[:]
        if attempt > 0 and random.random() < 0.4:
            random.shuffle(periods_ordered)

        for day in candidate_days:
            for period in periods_ordered:
                slot = (day, period)
                if slot in teacher_busy[teacher.id] or slot in batch_busy[subject.batch_id]:
                    continue

                shuffled_rooms = candidate_rooms[:]
                if attempt > 0:
                    random.shuffle(shuffled_rooms)

                for room in shuffled_rooms:
                    if slot in room_busy[room.id]:
                        continue

                    teacher_busy[teacher.id].add(slot)
                    room_busy[room.id].add(slot)
                    batch_busy[subject.batch_id].add(slot)
                    teacher_load[teacher.id] += 1
                    subject_day_used[subject.id].add(day)
                    batch_day_slots[subject.batch_id][day] += 1
                    placements.append((subject, teacher, room, subject.batch_id, day, period, None))

                    if _global_backtrack(units, index + 1, teacher_busy, room_busy, batch_busy,
                                         teacher_load, subject_day_used, batch_lab_day_count,
                                         batch_day_slots, teachers, classrooms, labs,
                                         placements, step_counter, max_steps, attempt):
                        return True

                    teacher_busy[teacher.id].discard(slot)
                    room_busy[room.id].discard(slot)
                    batch_busy[subject.batch_id].discard(slot)
                    teacher_load[teacher.id] -= 1
                    subject_day_used[subject.id].discard(day)
                    batch_day_slots[subject.batch_id][day] -= 1
                    placements.pop()

    return False


def _get_candidate_rooms(subject, classrooms, labs):
    pool = labs if subject.is_lab else classrooms
    if subject.required_room_id and subject.required_room:
        fallbacks = [r for r in pool if r.id != subject.required_room_id]
        return [subject.required_room] + fallbacks
    return pool


def _precheck_department_feasibility(dept_subjects, teachers):
    batch_demands = defaultdict(int)
    teacher_demands = defaultdict(int)

    for s in dept_subjects:
        slots_needed = s.classes_per_week
        batch_demands[s.batch_id] += slots_needed
        teacher_demands[s.teacher_id] += slots_needed

    for batch_id, demand in batch_demands.items():
        if demand > 30:
            return False, f"Feasibility Check Failed: Batch ID {batch_id} requires {demand} slots (max 30 slots available per week)."

    for teacher_id, demand in teacher_demands.items():
        t = teachers.get(teacher_id)
        max_load = getattr(t, 'max_classes_per_week', 30) if t else 30
        if demand > max_load:
            t_name = t.name if t else f"ID {teacher_id}"
            return False, f"Feasibility Check Failed: Teacher '{t_name}' assigned {demand} classes/week, exceeding cap of {max_load}."

    return True, ""


def check_clash(teacher_id, room_id, batch_id, day, period, exclude_entry_id=None):
    existing = TimetableEntry.objects.filter(day=day, period=period)
    if exclude_entry_id:
        existing = existing.exclude(pk=exclude_entry_id)
    for e in existing:
        if teacher_id and e.teacher_id == teacher_id:
            return True, f"Teacher is already teaching another class at this time ({e.subject.name})."
        if room_id and e.room_id == room_id:
            return True, f"Room is already booked at this time ({e.subject.name})."
        if batch_id and e.batch_id == batch_id:
            return True, f"This batch already has a class at this time ({e.subject.name})."
    return False, "No clash."


def _save_placements(placements):
    entries = []
    
    field_names = [f.name for f in TimetableEntry._meta.get_fields()]
    has_period_field = 'period' in field_names
    has_time_fields = 'start_time' in field_names and 'end_time' in field_names
    has_is_fixed_field = 'is_fixed' in field_names

    for subject, teacher, room, batch_id, day, p1, p2 in placements:
        periods_to_create = [p1] if p2 is None else [p1, p2]
        
        for p in periods_to_create:
            entry_kwargs = {
                'subject': subject,
                'teacher': teacher,
                'room': room,
                'batch_id': batch_id,
                'day': day,
                'is_published': True,
            }

            if has_is_fixed_field:
                entry_kwargs['is_fixed'] = False
            
            if has_period_field:
                entry_kwargs['period'] = p
                
            if has_time_fields:
                start, end = PERIOD_TIME_MAP.get(p, ("10:00", "11:00"))
                entry_kwargs['start_time'] = start
                entry_kwargs['end_time'] = end

            entries.append(TimetableEntry(**entry_kwargs))

    TimetableEntry.objects.bulk_create(entries)