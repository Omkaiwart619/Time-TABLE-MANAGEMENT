from django.contrib import admin
from .models import Department, Batch, Room, Teacher, Subject, TimetableEntry

admin.site.register(Department)
admin.site.register(Batch)
admin.site.register(Room)
admin.site.register(Teacher)
admin.site.register(Subject)
admin.site.register(TimetableEntry)