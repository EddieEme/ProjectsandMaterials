from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from books.models import Book


# Create your views here.
def subscription(request):
    if request.user.is_authenticated:
        return render(request, 'books/login-subscription.html')
    return render(request, 'books/subscription.html')



@login_required(login_url='books:user_login')
def login_subscription(request):
    return render(request, 'books/login-subscription.html')




def buyorsubscribe(request, id):
    if request.user.is_authenticated:
        return render(request, 'books/login-buyorsubscribe.html',)
    
    book = get_object_or_404(Book, id=id)
    stats = book.get_file_statistics()
    context = {
        "book": book,
        "page_count": stats["pages"],
        "word_count": stats["words"],
        }
    return render(request, 'books/buyorsubscribe.html', context)

@login_required(login_url='books:user_login')
def login_buyorsubscribe(request, id):
    book = get_object_or_404(Book, id=id)
    stats = book.get_file_statistics()
    context = {
        "book": book,
        "page_count": stats["pages"],
        "word_count": stats["words"],
        }
    return render(request, 'books/login-buyorsubscribe.html', context)