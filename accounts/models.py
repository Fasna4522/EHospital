from django.contrib.auth.models import AbstractUser
from django.db import models

from adminpanel.models import Department


class User(AbstractUser):
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    place = models.CharField(max_length=100, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    blood_group = models.CharField(max_length=3, null=True, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def display_name(self):
        if self.role == 'doctor':
            return f"Dr. {self.get_full_name() or self.username}"
        return self.get_full_name() or self.username