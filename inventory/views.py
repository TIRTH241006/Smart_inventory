from rest_framework import viewsets
from .models import Product, Supplier, Transaction
from .serializers import ProductSerializer, SupplierSerializer, TransactionSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import models
from django.shortcuts import render
from django.shortcuts import render, redirect

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def perform_create(self, serializer):
        transaction = serializer.save()
        product = transaction.product

        if transaction.transaction_type == 'IN':
            product.quantity += transaction.quantity
        else:
            product.quantity -= transaction.quantity

        product.save()

@api_view(['GET'])
def low_stock(request):
    low_products = Product.objects.filter(quantity__lte=models.F('reorder_level'))
    serializer = ProductSerializer(low_products, many=True)
    return Response(serializer.data)

def dashboard(request):
    return render(request, 'dashboard.html')

def home(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return render(request, 'home.html')
