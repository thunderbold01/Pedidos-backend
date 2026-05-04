# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def home(request):
    return JsonResponse({
        "status": "ok",
        "message": "API do Sistema de Pedidos",
        "versao": "1.0",
        "endpoints": {
            "admin": "/admin/",
            "api": "/api/",
            "login": "/api/auth/login/",
            "registro": "/api/auth/register/",
        }
    })

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('pedidos.urls')),
]
