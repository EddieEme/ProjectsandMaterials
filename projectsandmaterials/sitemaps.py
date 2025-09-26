# sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from books.models import Book, Category, BookType
from payments.models import Payment


class BaseSitemap(Sitemap):
    protocol = "https"  # force https
    domain = settings.SITE_URL.replace("http://", "").replace("https://", "").rstrip("/")

    def get_urls(self, page=1, site=None, protocol=None):
        return super().get_urls(page=page, site=type("Site", (), {
            "domain": self.domain,
            "name": self.domain
        })(), protocol=self.protocol)


# 1. Static pages
class StaticViewSitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "books:home",
            "books:services",
            "books:resources",
            "books:projects",
            "books:hire",
            "books:project_faculty",
            "books:project-list",
            "books:payment-checkout",
            "books:login-projects",
            "books:login-project-list",
            "books:login-payment-method",
            "books:verification-error",
            "books:upload-book",
        ]

    def location(self, item):
        return reverse(item)


# 2. Dynamic pages
class BookSitemap(BaseSitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Book.objects.all()

    def location(self, obj):
        return reverse("books:product-details", args=[obj.slug])

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None)


class CategorySitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse("books:category_books", args=[obj.slug])


class FacultySitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return BookType.objects.all()

    def location(self, obj):
        return reverse("books:faculty", args=[obj.slug])


class PaymentOptionSitemap(BaseSitemap):
    changefreq = "yearly"
    priority = 0.3

    def items(self):
        return Payment.objects.all()

    def location(self, obj):
        return reverse("books:payment-method", args=[obj.slug])
