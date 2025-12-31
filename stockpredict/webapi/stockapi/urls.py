"""
URL configuration for Stock Helper API project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/

All APIs are prefixed with 'stock_helper' to support multi-project deployment.
Example: http://localhost:8000/stock_helper/api/v1/{endpoint}
"""
from django.contrib import admin
from django.urls import path, include

# API URL prefix for multi-project deployment
API_PREFIX = 'stock_helper'

urlpatterns = [
    # Admin panel: /stock_helper/admin/
    path(f'{API_PREFIX}/admin/', admin.site.urls),

    # API v1: /stock_helper/api/v1/{endpoint}
    path(f'{API_PREFIX}/api/v1/', include('stock.urls')),

    # Legacy support (optional - remove after migration)
    # path('stock/api/', include('stock.urls')),
]
