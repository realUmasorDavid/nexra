from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product_name",
        "size",
        "color",
        "sku",
        "quantity",
        "price",
        "line_total_display",
    )
    fields = (
        "product_name",
        "size",
        "color",
        "sku",
        "quantity",
        "price",
        "line_total_display",
    )
    can_delete = False

    @admin.display(description="Line Total")
    def line_total_display(self, obj):
        total = obj.line_total or 0
        return f"₦{total:,.2f}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "name",
        "email",
        "phone",
        "status_badge",
        "payment_status_badge",
        "total_price_display",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "created_at",
        "state",
    )
    search_fields = (
        "order_id",
        "reference",
        "name",
        "email",
        "phone",
    )
    readonly_fields = (
        "order_id",
        "reference",
        "created_at",
        "updated_at",
        "paid_at",
        "shipping_type",
        "subtotal",
        "shipping_fee",
        "total_price",
        "service_fee",
    )
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25

    fieldsets = (
        ("Order Info", {
            "fields": (
                "order_id",
                "reference",
                "status",
                "payment_status",
                "paid_at",
            )
        }),
        ("Customer", {
            "fields": (
                "name",
                "email",
                "phone",
            )
        }),
        ("Shipping", {
            "fields": (
                "address",
                "city",
                "state",
                "postal_code",
                "additional_notes",
                "shipping_type",
            )
        }),
        ("Totals", {
            "fields": (
                "subtotal",
                "shipping_fee",
                "service_fee",
                "total_price",
            )
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    actions = ["mark_as_processing", "mark_as_shipped", "mark_as_delivered"]

    @admin.display(description="Total")
    def total_price_display(self, obj):
        return f"₦{obj.total_price:,.2f}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "processing": "#3b82f6",
            "shipped": "#8b5cf6",
            "delivered": "#22c55e",
            "cancelled": "#6b7280",
            "failed": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; '
            'border-radius:4px; font-size:11px; font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Payment")
    def payment_status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "paid": "#22c55e",
            "failed": "#ef4444",
            "refunded": "#6b7280",
        }
        color = colors.get(obj.payment_status, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; '
            'border-radius:4px; font-size:11px; font-weight:600;">{}</span>',
            color,
            obj.get_payment_status_display(),
        )

    @admin.action(description="Mark selected orders as Processing")
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status="processing")
        self.message_user(request, f"{updated} order(s) marked as Processing.")

    @admin.action(description="Mark selected orders as Shipped")
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status="shipped")
        self.message_user(request, f"{updated} order(s) marked as Shipped.")

    @admin.action(description="Mark selected orders as Delivered")
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status="delivered")
        self.message_user(request, f"{updated} order(s) marked as Delivered.")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order_link",
        "product_name",
        "size",
        "color",
        "quantity",
        "price",
        "line_total_display",
    )
    list_filter = ("size", "color")
    search_fields = (
        "product_name",
        "sku",
        "order__order_id",
        "order__email",
    )
    readonly_fields = (
        "order",
        "product_id",
        "variant_id",
        "product_name",
        "size",
        "color",
        "sku",
        "quantity",
        "price",
        "line_total_display",
    )

    def has_add_permission(self, request):
        return False  # items should only be created through the order flow

    @admin.display(description="Order")
    def order_link(self, obj):
        url = reverse("admin:orders_order_change", args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_id)

    @admin.display(description="Line Total")
    def line_total_display(self, obj):
        total = obj.line_total or 0
        return f"₦{total:,.2f}"