from datetime import date, datetime
from django.utils.timezone import make_aware, now, is_aware
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

from accounts.models import User
from doctor.forms import PrescriptionForm
from patient.models import Appointment, MedicalHistory, Prescription, Bill

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def is_doctor(user):
    return user.is_authenticated and user.role == 'doctor'


@login_required
@user_passes_test(is_doctor)
def all_appointments(request):
    current_time = now()

    appointments_to_check = Appointment.objects.filter(
        doctor=request.user,
        status__in=['Pending', 'Confirmed']
    )

    for appt in appointments_to_check:
        appt_datetime = datetime.combine(appt.date, appt.time)
        appt_datetime = make_aware(appt_datetime) if not is_aware(appt_datetime) else appt_datetime

        if current_time > appt_datetime:
            appt.status = 'Cancelled'
            appt.save()

    appointments = Appointment.objects.filter(doctor=request.user).order_by('-date', '-time')
    return render(request, 'doctor/all_appointment.html', {'appointments': appointments})


@login_required
@user_passes_test(is_doctor)
def doctor_dashboard(request):
    today = date.today()
    current_time = now()

    for appt in Appointment.objects.filter(doctor=request.user, status__in=['Pending', 'Confirmed']):
        appt_datetime = make_aware(datetime.combine(appt.date, appt.time))
        if current_time > appt_datetime:
            appt.status = 'Cancelled'
            appt.save()

    upcoming = Appointment.objects.filter(doctor=request.user).exclude(status__in=['Cancelled', 'Completed']).order_by('date', 'time')
    today_appointments = upcoming.filter(date=today).count()
    patients_count = Appointment.objects.filter(doctor=request.user).values('patient').distinct().count()

    return render(request, 'doctor/dashboard.html', {
        'appointments': upcoming,
        'today_appointments': today_appointments,
        'patients_count': patients_count,
    })


@user_passes_test(is_doctor)
def patient_list(request):
    doctor = request.user
    patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient_id', flat=True).distinct()
    patients = User.objects.filter(id__in=patient_ids, role='patient')
    return render(request, 'doctor/patient_list.html', {'patients': patients})


@login_required
@user_passes_test(is_doctor)
def view_patient_history(request, patient_id):
    patient = User.objects.get(id=patient_id, role='patient')
    history = MedicalHistory.objects.filter(patient=patient).order_by('-date')

    if request.method == 'POST':
        diagnosis = request.POST.get('diagnosis')
        medications = request.POST.get('medications')
        allergies = request.POST.get('allergies')
        notes = request.POST.get('treatment_notes')

        MedicalHistory.objects.create(
            patient=patient,
            doctor=request.user,
            diagnosis=diagnosis,
            medications=medications,
            allergies=allergies,
            treatment_notes=notes
        )
        return redirect('view_patient_history', patient_id=patient.id)

    return render(request, 'doctor/view_patient_history.html', {
        'patient': patient,
        'history': history
    })


@login_required
@user_passes_test(is_doctor)
def update_appointment_status(request, appointment_id, action):
    appointment = Appointment.objects.get(id=appointment_id, doctor=request.user)

    if action == 'confirm':
        appointment.status = 'Confirmed'
    elif action == 'cancel':
        appointment.status = 'Cancelled'
    appointment.save()

    return redirect('doctor_dashboard')


# --------- 🔴 MAIN PRESCRIPTION ENTRY POINT ----------
@login_required
@user_passes_test(is_doctor)
def prescribe_patient(request, patient_id, appointment_id):
    patient = get_object_or_404(User, id=patient_id)
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)

    if request.method == 'POST':
        diagnosis = request.POST.get('diagnosis')
        medications = request.POST.get('medications')
        notes = request.POST.get('notes')

        prescription = Prescription.objects.create(
            doctor=request.user,
            patient=patient,
            appointment=appointment,
            diagnosis=diagnosis,
            medications=medications,
            notes=notes
        )

        Bill.objects.create(
            prescription=prescription,
            patient=patient,
            amount=500,
            description="Consultation Fee"
        )

        appointment.status = 'Completed'
        appointment.save()

        messages.success(request, "Prescription submitted successfully. Bill generated.")
        return redirect('prescribe_patient', patient_id=patient.id, appointment_id=appointment.id)

    prescriptions = Prescription.objects.filter(patient=patient).order_by('-date_issued')
    return render(request, 'doctor/prescribe.html', {
        'patient': patient,
        'appointment': appointment,
        'prescriptions': prescriptions
    })

# ✅ Payment View (for patient)
@login_required
def pay_prescription_bill(request, pres_id):
    prescription = get_object_or_404(Prescription, id=pres_id, patient=request.user)
    bill = get_object_or_404(Bill, related_prescription=prescription, patient=request.user)

    if bill.is_paid:
        return redirect('view_prescription', pres_id=prescription.id)

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {'name': bill.description},
                'unit_amount': int(bill.amount * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/prescription/success/') + f'?bill_id={bill.id}',
        cancel_url=request.build_absolute_uri('/patient/my_bills/'),
    )

    bill.stripe_session_id = session.id
    bill.save()

    return redirect(session.url, code=303)


@login_required
def prescription_payment_success(request):
    bill_id = request.GET.get('bill_id')
    if bill_id:
        bill = get_object_or_404(Bill, id=bill_id, patient=request.user)
        bill.is_paid = True
        bill.save()
    return render(request, 'patient/payment_success.html')
