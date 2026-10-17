from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    Collection,
    Product,
    ProductImage,
    Size,
    SizeGuide,
    Color,
    ProductVariant,
)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_main', 'order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 60px; max-width: 60px;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Preview"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        'size',
        'color',
        'sku',
        'price_override',
        'stock',
        'total_sold',
        'is_active',
    )
    readonly_fields = ('total_sold',)
    show_change_link = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active',)
    ordering = ('name',)

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'is_featured',
        'is_active',
        'is_live_display',
        'start_date',
        'end_date',
        'order',
    )
    list_filter = ('is_featured', 'is_active')
    search_fields = ('name', 'description', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_featured', 'is_active', 'order')
    ordering = ('order', '-start_date')

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'short_description', 'description')
        }),
        ('Media', {
            'fields': ('image', 'banner_image')
        }),
        ('Scheduling & Status', {
            'fields': ('start_date', 'end_date', 'is_featured', 'is_active', 'order')
        }),
    )

    def is_live_display(self, obj):
        return obj.is_live
    is_live_display.boolean = True
    is_live_display.short_description = "Live"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'compare_at_price',
        'gender',
        'is_featured',
        'is_active',
        'total_sold',
        'created_at',
    )
    list_filter = (
        'is_active',
        'is_featured',
        'gender',
        'category',
        'collections',
    )
    search_fields = ('name', 'description', 'short_description', 'material')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_featured', 'is_active')
    filter_horizontal = ('collections',)
    readonly_fields = ('total_sold', 'total_revenue', 'created_at', 'updated_at')
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'collections')
        }),
        ('Content', {
            'fields': (
                'short_description',
                'description',
                'material',
                'care_instructions',
                'size_guide',
            )
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Status & Visibility', {
            'fields': ('gender', 'is_featured', 'is_active')
        }),
        ('Analytics', {
            'classes': ('collapse',),
            'fields': ('total_sold', 'total_revenue')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview', 'is_main', 'order')
    list_filter = ('is_main',)
    search_fields = ('product__name', 'alt_text')
    list_editable = ('is_main', 'order')

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Preview"

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order')
    list_editable = ('order',)
    search_fields = ('name', 'code')
    ordering = ('order', 'name')

@admin.register(SizeGuide)
class SizeGuideAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_guide')
    search_fields = ('name',)

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'hex_preview', 'order')
    list_editable = ('order',)
    search_fields = ('name', 'code')
    ordering = ('order', 'name')

    def hex_preview(self, obj):
        if obj.hex_code:
            return format_html(
                '<div style="width: 24px; height: 24px; background-color: {}; '
                'border: 1px solid #ccc; border-radius: 4px;"></div>',
                obj.hex_code
            )
        return "—"
    hex_preview.short_description = "Color"

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'size',
        'color',
        'sku',
        'price_display',
        'stock',
        'total_sold',
        'is_active',
    )
    list_filter = ('is_active', 'size', 'color', 'product__category')
    search_fields = ('sku', 'product__name')
    list_editable = ('stock', 'is_active')
    readonly_fields = ('total_sold',)
    autocomplete_fields = ('product', 'size', 'color')

    def price_display(self, obj):
        return obj.price
    price_display.short_description = "Price"