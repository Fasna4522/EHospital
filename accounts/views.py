from datetime import date

from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from adminpanel.models import Department
from patient.models import Appointment, Bill, HealthResource
from .models import User
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.db.models import Q
from datetime import datetime, date

from django.http import HttpResponse

def register_view(request):
    departments = Department.objects.select_related('location').all()
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        role = request.POST.get('role')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        place = request.POST.get('place')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        blood_group = request.POST.get('blood_group')
        department_id = request.POST.get('department')
        department = Department.objects.get(id=department_id) if department_id else None

        if password1 != password2:
            return render(request, 'accounts/register.html', {'error': 'Passwords do not match.'})

        if len(password1) < 8:
            return render(request, 'accounts/register.html', {'error': 'Password must be at least 8 characters.'})

        try:
            user = User.objects.create(
                username=username,
                email=email,
                role=role,
                place=place,
                password=make_password(password1),
                age=age if role == 'patient' else None,
                gender=gender if role == 'patient' else None,
                phone=phone if role == 'patient' else None,
                address=address if role == 'patient' else None,
                blood_group=blood_group if role == 'patient' else None,
                department=department if role == 'doctor' else None,
            )
            login(request, user)
            return redirect_user_based_on_role(user)
        except IntegrityError:
            return render(request, 'accounts/register.html', {'error': 'Username already taken.'})

    return render(request, 'accounts/register.html',{'departments': departments})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect_user_based_on_role(user)
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid credentials.'})

    return render(request, 'accounts/login.html')


def redirect_user_based_on_role(user):
    if user.role == 'patient':
        return redirect('patient_dashboard')
    elif user.role == 'doctor':
        return redirect('doctor_dashboard')
    elif user.role == 'admin':
        return redirect('admin_dashboard')


def patient_dashboard(request):
    today = date.today()
    current_time = datetime.now().time()

    upcoming_appointments = Appointment.objects.filter(
        patient=request.user,
        status='Confirmed'
    ).filter(
        Q(date__gt=today) | Q(date=today, time__gte=current_time)
    ).order_by('date', 'time')[:3]

    latest_resources = HealthResource.objects.all().order_by('-created_at')[:3]

    return render(request, 'patient/patient_base.html', {
        'upcoming_appointments': upcoming_appointments,
        'health_resources': latest_resources
    })


def doctor_dashboard(request):
    return render(request, 'doctor/doctor_base.html')

def admin_dashboard(request):
    total_patients = User.objects.filter(role='patient').count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_appointments = Appointment.objects.count()
    pending_bills = Bill.objects.filter(is_paid=False).count()

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'pending_bills': pending_bills,
    }
    return render(request, 'adminpanel/admin_base.html', context)



def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No user with that email.")
            return redirect('forgot_password')

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = request.build_absolute_uri(
            reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
        )

        html_content = render_to_string('reset_password_email.html', {
            'user': user,
            'reset_url': reset_url,
        })

        email_subject = 'Reset Your Password – E-Hospitality'
        msg = EmailMultiAlternatives(email_subject, '', None, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        messages.success(request, "Reset link sent to your email.")
        return redirect('login')

    return render(request, 'forgot_password.html')


def reset_password_view(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Password has been reset.")
                return redirect('login')
        else:
            form = SetPasswordForm(user)
        return render(request, 'reset_password.html', {'form': form})
    else:
        messages.error(request, "Invalid or expired link.")
        return redirect('forgot_password')

