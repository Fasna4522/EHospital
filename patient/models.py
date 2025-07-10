from django.db import models
from django.conf import settings
from datetime import datetime

from django.utils import timezone


class Appointment(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    date = models.DateField()
    time = models.TimeField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    ], default='Pending')

    def __str__(self):
        return f"{self.patient.username} with {self.doctor.username} on {self.date} at {self.time}"


class MedicalHistory(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medical_histories')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    diagnosis = models.TextField()
    medications = models.TextField()
    allergies = models.TextField(blank=True, null=True)
    treatment_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.patient.username} - {self.date}"


class Bill(models.Model):
    prescription = models.OneToOneField('Prescription', on_delete=models.CASCADE, null=True, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date_issued = models.DateField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Bill #{self.id} - {self.patient.username}"


class HealthResource(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    link = models.URLField(blank=True, null=True)
    uploaded_file = models.FileField(upload_to='health_resources/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Prescription(models.Model):
    is_paid = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions_given')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions_received')
    diagnosis = models.TextField()
    medications = models.TextField(help_text="List medications with dosage")
    notes = models.TextField(blank=True)
    date_issued = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Prescription for {self.patient.username} by Dr. {self.doctor.username} on {self.date_issued.strftime('%Y-%m-%d')}"
