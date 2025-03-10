from django.urls import path
from . import views


app_name = "subscriptions"

urlpatterns = [
    path('subscription/', views.subscription, name='subscription'),
    path('buyorsubscribe/<int:id>/', views.buyorsubscribe, name='buyorsubscribe'),
    path('login-subscription/', views.login_subscription, name='login-subscription'),
    path('login-buyorsubscribe/<int:id>/', views.login_buyorsubscribe, name='login-buyorsubscribe'),
]

