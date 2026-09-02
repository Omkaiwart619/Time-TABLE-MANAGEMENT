from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),

    path('departments/', views.department_list, name='department_list'),
    path('departments/add/', views.department_add, name='department_add'),
    path('departments/delete/<int:pk>/', views.department_delete, name='department_delete'),

    path('rooms/', views.room_list, name='room_list'),
    path('rooms/add/', views.room_add, name='room_add'),
    path('rooms/delete/<int:pk>/', views.room_delete, name='room_delete'),

    path('batches/', views.batch_list, name='batch_list'),
    path('batches/add/', views.batch_add, name='batch_add'),
    path('batches/delete/<int:pk>/', views.batch_delete, name='batch_delete'),

    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.teacher_add, name='teacher_add'),
    path('teachers/delete/<int:pk>/', views.teacher_delete, name='teacher_delete'),

    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/add/', views.subject_add, name='subject_add'),
    path('subjects/delete/<int:pk>/', views.subject_delete, name='subject_delete'),

    path('timetable/generate/', views.generate_timetable_view, name='timetable_generate'),
    path('timetable/view/', views.timetable_view, name='timetable_view'),
    path('timetable/edit/<int:pk>/', views.timetable_edit, name='timetable_edit'),
    path('timetable/edit-slot/', views.edit_timetable_slot, name='edit_timetable_slot'),  # <--- AJAX ENDPOINT
    path('timetable/export/', views.timetable_export_pdf, name='timetable_export_pdf'),
    path('my-timetable/', views.my_timetable, name='my_timetable'),
    path('timetable/master-export/', views.master_pdf_export, name='master_pdf_export'),
]