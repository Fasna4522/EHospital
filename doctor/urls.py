from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:patient_id>/history/', views.view_patient_history, name='view_patient_history'),
    path('appointments/<int:appointment_id>/<str:action>/', views.update_appointment_status, name='update_appointment_status'),
    path('all_appointments/', views.all_appointments, name='appointment'),
    path('prescribe/<int:patient_id>/<int:appointment_id>/', views.prescribe_patient, name='prescribe_patient'),
]
