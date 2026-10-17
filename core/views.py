from django.shortcuts import render
from products.models import Product
# Create your views here.

def index(request):
    featured_products = Product.objects.filter(is_featured=True)
    return render(request, 'core/index.html', {'featured_products': featured_products})