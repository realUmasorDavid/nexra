from django.shortcuts import render, get_object_or_404
from .models import Product

def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects
        .select_related('category', 'size_guide')
        .prefetch_related(
            'images',
            'variants__size',
            'variants__color',
            'collections'
        ),
        slug=slug,
        is_active=True
    )

    # Available sizes & colors (only from active variants with stock)
    available_variants = product.variants.filter(is_active=True, stock__gt=0)

    sizes = sorted(
        {v.size for v in available_variants},
        key=lambda s: s.order
    )
    colors = sorted(
        {v.color for v in available_variants},
        key=lambda c: c.order
    )

    # All variants as JSON-friendly data for the frontend (size/color → stock/sku/price)
    variants_data = [
        {
            'id': v.id,
            'size': v.size.code,
            'color': v.color.code,
            'sku': v.sku,
            'price': str(v.price),
            'stock': v.stock,
            'in_stock': v.in_stock,
        }
        for v in product.variants.filter(is_active=True)
    ]

    context = {
        'product': product,
        'sizes': sizes,
        'colors': colors,
        'variants_data': variants_data,
        'is_sold_out': product.is_sold_out,
    }
    return render(request, 'products/detail.html', context)