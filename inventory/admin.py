from django.contrib import admin
from .models import Product, Supplier, Transaction

admin.site.register(Product)
admin.site.register(Supplier)
admin.site.register(Transaction)