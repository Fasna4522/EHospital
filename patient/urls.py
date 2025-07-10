from django.urls import path
from . import views

urlpatterns = [
    path('book/', views.book_appointment, name='book_appointment'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('medical-history/', views.medical_history_view, name='medical_history'),
    path('my-bills/', views.my_bills_view, name='my_bills'),
    path('pay-bill/<int:bill_id>/', views.pay_bill, name='pay_bill'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('health-resources/', views.health_resources_view, name='health_resources'),
    path('reschedule/<int:appointment_id>/', views.reschedule_appointment, name='reschedule_appointment'),
    path('get-slots/<int:doctor_id>/<int:appointment_id>/<str:selected_date>/', views.get_available_slots, name='get_available_slots'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('my-prescriptions/', views.my_prescriptions, name='my_prescriptions'),
    path('pay-prescription/<int:bill_id>/', views.pay_prescription_bill, name='pay_prescription_bill'),
    path('prescription-success/', views.prescription_success, name='prescription_success'),
]
