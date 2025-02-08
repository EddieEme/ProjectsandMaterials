from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

def home(request):
    return render(request, 'books/index.html')


def projects(request):
    return render(request, 'books/project.html')

def projectList(request):
    return render(request, 'books/list-project.html')


def user_login(request):
    return render(request, 'books/login.html')

def register(request):
    return render(request, 'books/register.html')

def product_details(request, id):
    return render(request, 'books/product-details.html', {'id': id})

def department(request):
    return render(request, 'books/department.html')


def buyorsubscribe(request):
    return render(request, 'books/buyorsubscribe.html')

def subscription(request):
    return render(request, 'books/subscription.html')

def payment_method(request):
    return render(request, 'books/payment-method.html')




@login_required(login_url='books:login')
def login_projects(request):
    return render(request, 'books/login-project.html')

@login_required(login_url='books:login') 
def login_projectList(request):
    return render(request, 'books/login-list-project.html')

@login_required(login_url='books:login')
def login_product_details(request, id):
    return render(request, 'books/login-product-details.html', {'id': id})

@login_required(login_url='books:login')
def login_department(request):
    return render(request, 'books/login-department.html')

@login_required(login_url='books:login')
def login_buyorsubscribe(request):
    return render(request, 'books/login-buyorsubscribe.html')

@login_required(login_url='books:login')
def login_subscription(request):
    return render(request, 'books/login-subscription.html')

@login_required(login_url='books:login')
def login_payment_method(request):
    return render(request, 'books/login-payment-method.html')

def login_home(request):
    
    return render(request, "books/login-index.html")



