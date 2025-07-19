from pyexpat.errors import messages
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from books.models import Book
from .models import SubscriptionPlan

import json
import uuid
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.urls import reverse
from decimal import Decimal
from subscriptions.models import SubscriptionPlan, UserSubscription
import logging

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY


# Create your views here.
def subscription(request):
    plans = SubscriptionPlan.objects.all()
    
    context = {
        'plans': plans 
    }
    
    template = 'books/login-subscription.html' if request.user.is_authenticated else 'books/subscription.html'
    
    return render(request, template, context)




def buyorsubscribe(request, id):
    book = get_object_or_404(Book, id=id)
    stats = book.get_file_statistics()
    context = {
        "book": book,
        "page_count": stats["pages"],
        "word_count": stats["words"],
        }
    template = 'books/login-buyorsubscribe.html' if request.user.is_authenticated  else 'books/buyorsubscribe.html'
    return render(request, template, context)

@login_required(login_url='users:user_login')
def subscription_payment_method(request, id):
    plan = get_object_or_404(SubscriptionPlan, id=id)
    
    context ={
        "plan":plan,
    }
    return render(request, 'books/subscription-payment-method.html', context)
    
    
    


@login_required
def initiate_subscription_payment(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    # Check if user already has an active subscription
    active_sub = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if active_sub and active_sub.plan == plan:
        messages.warning(request, f"You already have an active {plan.name} subscription.")
        return redirect('subscription_plans')
    
    # Generate a unique reference
    reference = f"sub_{uuid.uuid4().hex[:10]}"
    
    # Create a pending subscription
    subscription = UserSubscription.objects.create(
        user=request.user,
        plan=plan,
        status='pending',
        payment_reference=reference
    )
    
    
    # Initialize Paystack payment
    callback_url = request.build_absolute_uri(
        reverse('subscription_payment_callback')
    )
    
    paystack_url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "email": request.user.email,
        "amount": int(plan.price * 100),  # Convert to kobo
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {
            "plan_id": plan.id,
            "subscription_id": subscription.id,
            "user_id": request.user.id,
            "custom_fields": [
                {
                    "display_name": "Subscription Plan",
                    "variable_name": "subscription_plan",
                    "value": plan.name
                }
            ]
        }
    }
    
    try:
        response = requests.post(paystack_url, json=data, headers=headers)
        response_data = response.json()
        
        if response_data.get("status") == True:
            authorization_url = response_data["data"]["authorization_url"]
            return redirect(authorization_url)
        else:
            messages.error(request, "Payment initialization failed. Please try again.")
            logger.error(f"Paystack initialization failed: {response_data}")
            return redirect('subscription_plans')
            
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        logger.error(f"Error initializing Paystack payment: {str(e)}")
        return redirect('subscription_plans')

@csrf_exempt
def subscription_payment_callback(request):
    reference = request.GET.get('reference')
    
    if not reference:
        logger.error("No reference provided in callback")
        return redirect('payment_failed')
    
    # Verify payment with Paystack
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    
    try:
        response = requests.get(verify_url, headers=headers)
        response_data = response.json()
        
        if not response_data.get("status"):
            logger.error(f"Paystack verification failed: {response_data}")
            return redirect('payment_failed')
        
        transaction_data = response_data.get("data", {})
        metadata = transaction_data.get("metadata", {})
        
        # Get subscription and transaction records
        subscription_id = metadata.get("subscription_id")
        if not subscription_id:
            logger.error("No subscription_id in metadata")
            return redirect('payment_failed')
            
        try:
            subscription = UserSubscription.objects.get(id=subscription_id)
            transaction = PaymentTransaction.objects.get(reference=reference)
            
            if transaction_data.get("status") == "success":
                # Payment successful - activate subscription
                subscription.status = 'active'
                subscription.save()
                
                transaction.status = 'successful'
                transaction.paystack_response = transaction_data
                transaction.save()
                
                return redirect('subscription_payment_success', transaction_id=transaction.id)
            else:
                # Payment failed
                subscription.status = 'cancelled'
                subscription.save()
                
                transaction.status = 'failed'
                transaction.paystack_response = transaction_data
                transaction.save()
                
                return redirect('payment_failed')
                
        except (UserSubscription.DoesNotExist, PaymentTransaction.DoesNotExist) as e:
            logger.error(f"Database record not found: {str(e)}")
            return redirect('payment_failed')
            
    except Exception as e:
        logger.error(f"Error verifying Paystack payment: {str(e)}")
        return redirect('payment_failed')

@login_required
def subscription_payment_success(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    subscription = transaction.subscription
    
    return render(request, 'payments/subscription_success.html', {
        'transaction': transaction,
        'subscription': subscription
    })

@login_required
def subscription_plans(request):
    plans = SubscriptionPlan.objects.all().order_by('price')
    active_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    return render(request, 'payments/subscription_plans.html', {
        'plans': plans,
        'active_subscription': active_subscription,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    })