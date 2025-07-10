import stripe
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import make_aware

from .models import Appointment, MedicalHistory, Bill, HealthResource, Prescription
from accounts.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, date, time, timedelta


stripe.api_key = settings.STRIPE_SECRET_KEY

def generate_time_slots(start, end, interval_minutes=15):
    slots = []
    current = datetime.combine(date.today(), start)
    end_time = datetime.combine(date.today(), end)
    while current <= end_time:
        formatted_time = current.strftime('%I:%M %p')
        if formatted_time not in ['01:15 PM', '01:30 PM', '01:45 PM']:
            slots.append(formatted_time)
        current += timedelta(minutes=interval_minutes)
    return slots

def book_appointment(request):
    doctors = User.objects.filter(role='doctor').select_related('department__location')
    selected_doctor_id = request.GET.get('doctor') or request.POST.get('doctor')
    selected_date = request.GET.get('date') or request.POST.get('date')
    available_slots = []

    if request.method == 'POST':
        time_str = request.POST.get('time')
        reason = request.POST.get('reason')

        try:
            time_selected = datetime.strptime(time_str, '%I:%M %p').time()  # FIXED
        except ValueError:
            return render(request, 'patient/book_appointment.html', {
                'doctors': doctors,
                'selected_doctor_id': selected_doctor_id,
                'selected_date': selected_date,
                'error': 'Invalid time format.',
            })

        doctor = User.objects.get(id=selected_doctor_id)

        if Appointment.objects.filter(doctor=doctor, date=selected_date, time=time_selected).exists():
            return render(request, 'patient/book_appointment.html', {
                'doctors': doctors,
                'doctor':doctor,
                'selected_doctor_id': selected_doctor_id,
                'selected_date': selected_date,
                'error': 'Selected slot is already booked.'
            })

        Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            date=selected_date,
            time=time_selected,
            reason=reason
        )
        return redirect('my_appointments')


    elif selected_doctor_id and selected_date:
        doctor = User.objects.get(id=selected_doctor_id)
        all_slots = generate_time_slots(time(9, 0), time(17, 0))
        blocked_times = ['01:15 PM', '01:30 PM', '01:45 PM']
        all_slots = [slot for slot in all_slots if slot not in blocked_times]

        if selected_date == date.today().isoformat():
            now = datetime.now().time()
            all_slots = [slot for slot in all_slots if datetime.strptime(slot, '%I:%M %p').time() > now]

        booked_slots = Appointment.objects.filter(doctor=doctor, date=selected_date).values_list('time', flat=True)
        booked_slots = [t.strftime('%I:%M %p') for t in booked_slots]
        available_slots = [slot for slot in all_slots if slot not in booked_slots]

    return render(request, 'patient/book_appointment.html', {
        'doctors': doctors,
        'selected_doctor_id': selected_doctor_id,
        'selected_date': selected_date,
        'available_slots': available_slots,
        'today': date.today().isoformat()
    })

@login_required
def my_appointments(request):
    appointments = Appointment.objects.filter(patient=request.user).order_by('-date', '-time')
    return render(request, 'patient/my_appointments.html', {
        'appointments': appointments,
        'today': date.today().isoformat()
    })


@login_required
def medical_history_view(request):
    history = MedicalHistory.objects.filter(patient=request.user).order_by('-date')
    return render(request, 'patient/medical_history.html', {'history': history})



@login_required
def my_bills_view(request):
    bills = Bill.objects.filter(patient=request.user).order_by('-date_issued')
    return render(request, 'patient/my_bills.html', {'bills': bills})


@login_required
def pay_bill(request, bill_id):
    bill = Bill.objects.get(id=bill_id, patient=request.user)

    if bill.is_paid:
        return JsonResponse({'message': 'Bill already paid.'})

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': bill.description,
                },
                'unit_amount': int(bill.amount * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/patient/payment-success/') + f'?bill_id={bill.id}',
        cancel_url=request.build_absolute_uri('/patient/my-bills/'),
    )

    bill.stripe_session_id = session.id
    bill.save()

    return redirect(session.url, code=303)

@login_required
def payment_success(request):
    bill_id = request.GET.get('bill_id')
    if bill_id:
        bill = Bill.objects.get(id=bill_id, patient=request.user)
        bill.is_paid = True
        bill.save()
    return render(request, 'patient/payment_success.html')


@login_required
def health_resources_view(request):
    resources = HealthResource.objects.all().order_by('-created_at')
    return render(request, 'patient/health_resources.html', {'resources': resources})

@login_required
def reschedule_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)

    if request.method == 'POST':
        new_date = request.POST.get('new_date')
        new_time_str = request.POST.get('new_time')

        try:
            new_time = datetime.strptime(new_time_str, '%I:%M %p').time()
        except ValueError:
            messages.error(request, "Invalid time format.")
            return redirect('my_appointments')

        conflict = Appointment.objects.filter(
            doctor=appointment.doctor,
            date=new_date,
            time=new_time,
        ).exclude(id=appointment.id).exists()

        if conflict:
            messages.error(request, "Selected time slot is not available.")
        else:
            appointment.date = new_date
            appointment.time = new_time
            appointment.status = 'Pending'
            appointment.save()
            messages.success(request, "Appointment rescheduled successfully.")

        return redirect('my_appointments')

    available_slots = generate_time_slots(time(9, 0), time(17, 0))
    return render(request, 'patient/my_appointments.html', {
        'appointment': appointment,
        'available_slots': available_slots
    })

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    if request.method == 'POST':
        appointment.status = 'Cancelled'
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")
    return redirect('my_appointments')


@login_required
def get_available_slots(request, doctor_id, appointment_id, selected_date):
    doctor = get_object_or_404(User, id=doctor_id)
    selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    all_slots = []
    current = datetime.combine(date.today(), time(9, 0))
    end = datetime.combine(date.today(), time(17, 0))
    while current <= end:
        if current.time() < time(13, 0) or current.time() >= time(14, 0):  # 1pm–2pm lunch break
            all_slots.append(current.strftime('%I:%M %p'))
        current += timedelta(minutes=15)

    # Remove past times if today
    if selected_date == date.today():
        now = datetime.now().time()
        all_slots = [slot for slot in all_slots if datetime.strptime(slot, '%I:%M %p').time() > now]

    # Remove already booked
    booked = Appointment.objects.filter(
        doctor=doctor, date=selected_date
    ).exclude(id=appointment_id).values_list('time', flat=True)

    booked_slots = [t.strftime('%I:%M %p') for t in booked]
    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    return JsonResponse({'slots': available_slots})


@login_required
def my_prescriptions(request):
    prescriptions = Prescription.objects.filter(patient=request.user).order_by('-date_issued')
    return render(request, 'patient/my_prescriptions.html', {'prescriptions': prescriptions})


@login_required
def pay_prescription_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id, patient=request.user)
    if bill.is_paid:
        return redirect('my_prescriptions')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': bill.description,
                },
                'unit_amount': int(bill.amount * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/patient/prescription-success/') + f'?bill_id={bill.id}',
        cancel_url=request.build_absolute_uri('/patient/my-prescriptions/'),
    )

    bill.prescription.stripe_session_id = session.id
    bill.prescription.save()

    return redirect(session.url, code=303)


@login_required
def prescription_success(request):
    bill_id = request.GET.get('bill_id')
    bill = get_object_or_404(Bill, id=bill_id, patient=request.user)

    if not bill.is_paid:
        bill.is_paid = True
        bill.prescription.is_paid = True
        bill.prescription.save()
        bill.save()

    return render(request, 'patient/payment_success.html')
