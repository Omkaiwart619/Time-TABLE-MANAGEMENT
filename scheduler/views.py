import json
import re
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from xhtml2pdf import pisa

# ReportLab imports for generating consolidated department grid printout
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .algorithm import check_clash, clear_generated_timetable, generate_timetable
from .models import Batch, Department, Room, Subject, Teacher, TimetableEntry

DAYS_LIST = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS_LIST = [1, 2, 3, 4, 5, 6]
PERIOD_TIMES = {
    1: "10:00 - 11:00",
    2: "11:00 - 12:00",
    3: "12:00 - 01:00",
    4: "02:00 - 03:00",
    5: "03:00 - 04:00",
    6: "04:00 - 05:00",
}


# ---------------- DECORATOR FOR ROLE PROTECTION ----------------

def admin_required(view_func):
    """Decorator to ensure only admin users can access management views."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('logged_in'):
            return redirect('login')
        if request.session.get('role') != 'admin':
            messages.warning(request, "Access restricted. You do not have permission to view this page.")
            return redirect('my_timetable')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ---------------- AUTHENTICATION & ROLE MANAGEMENT ----------------

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            request.session['logged_in'] = True
            request.session['username'] = username

            if user.is_staff or user.is_superuser:
                request.session['role'] = 'admin'
                return redirect('dashboard')

            teacher = Teacher.objects.filter(user=user).first()
            if teacher:
                request.session['role'] = 'teacher'
                request.session['teacher_id'] = teacher.id
                return redirect('my_timetable')

            batch = Batch.objects.filter(user=user).first()
            if batch:
                request.session['role'] = 'student'
                request.session['batch_id'] = batch.id
                return redirect('my_timetable')

            return render(request, 'scheduler/login.html', {'error': 'Account not assigned to any system role.'})
        else:
            return render(request, 'scheduler/login.html', {'error': 'Invalid username or password.'})

    return render(request, 'scheduler/login.html')


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login')


@admin_required
def dashboard(request):
    stats = {
        'departments': Department.objects.count(),
        'batches': Batch.objects.count(),
        'teachers': Teacher.objects.count(),
        'rooms': Room.objects.count(),
        'subjects': Subject.objects.count(),
    }
    return render(request, 'scheduler/dashboard.html', {'stats': stats})


def my_timetable(request):
    if not request.session.get('logged_in'):
        return redirect('login')

    role = request.session.get('role')

    if role == 'admin':
        return redirect('dashboard')

    entries = TimetableEntry.objects.select_related('subject', 'teacher', 'room', 'batch').all()
    label = ""
    workload_note = None

    if role == 'teacher':
        teacher_id = request.session.get('teacher_id')
        entries = entries.filter(teacher_id=teacher_id)
        teacher = get_object_or_404(Teacher, id=teacher_id)
        label = f"{teacher.name}'s Schedule"
        workload_note = f"Weekly Workload: {entries.count()} / {teacher.max_classes_per_week} assigned hours."

    elif role == 'student':
        batch_id = request.session.get('batch_id')
        entries = entries.filter(batch_id=batch_id)
        batch = get_object_or_404(Batch, id=batch_id)
        label = f"{batch} Schedule"

    else:
        return redirect('login')

    grid = {day: {p: None for p in PERIODS_LIST} for day in DAYS_LIST}
    for e in entries:
        if e.day in grid and e.period in grid[e.day]:
            grid[e.day][e.period] = e

    formatted_grid = {day: {p: None for p in PERIODS_LIST} for day in DAYS_LIST}
    for day in DAYS_LIST:
        skip_next = False
        for p in PERIODS_LIST:
            if skip_next:
                formatted_grid[day][p] = {'is_skip': True}
                skip_next = False
                continue

            entry = grid[day][p]
            if entry:
                if entry.subject.is_lab:
                    formatted_grid[day][p] = {'entry': entry, 'is_lab_block': True}
                    skip_next = True
                else:
                    formatted_grid[day][p] = {'entry': entry, 'is_lab_block': False}

    context = {
        'grid': formatted_grid,
        'days': DAYS_LIST,
        'periods': PERIODS_LIST,
        'period_times': PERIOD_TIMES,
        'label': label,
        'workload_note': workload_note,
        'role': role,
    }
    return render(request, 'scheduler/my_timetable.html', context)


# ---------------- DEPARTMENTS ----------------

@admin_required
def department_list(request):
    departments = Department.objects.annotate(
        batch_count=Count('batches', distinct=True),
        teacher_count=Count('teachers', distinct=True)
    ).all()
    return render(request, 'scheduler/department_list.html', {'departments': departments})


@admin_required
def department_add(request):
    if request.method == 'POST':
        Department.objects.create(
            name=request.POST.get('name'),
            code=request.POST.get('code')
        )
        messages.success(request, 'Department added successfully.')
        return redirect('department_list')
    return render(request, 'scheduler/department_form.html')


@admin_required
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.delete()
    messages.success(request, 'Department deleted.')
    return redirect('department_list')


# ---------------- ROOMS ----------------

@admin_required
def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'scheduler/room_list.html', {'rooms': rooms})


@admin_required
def room_add(request):
    if request.method == 'POST':
        Room.objects.create(
            name=request.POST.get('name'),
            room_type=request.POST.get('room_type'),
            capacity=request.POST.get('capacity') or None
        )
        messages.success(request, 'Room added successfully.')
        return redirect('room_list')
    return render(request, 'scheduler/room_form.html')


@admin_required
def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    room.delete()
    messages.success(request, 'Room deleted.')
    return redirect('room_list')


# ---------------- BATCHES ----------------

@admin_required
def batch_list(request):
    batches = Batch.objects.select_related('department').all()
    return render(request, 'scheduler/batch_list.html', {'batches': batches})


@admin_required
def batch_add(request):
    departments = Department.objects.all()
    if request.method == 'POST':
        Batch.objects.create(
            department_id=request.POST.get('department'),
            year=request.POST.get('year'),
            section=request.POST.get('section'),
            strength=request.POST.get('strength') or None
        )
        messages.success(request, 'Batch added successfully.')
        return redirect('batch_list')
    return render(request, 'scheduler/batch_form.html', {'departments': departments})


@admin_required
def batch_delete(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    batch.delete()
    messages.success(request, 'Batch deleted.')
    return redirect('batch_list')


# ---------------- TEACHERS ----------------

@admin_required
def teacher_list(request):
    teachers = Teacher.objects.select_related('department', 'lab_room').all()
    return render(request, 'scheduler/teacher_list.html', {'teachers': teachers})


@admin_required
def teacher_add(request):
    departments = Department.objects.all()
    labs = Room.objects.filter(room_type='lab')
    
    if request.method == 'POST':
        is_lab_incharge = request.POST.get('is_lab_incharge') == 'on'
        Teacher.objects.create(
            name=request.POST.get('name'),
            department_id=request.POST.get('department'),
            max_classes_per_week=request.POST.get('max_classes_per_week') or 16,
            is_lab_incharge=is_lab_incharge,
            lab_room_id=request.POST.get('lab_room') if is_lab_incharge else None
        )
        messages.success(request, 'Teacher added successfully.')
        return redirect('teacher_list')
        
    return render(request, 'scheduler/teacher_form.html', {
        'departments': departments, 
        'labs': labs
    })


@admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    teacher.delete()
    messages.success(request, 'Teacher deleted.')
    return redirect('teacher_list')


# ---------------- SUBJECTS ----------------

@admin_required
def subject_list(request):
    search_query = request.GET.get('q', '').strip()

    subject_queryset = Subject.objects.select_related(
        'department', 
        'batch', 
        'teacher', 
        'required_room'
    ).all().order_by('id')

    if search_query:
        subject_queryset = subject_queryset.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(teacher__name__icontains=search_query) |
            Q(batch__section__icontains=search_query) |
            Q(batch__year__icontains=search_query)
        )

    paginator = Paginator(subject_queryset, 20)
    page_number = request.GET.get('page')
    subjects = paginator.get_page(page_number)

    return render(request, 'scheduler/subject_list.html', {
        'subjects': subjects,
        'search_query': search_query,
    })


@admin_required
def subject_add(request):
    departments = Department.objects.all()
    batches = Batch.objects.select_related('department').all()
    teachers = Teacher.objects.select_related('department').all()
    rooms = Room.objects.all()

    if request.method == 'POST':
        Subject.objects.create(
            name=request.POST.get('name'),
            code=request.POST.get('code'),
            department_id=request.POST.get('department'),
            batch_id=request.POST.get('batch'),
            teacher_id=request.POST.get('teacher'),
            classes_per_week=request.POST.get('classes_per_week') or 3,
            is_lab=request.POST.get('is_lab') == 'on',
            required_room_id=request.POST.get('required_room') or None
        )
        messages.success(request, 'Subject added successfully.')
        return redirect('subject_list')

    return render(request, 'scheduler/subject_form.html', {
        'departments': departments, 
        'batches': batches, 
        'teachers': teachers, 
        'rooms': rooms
    })


@admin_required
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    subject.delete()
    messages.success(request, 'Subject deleted.')
    return redirect('subject_list')


# ---------------- TIMETABLE GENERATE + VIEW ----------------

import io
from django.core.management import call_command
from django.contrib import messages
from django.shortcuts import redirect, render
from .models import Department, TimetableEntry

@admin_required
def generate_timetable_view(request):
    if request.method == 'POST':
        try:
            # Capture stdout from management command execution
            out = io.StringIO()
            call_command('generate_timetable', stdout=out)
            output_text = out.getvalue()

            # Parse output lines for per-department details display in UI
            formatted_details = []
            for line in output_text.splitlines():
                line_str = line.strip()
                if "OK -" in line_str:
                    parts = line_str.split(":", 1)
                    dept_name = parts[0].strip()
                    info = parts[1].replace("OK -", "").strip() if len(parts) > 1 else ""
                    formatted_details.append({'dept_name': dept_name, 'success': True, 'info': info})
                elif "FAILED -" in line_str:
                    parts = line_str.split(":", 1)
                    dept_name = parts[0].strip()
                    info = parts[1].replace("FAILED -", "").strip() if len(parts) > 1 else ""
                    formatted_details.append({'dept_name': dept_name, 'success': False, 'info': info})

            request.session['generation_details'] = formatted_details

            # Verify DB entries were generated
            total_entries = TimetableEntry.objects.count()
            if total_entries > 0:
                messages.success(request, f"Timetable generated successfully! Total saved entries: {total_entries}.")
            else:
                messages.error(request, "Generation finished, but no entries were saved to the database.")

        except Exception as e:
            messages.error(request, f"Generation failed: {str(e)}")

        return redirect('timetable_view')

    return render(request, 'scheduler/timetable_generate.html')

def timetable_view(request):
    if not request.session.get('logged_in'):
        return redirect('login')

    generation_details = request.session.pop('generation_details', None)

    batches = Batch.objects.select_related('department').all()
    teachers = Teacher.objects.select_related('department').all()
    rooms = Room.objects.all()

    filter_type = request.GET.get('filter_type', 'batch')
    filter_id = request.GET.get('filter_id')

    entries = TimetableEntry.objects.select_related(
        'subject', 
        'teacher', 
        'room', 
        'batch', 
        'batch__department'
    ).all()

    if filter_id:
        entries = entries.filter(**{f'{filter_type}_id': filter_id})
    elif batches.exists():
        filter_type = 'batch'
        filter_id = str(batches.first().id)
        entries = entries.filter(batch_id=filter_id)

    grid = {day: {p: None for p in PERIODS_LIST} for day in DAYS_LIST}
    for e in entries:
        if e.day in grid and e.period in grid[e.day]:
            grid[e.day][e.period] = e

    formatted_grid = {day: {p: None for p in PERIODS_LIST} for day in DAYS_LIST}
    for day in DAYS_LIST:
        skip_next = False
        for p in PERIODS_LIST:
            if skip_next:
                formatted_grid[day][p] = {'is_skip': True}
                skip_next = False
                continue

            entry = grid[day][p]
            if entry:
                if entry.subject.is_lab:
                    formatted_grid[day][p] = {'entry': entry, 'is_lab_block': True}
                    skip_next = True
                else:
                    formatted_grid[day][p] = {'entry': entry, 'is_lab_block': False}

    context = {
        'batches': batches,
        'teachers': teachers,
        'rooms': rooms,
        'grid': formatted_grid,
        'days': DAYS_LIST,
        'periods': PERIODS_LIST,
        'period_times': PERIOD_TIMES,
        'filter_type': filter_type,
        'filter_id': str(filter_id) if filter_id else None,
        'generation_details': generation_details,
    }
    return render(request, 'scheduler/timetable_view.html', context)


@admin_required
def timetable_edit(request, pk):
    entry = get_object_or_404(
        TimetableEntry.objects.select_related('subject', 'teacher', 'room', 'batch'), 
        pk=pk
    )
    rooms = Room.objects.all()

    if request.method == 'POST':
        new_day = request.POST.get('day')
        new_period = int(request.POST.get('period'))
        new_room_id = int(request.POST.get('room'))

        has_clash, message = check_clash(
            teacher_id=entry.teacher_id,
            room_id=new_room_id,
            batch_id=entry.batch_id,
            day=new_day,
            period=new_period,
            exclude_entry_id=entry.pk
        )

        if has_clash:
            messages.error(request, f"Cannot save: {message}")
        else:
            entry.day = new_day
            entry.period = new_period
            entry.room_id = new_room_id
            entry.save()
            messages.success(request, "Class moved successfully.")
            return redirect('timetable_view')

    return render(request, 'scheduler/timetable_edit.html', {
        'entry': entry,
        'rooms': rooms,
        'days': DAYS_LIST,
        'periods': PERIODS_LIST,
        'period_times': PERIOD_TIMES
    })


@require_POST
def edit_timetable_slot(request):
    if not request.session.get('logged_in'):
        return JsonResponse({"status": "error", "message": "Authentication required."}, status=401)
        
    if request.session.get('role') != 'admin':
        return JsonResponse({"status": "error", "message": "Access denied. Admin permissions required."}, status=403)

    try:
        data = json.loads(request.body)
        entry_id = data.get("entry_id")
        new_day = data.get("new_day")
        new_period = int(data.get("new_period"))

        if not all([entry_id, new_day, new_period]):
            return JsonResponse({"status": "error", "message": "Missing required parameters."}, status=400)

        primary_entry = get_object_or_404(
            TimetableEntry.objects.select_related('subject', 'batch', 'teacher', 'room'), 
            pk=entry_id
        )

        with transaction.atomic():
            if primary_entry.subject.is_lab:
                sibling_entry = TimetableEntry.objects.filter(
                    subject=primary_entry.subject,
                    batch=primary_entry.batch
                ).exclude(pk=primary_entry.pk).first()

                if new_period in [1, 2]:
                    p1, p2 = 1, 2
                elif new_period == 3:
                    p1, p2 = 2, 3
                elif new_period in [4, 5]:
                    p1, p2 = 4, 5
                elif new_period == 6:
                    p1, p2 = 5, 6
                else:
                    return JsonResponse({"status": "error", "message": "Invalid target period for lab block."}, status=400)

                # Move entries out of the way temporarily to clear database unique constraint checks
                orig_p1, orig_p2 = primary_entry.period, sibling_entry.period if sibling_entry else None
                primary_entry.period = -1
                primary_entry.save()
                if sibling_entry:
                    sibling_entry.period = -2
                    sibling_entry.save()

                clash_p1, msg_p1 = check_clash(
                    teacher_id=primary_entry.teacher_id,
                    room_id=primary_entry.room_id,
                    batch_id=primary_entry.batch_id,
                    day=new_day,
                    period=p1,
                    exclude_entry_id=primary_entry.pk
                )
                clash_p2, msg_p2 = check_clash(
                    teacher_id=primary_entry.teacher_id,
                    room_id=primary_entry.room_id,
                    batch_id=primary_entry.batch_id,
                    day=new_day,
                    period=p2,
                    exclude_entry_id=sibling_entry.pk if sibling_entry else primary_entry.pk
                )

                if clash_p1 or clash_p2:
                    # Rollback updates
                    primary_entry.period = orig_p1
                    primary_entry.save()
                    if sibling_entry:
                        sibling_entry.period = orig_p2
                        sibling_entry.save()
                    err_msg = msg_p1 if clash_p1 else msg_p2
                    return JsonResponse({"status": "error", "message": f"Lab Block Conflict: {err_msg}"}, status=400)

                primary_entry.day = new_day
                primary_entry.period = p1
                primary_entry.save()

                if sibling_entry:
                    sibling_entry.day = new_day
                    sibling_entry.period = p2
                    sibling_entry.save()
            else:
                clash, msg = check_clash(
                    teacher_id=primary_entry.teacher_id,
                    room_id=primary_entry.room_id,
                    batch_id=primary_entry.batch_id,
                    day=new_day,
                    period=new_period,
                    exclude_entry_id=primary_entry.pk
                )
                if clash:
                    return JsonResponse({"status": "error", "message": msg}, status=400)

                primary_entry.day = new_day
                primary_entry.period = new_period
                primary_entry.save()

        return JsonResponse({"status": "success", "message": "Timetable updated successfully."})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON format."}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# ---------------- EXPORT PDF FUNCTIONS ----------------

def timetable_export_pdf(request):
    filter_type = request.GET.get('filter_type')
    filter_id = request.GET.get('filter_id')

    entries = TimetableEntry.objects.select_related('subject', 'teacher', 'room', 'batch').all()
    title_label = ""

    if filter_type == 'teacher' and filter_id:
        teacher_id = int(filter_id)
        entries = entries.filter(teacher_id=teacher_id)
        teacher = get_object_or_404(Teacher, id=teacher_id)
        title_label = f"Dr. {teacher.name}" if not teacher.name.startswith("Dr.") else teacher.name

    elif filter_type == 'batch' and filter_id:
        batch_id = int(filter_id)
        entries = entries.filter(batch_id=batch_id)
        batch = get_object_or_404(Batch, id=batch_id)
        title_label = str(batch)

    else:
        title_label = "All Schedules"

    raw_grid = {day: {p: None for p in range(1, 7)} for day in DAYS_LIST}
    for e in entries:
        p_num = int(e.period) if isinstance(e.period, (int, str)) and str(e.period).isdigit() else e.period
        if e.day in raw_grid and p_num in raw_grid[e.day]:
            raw_grid[e.day][p_num] = e

    formatted_grid = {day: {p: None for p in range(1, 7)} for day in DAYS_LIST}
    for day in DAYS_LIST:
        skip_next = False
        for p in range(1, 7):
            if skip_next:
                formatted_grid[day][p] = {'is_skip': True}
                skip_next = False
                continue

            entry = raw_grid[day][p]
            if entry:
                if entry.subject.is_lab:
                    formatted_grid[day][p] = {'entry': entry, 'is_lab_block': True}
                    skip_next = True
                else:
                    formatted_grid[day][p] = {'entry': entry, 'is_lab_block': False}
            else:
                formatted_grid[day][p] = {'entry': None, 'is_lab_block': False}

    context = {
        'grid': formatted_grid,
        'days': DAYS_LIST,
        'periods': range(1, 7),
        'title_label': title_label,
        'filter_type': filter_type,
    }

    html_string = render_to_string('scheduler/timetable_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Timetable_{title_label}.pdf"'

    pisa_status = pisa.CreatePDF(html_string, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    
    return response


@admin_required
def master_pdf_export(request):
    """
    Department Master Timetable PDF Exporter.
    Generates a single-page landscape PDF with no cut-off margins.
    """
    dept_id = request.GET.get('department_id')

    if not dept_id:
        departments = Department.objects.all()
        return render(request, 'scheduler/master_pdf_select.html', {'departments': departments})

    department = get_object_or_404(Department, pk=dept_id)
    batches = list(Batch.objects.filter(department=department).order_by('year', 'section'))
    all_entries = TimetableEntry.objects.select_related('subject', 'teacher', 'room', 'batch').filter(batch__department=department)

    grid = {day: {p: {} for p in PERIODS_LIST} for day in DAYS_LIST}
    for e in all_entries:
        if e.day in grid and e.period in grid[e.day]:
            grid[e.day][e.period][e.batch_id] = e

    def get_teacher_initials(name):
        clean_name = re.sub(r'^(Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)\s*', '', name, flags=re.IGNORECASE).strip()
        parts = clean_name.split()
        return "".join([p[0].upper() for p in parts if p])

    response = HttpResponse(content_type='application/pdf')
    safe_dept = "".join([c for c in department.code if c.isalnum() or c in ('_', '-')]).rstrip()
    response['Content-Disposition'] = f'attachment; filename="{safe_dept}_master_timetable.pdf"'

    # Page setup: Printable area = 792 - 2*(0.2*72) = 763.2 pt available width
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        leftMargin=0.2 * inch,
        rightMargin=0.2 * inch,
        topMargin=0.2 * inch,
        bottomMargin=0.2 * inch
    )

    elements = []
    styles = getSampleStyleSheet()

    num_batches = max(1, len(batches))

    # Font sizing & padding adjusted for single-line fit without side overflow
    if num_batches >= 6:
        body_font_size, header_font_size = 5.0, 6.0
        padding_v = 1.5
    else:
        body_font_size, header_font_size = 6.0, 7.0
        padding_v = 2.5

    leading_body = body_font_size + 1.0
    leading_hdr = header_font_size + 1.2

    title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], alignment=1, fontSize=10, leading=11, fontName="Helvetica-Bold")
    sub_title_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], alignment=1, fontSize=8, leading=9, fontName="Helvetica-Bold")

    elements.append(Paragraph(f"DEPARTMENT OF {department.name.upper()}", title_style))
    elements.append(Paragraph("TIME TABLE (MASTER CHART)", sub_title_style))
    elements.append(Spacer(1, 2))

    headers = ['DAY', 'SEM']
    for p in PERIODS_LIST:
        headers.append(f"P{p}<br/>({PERIOD_TIMES[p]})")
        if p == 3:
            headers.append("LUNCH<br/>01-02")
    headers.append("Room")

    hdr_cell_style = ParagraphStyle('TH', fontSize=header_font_size, leading=leading_hdr, alignment=1, fontName="Helvetica-Bold")
    table_data = [[Paragraph(h, hdr_cell_style) for h in headers]]

    cell_style = ParagraphStyle('TD', fontSize=body_font_size, leading=leading_body, alignment=1)
    cell_bold_style = ParagraphStyle('TDBold', fontSize=body_font_size, leading=leading_body, alignment=1, fontName="Helvetica-Bold")

    table_style_cmd = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E9ECEF')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding_v),
        ('TOPPADDING', (0, 0), (-1, -1), padding_v),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.5),
    ]

    current_row = 1

    for day in DAYS_LIST:
        day_start_row = current_row
        
        for idx, batch in enumerate(batches):
            row = []
            row.append(Paragraph(f"<b>{day[:3].upper()}</b>", cell_bold_style) if idx == 0 else "")
            
            b_str = str(batch).replace("CSE Year ", "Y").replace("CSE ", "")
            row.append(Paragraph(f"<b>{b_str}</b>", cell_bold_style))

            assigned_room = set()

            for p in PERIODS_LIST:
                entry = grid[day][p].get(batch.id)
                if entry:
                    t_initials = get_teacher_initials(entry.teacher.name) if entry.teacher else ""
                    raw_code = entry.subject.code.strip() if entry.subject.code else ""
                    raw_name = entry.subject.name.strip() if entry.subject.name else ""
                    
                    if raw_code and len(raw_code) <= 8:
                        sub_disp = raw_code
                    elif raw_name:
                        clean_n = re.sub(r'\s*\((?:B\d+|Sec\s*[A-Z]|CSE-\d+|ECE-\d+|IT-\d+)\)', '', raw_name, flags=re.IGNORECASE).strip()
                        sub_disp = clean_n[:9] + '.' if len(clean_n) > 9 else clean_n
                    else:
                        sub_disp = "-"

                    r_name = entry.room.name.strip() if entry.room else ""
                    # Shorten verbose room strings to preserve cell space
                    r_name_short = r_name.replace("-3rdYr-", "-") if "-3rdYr-" in r_name else r_name
                    room_disp = f"[{r_name_short}]" if r_name_short else ""

                    cell_text = sub_disp
                    if room_disp:
                        cell_text += f" {room_disp}"
                    if t_initials:
                        cell_text += f" ({t_initials})"

                    row.append(Paragraph(cell_text, cell_style))

                    if entry.room:
                        assigned_room.add(r_name_short)
                else:
                    row.append(Paragraph("-", cell_style))

                if p == 3:
                    if idx == 0:
                        row.append(Paragraph("<b>LUNCH</b>", cell_bold_style))
                    else:
                        row.append("")

            room_str = ", ".join(sorted(list(assigned_room))) if assigned_room else "-"
            row.append(Paragraph(room_str, cell_style))

            table_data.append(row)
            current_row += 1

        if num_batches > 1:
            table_style_cmd.append(('SPAN', (0, day_start_row), (0, current_row - 1)))
            table_style_cmd.append(('SPAN', (5, day_start_row), (5, current_row - 1)))

    # CALIBRATED WIDTHS: Total sum = 10.5 inches (756 pt) < Printable Width (763.2 pt)
    col_widths = [
        0.40 * inch,  # DAY
        0.75 * inch,  # SEM
        1.35 * inch,  # P1
        1.35 * inch,  # P2
        1.35 * inch,  # P3
        0.65 * inch,  # LUNCH
        1.35 * inch,  # P4
        1.35 * inch,  # P5
        1.35 * inch,  # P6
        0.55 * inch   # Room
    ]
    
    master_table = Table(
        table_data, 
        colWidths=col_widths, 
        repeatRows=1
    )
    master_table.setStyle(TableStyle(table_style_cmd))
    elements.append(master_table)
    elements.append(Spacer(1, 3))

    # Inline Legends formatted cleanly without extending printable bounds
    leg_style = ParagraphStyle('LegInline', fontSize=4.8, leading=5.8)

    assigned_teacher_ids = all_entries.exclude(teacher=None).values_list('teacher_id', flat=True).distinct()
    assigned_teachers = Teacher.objects.filter(id__in=assigned_teacher_ids).order_by('name')
    teacher_items = [f"<b>{get_teacher_initials(t.name)}</b>: {t.name}" for t in assigned_teachers if t.name]
    teacher_text = "<b>Faculty Legend:</b> " + " | ".join(teacher_items)
    elements.append(Paragraph(teacher_text, leg_style))

    elements.append(Spacer(1, 1.5))

    assigned_subjects = Subject.objects.filter(id__in=all_entries.values_list('subject_id', flat=True).distinct()).order_by('name')
    subject_items = [f"<b>{s.code or s.name[:8]}</b>: {s.name}" for s in assigned_subjects]
    subject_text = "<b>Subject Legend:</b> " + " | ".join(subject_items)
    elements.append(Paragraph(subject_text, leg_style))

    doc.build(elements)
    return response