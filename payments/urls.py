from django.urls import path
from books.utils import download_book
from .import views

app_name = 'payments'

urlpatterns = [ 
    path('paystack/<int:book_id>/', views.pay_with_paystack, name='pay_with_paystack'),
    path('flutterwave/<int:book_id>/', views.pay_with_flutterwave, name='pay_with_flutterwave'),
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('flutterwave/callback/', views.flutterwave_callback, name='flutterwave_callback'),
    path('download/<uuid:token>/', download_book, name='download_book'),
]
