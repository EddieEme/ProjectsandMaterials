from django.urls import path
from . import views


app_name = "subscriptions"

urlpatterns = [
    path('subscription/', views.subscription, name='subscription'),
    path('buyorsubscribe/<int:id>/', views.buyorsubscribe, name='buyorsubscribe'),
    path('subscription_payment/<int:id>/', views.subscription_payment_method, name = 'subscription_payment'),
    
    path('subscriptions/initiate/<int:plan_id>/', views.initiate_subscription_payment, name='initiate_subscription_payment'),
    path('subscriptions/callback/', views.subscription_payment_callback, name='subscription_payment_callback'),
    path('subscriptions/success/<int:transaction_id>/', views.subscription_payment_success, name='subscription_payment_success'),

    # path('success/<int:transaction_id>/', views.payment_success, name='payment_success'),
    # path('failed/', views.payment_failed, name='payment_failed'),
    # path('login-subscription/', views.login_subscription, name='login-subscription'),
    # path('login-buyorsubscribe/<int:id>/', views.login_buyorsubscribe, name='login-buyorsubscribe'),
]

