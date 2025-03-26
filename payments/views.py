import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal
from books.models import Book
from . models import Order, Payment
from .models import RoyaltyManager, WithdrawalRequest, Royalty, Download
import logging

logger = logging.getLogger(__name__)



PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
FLUTTERWAVE_SECRET_KEY = settings.FLUTTERWAVE_SECRET_KEY

def pay_with_paystack(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Check if user already paid for this book
    existing_order = Order.objects.filter(user=request.user, book=book, status="completed").first()
    
    if existing_order:
        return redirect("/user-dashboard/")  # Redirect to dashboard if already paid

    # Create a new order
    order = Order.objects.create(user=request.user, book=book, price=book.price, status="pending")

    callback_url = request.build_absolute_uri('/payments/paystack/callback/')
    paystack_url = "https://api.paystack.co/transaction/initialize"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "email": request.user.email,
        "amount": int(order.price * 100),  # Paystack uses kobo
        "callback_url": callback_url,
        "metadata": { 
            "order_id": order.id
        }
    }
    
    response = requests.post(paystack_url, json=data, headers=headers)
    response_data = response.json()
    
    if response_data.get("status") == True:
        authorization_url = response_data["data"]["authorization_url"]
        return redirect(authorization_url)
    else:
        return JsonResponse({"error": "Payment initialization failed"}, status=400)


def pay_with_flutterwave(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    order = Order.objects.create(user=request.user, book=book, price=book.price)

    callback_url = request.build_absolute_uri('/flutterwave/callback/')
    flutterwave_url = "https://api.flutterwave.com/v3/payments"

    headers = {
        "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "tx_ref": f"TX-{order.id}",
        "amount": str(order.price),
        "currency": "NGN",
        "redirect_url": callback_url,
        "customer": {
            "email": request.user.email,
            "name": request.user.get_full_name(),
        },
        "customizations": {
            "title": "Book Purchase",
            "description": f"Payment for {book.title}",
        },
    }

    response = requests.post(flutterwave_url, json=data, headers=headers)

    # ✅ First, check response status
    if response.status_code != 200:
        print(f"Error: {response.status_code}, Response Text: {response.text}")  # Debugging
        return JsonResponse({"error": "Failed to initialize payment"}, status=response.status_code)

    # ✅ Try parsing JSON safely
    try:
        response_data = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Invalid JSON response from Flutterwave: {response.text}")  # Debugging
        return JsonResponse({"error": "Invalid response from payment gateway"}, status=500)

    # ✅ Check if payment was successfully initialized
    if response_data.get("status") == "success":
        authorization_url = response_data["data"]["link"]
        return redirect(authorization_url)
    else:
        return JsonResponse({"error": response_data.get("message", "Payment initialization failed")}, status=400)
    
def paystack_callback(request):
    reference = request.GET.get('reference')

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    response = requests.get(verify_url, headers=headers)

    try:
        response_data = response.json()
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON response from Paystack"}, status=400)

    # Ensure metadata exists
    metadata = response_data.get("data", {}).get("metadata", {})

    if not isinstance(metadata, dict):
        return JsonResponse({"error": "Metadata is missing or not a dictionary"}, status=400)

    order_id = metadata.get("order_id")
    if not order_id:
        return JsonResponse({"error": "Order ID not found in metadata"}, status=400)

    # Fetch the order
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    # Update order status if payment is successful
    if response_data["data"].get("status") == "success":
        order.status = "completed"
        order.save()

        Payment.objects.create(
            user=order.user,
            order=order,
            amount=order.price,
            payment_method="paystack",
            status="completed",
            transaction_id=reference
        )

        return redirect("/users/user-dashboard/")

    return redirect("payment_failed")



@csrf_exempt  # Allow webhook POST requests without CSRF token
def flutterwave_callback(request):
    if request.method == "GET":
        # Handle redirect after payment
        status = request.GET.get("status")  # Payment status (successful, cancelled, failed)
        tx_ref = request.GET.get("tx_ref")  # Transaction reference

        logger.info(f"Flutterwave Redirect Callback Received: status={status}, tx_ref={tx_ref}")

        if not tx_ref:
            return redirect("payment_failed")  # No transaction reference, redirect to failure page

        try:
            order_id = int(tx_ref.split("-")[1])
            order = Order.objects.get(id=order_id)

            if status == "successful":
                order.status = "completed"
                order.save()
                
                # Create a Payment record
                Payment.objects.create(
                    user=order.user,
                    order=order,
                    amount=order.price,
                    payment_method="flutterwave",
                    status="completed",
                    transaction_id=tx_ref
                )

                return redirect("payment_success")  # Redirect to success page

            elif status in ["failed", "cancelled"]:
                order.status = "cancelled"
                order.save()
                return redirect("payment_failed")  # Redirect to failure page

        except Order.DoesNotExist:
            logger.error(f"Order with ID {order_id} not found")
            return redirect("payment_failed")

    elif request.method == "POST":
        # Handle webhook POST request from Flutterwave
        try:
            payload = json.loads(request.body)  # Parse incoming JSON data
            logger.info(f"Flutterwave Webhook Received: {payload}")

            tx_ref = payload.get("txRef")  # Transaction reference
            status = payload.get("status")  # Status from webhook
            transaction_id = payload.get("transaction_id")  # Flutterwave transaction ID

            if not tx_ref:
                logger.warning("Missing tx_ref in webhook data")
                return JsonResponse({"error": "Invalid request"}, status=400)

            order_id = int(tx_ref.split("-")[1])
            order = Order.objects.get(id=order_id)

            if status == "successful":
                order.status = "completed"
                order.save()

                # Store payment details
                Payment.objects.create(
                    user=order.user,
                    order=order,
                    amount=order.price,
                    payment_method="flutterwave",
                    status="completed",
                    transaction_id=transaction_id
                )
                
                return JsonResponse({"message": "Payment processed successfully"}, status=200)

            elif status in ["failed", "cancelled"]:
                order.status = "cancelled"
                order.save()
                return JsonResponse({"message": "Payment failed or cancelled"}, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook request")
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        except Order.DoesNotExist:
            logger.error(f"Order with ID {order_id} not found")
            return JsonResponse({"error": "Order not found"}, status=404)

    return HttpResponse(status=405)