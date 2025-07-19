#!/usr/bin/env python3

import os 
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectsandmaterials.settings')
django.setup()

from subscriptions.models import SubscriptionPlan

SubscriptionPlan.objects.create(
    name="Basic",
    description="Access to Basic Documents, Limited Research Papers, Monthly Newsletter",
    price=9.99,
    duration=30,  # days
    download_limit=10,  # or set to 0 if unlimited
    features=[
        "Access to Basic Documents",
        "Limited Research Papers",
        "Monthly Newsletter"
    ]
)

SubscriptionPlan.objects.create(
    name="Premium",
    description="Full Document Access, Unlimited Research Papers, Monthly Newsletter, Priority Support",
    price=19.99,
    duration=30,
    download_limit=50,  # or 0 for unlimited
    features=[
        "Full Document Access",
        "Unlimited Research Papers",
        "Monthly Newsletter",
        "Priority Support"
    ]
)

SubscriptionPlan.objects.create(
    name="Enterprise",
    description="Complete Institutional Access, Unlimited Papers & Documents, Custom Research Support, Dedicated Account Manager",
    price=49.99,
    duration=30,
    download_limit=0,  # Unlimited
    features=[
        "Complete Institutional Access",
        "Unlimited Papers & Documents",
        "Custom Research Support",
        "Dedicated Account Manager"
    ]
)

