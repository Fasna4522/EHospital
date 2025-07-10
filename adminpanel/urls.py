from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('change-role/<int:user_id>/', views.change_role, name='change_role'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('facilities/', views.manage_facilities, name='manage_facilities'),
    path('appointments/', views.manage_appointments, name='manage_appointments'),
    path('location/edit/<int:location_id>/', views.edit_location, name='edit_location'),
    path('location/delete/<int:location_id>/', views.delete_location, name='delete_location'),
    path('department/edit/<int:dept_id>/', views.edit_department, name='edit_department'),
    path('department/delete/<int:dept_id>/', views.delete_department, name='delete_department'),

]
