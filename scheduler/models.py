from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Batch(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='batches')
    year = models.IntegerField()  # 1, 2, 3, 4
    section = models.CharField(max_length=10, default='A')  # e.g., "A", "B"
    strength = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['department', 'year', 'section'], 
                name='unique_batch_per_dept_year_section'
            )
        ]

    def __str__(self):
        return f"{self.department.code} Year {self.year} - {self.section}"


class Room(models.Model):
    ROOM_TYPES = [('classroom', 'Classroom'), ('lab', 'Lab')]
    name = models.CharField(max_length=50, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='classroom')
    capacity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='teachers')
    max_classes_per_week = models.IntegerField(default=16)  # Workload cap
    is_lab_incharge = models.BooleanField(default=False)
    lab_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='subjects')
    classes_per_week = models.IntegerField(default=3)
    is_lab = models.BooleanField(default=False)
    required_room = models.ForeignKey(
        Room, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='subjects_requiring'
    )

    def __str__(self):
        return f"{self.name} ({self.batch})"


class TimetableEntry(models.Model):
    DAYS = [
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday')
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='timetable_entries')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='timetable_entries')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='timetable_entries')
    day = models.CharField(max_length=10, choices=DAYS)
    period = models.IntegerField()  # 1 to 6
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['day', 'period']
        constraints = [
            models.UniqueConstraint(fields=['day', 'period', 'room'], name='unique_room_slot'),
            models.UniqueConstraint(fields=['day', 'period', 'teacher'], name='unique_teacher_slot'),
            models.UniqueConstraint(fields=['day', 'period', 'batch'], name='unique_batch_slot'),
        ]

    def __str__(self):
        return f"{self.subject.name} - {self.day} P{self.period}"


# ==========================================
# SIGNALS FOR AUTOMATIC USER ACCOUNT CREATION
# ==========================================

@receiver(post_save, sender=Teacher)
def auto_create_teacher_user(sender, instance, created, **kwargs):
    if created and not instance.user:
        clean_name = instance.name.lower().replace('.', '').replace(' ', '_')
        username = f"teacher_{clean_name}"
        
        # Ensure unique username if duplicates exist
        count = 1
        base_username = username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{count}"
            count += 1
            
        user = User.objects.create_user(username=username, password='teacher123')
        instance.user = user
        instance.save(update_fields=['user'])


@receiver(post_save, sender=Batch)
def auto_create_batch_user(sender, instance, created, **kwargs):
    if created and not instance.user:
        dept_code = instance.department.code.lower()
        clean_section = instance.section.lower().replace(' ', '_')
        username = f"batch_{dept_code}_{instance.year}_{clean_section}"
        
        count = 1
        base_username = username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{count}"
            count += 1
            
        user = User.objects.create_user(username=username, password='student123')
        instance.user = user
        instance.save(update_fields=['user'])