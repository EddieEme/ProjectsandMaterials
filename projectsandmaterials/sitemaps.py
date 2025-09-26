# sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from books.models import Book, Category, BookType
from payments.models import Payment  # change this if your model is PaymentOption or similar

# 1. Static pages (just fixed paths, no slugs here)
class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "/",                
            "/services/",
            "/resources/",
            "/projects/",
            "/hire/",
            "/project_faculty/",
            "/project-list/",
            "/payment-checkout/",
            "/login-projects/",
            "/login-project-list/",
            "/login-payment-method/",
            "/verification-error/",
            "/upload-book/"
        ]

    def location(self, item):
        return item


# 2. Dynamic pages
class BookSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Book.objects.all()

    def location(self, obj):
        return reverse("books:product-details", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, "updated_at") else None


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse("books:category_books", args=[obj.slug])


class FacultySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return BookType.objects.all()

    def location(self, obj):
        return reverse("books:faculty", args=[obj.slug])


class PaymentOptionSitemap(Sitemap):
    changefreq = "yearly"
    priority = 0.3

    def items(self):
        return Payment.objects.all()

    def location(self, obj):
        return reverse("books:payment-method", args=[obj.slug])
