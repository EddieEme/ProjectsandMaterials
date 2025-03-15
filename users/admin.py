from django.contrib import admin
from django.contrib.auth.admin import UserAdmin 
from django.contrib.admin import ModelAdmin
from django.contrib.auth.models import Group
from .models import CustomUser, Profile

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):  # ✅ Now ModelAdmin is defined
    model = CustomUser
    ordering = ["email"]
    list_display = ("email", "first_name", "last_name", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    # Use Django-provided forms
    from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AdminPasswordChangeForm

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")





@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "can_publish", "created_at")
    search_fields = ("user__email",)
