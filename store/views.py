from django.shortcuts import render
from products.models import Product, Collection

def store(request):
    products = (
        Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants', 'collections').order_by('-created_at')
    )

    collections = Collection.objects.filter(is_active=True).order_by('order', 'name')

    context = {
        'products': products,
        'collections': collections,
    }
    return render(request, 'store/store.html', context)


def cart(request):
    return render(request, 'store/cart.html')

def checkout(request):
    return render(request, 'store/checkout.html')