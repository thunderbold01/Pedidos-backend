# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['email']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'phone', 'foto')}),
        ('Curso', {'fields': ('curso', 'classe', 'ano_ingresso')}),
        ('Permissões', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Segurança', {'fields': ('two_factor_enabled', 'login_attempts', 'locked_until')}),
        ('Datas', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role', 'first_name', 'last_name'),
        }),
    )