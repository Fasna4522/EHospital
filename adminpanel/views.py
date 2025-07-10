from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import User
from django.contrib.auth.decorators import login_required, user_passes_test

from adminpanel.models import Location, Department
from patient.models import Appointment, Prescription, Bill


def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.exclude(role='admin').order_by('role', 'username')
    return render(request, 'adminpanel/user_list.html', {'users': users})

@user_passes_test(is_admin)
def change_role(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        user.role = new_role
        user.save()
    return redirect('user_list')

@user_passes_test(is_admin)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
    return redirect('user_list')


@user_passes_test(is_admin)
def manage_facilities(request):
    locations = Location.objects.all()
    departments = Department.objects.select_related('location').all()

    if request.method == 'POST':
        if 'add_location' in request.POST:
            name = request.POST.get('location_name')
            address = request.POST.get('location_address')
            Location.objects.create(name=name, address=address)
            messages.success(request, "Location added successfully.")
        elif 'add_department' in request.POST:
            location_id = request.POST.get('department_location')
            name = request.POST.get('department_name')
            desc = request.POST.get('department_description')
            location = Location.objects.get(id=location_id)
            Department.objects.create(location=location, name=name, description=desc)
            messages.success(request, "Department added successfully.")
        return redirect('manage_facilities')

    return render(request, 'adminpanel/manage_facilities.html', {
        'locations': locations,
        'departments': departments
    })


@user_passes_test(is_admin)
def manage_appointments(request):
    appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-date', '-time')

    # Optional filters (can extend)
    doctor_name = request.GET.get('doctor')
    patient_name = request.GET.get('patient')

    if doctor_name:
        appointments = appointments.filter(doctor__username__icontains=doctor_name)
    if patient_name:
        appointments = appointments.filter(patient__username__icontains=patient_name)

    return render(request, 'adminpanel/manage_appointments.html', {
        'appointments': appointments,
        'doctor_name': doctor_name or '',
        'patient_name': patient_name or ''
    })


@user_passes_test(is_admin)
def edit_location(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    if request.method == 'POST':
        location.name = request.POST.get('name')
        location.address = request.POST.get('address')
        location.save()
        messages.success(request, "Location updated.")
    return redirect('manage_facilities')


@user_passes_test(is_admin)
def delete_location(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    if request.method == 'POST':
        location.delete()
        messages.success(request, "Location deleted.")
    return redirect('manage_facilities')


@user_passes_test(is_admin)
def edit_department(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        dept.name = request.POST.get('name')
        dept.description = request.POST.get('description')
        location_id = request.POST.get('location')
        dept.location = Location.objects.get(id=location_id)
        dept.save()
        messages.success(request, "Department updated.")
    return redirect('manage_facilities')


@user_passes_test(is_admin)
def delete_department(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        dept.delete()
        messages.success(request, "Department deleted.")
    return redirect('manage_facilities')

