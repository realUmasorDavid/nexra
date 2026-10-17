import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Order(models.Model):
    SHIPPING_TYPE_CHOICES = [
        ("local", "Local"),
        ("international", "International"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    # Public-facing ID (shown to customer)
    order_id = models.CharField(max_length=20, unique=True, editable=False)

    # Paystack reference
    reference = models.CharField(max_length=50, unique=True, editable=False)

    # Guest customer info
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Shipping
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    additional_notes = models.TextField(blank=True)
    shipping_type = models.CharField(
        max_length=20,
        choices=SHIPPING_TYPE_CHOICES,
        default="local",
    )

    # Money
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    shipping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_id"]),
            models.Index(fields=["email"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"NR-{uuid.uuid4().hex[:8].upper()}"
        if not self.reference:
            self.reference = f"NR-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_id}"

    @property
    def is_paid(self):
        return self.payment_status == "paid"

    def mark_paid(self):
        """Convenience method when payment is confirmed."""
        self.payment_status = "paid"
        self.status = "processing"
        self.paid_at = timezone.now()
        self.save(update_fields=["payment_status", "status", "paid_at", "updated_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # Links back to catalog (nullable so old orders survive product deletion)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    variant_id = models.PositiveIntegerField(null=True, blank=True)

    # Snapshots – these never change even if the product is edited later
    product_name = models.CharField(max_length=200)
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    sku = models.CharField(max_length=50, blank=True)
    image = models.URLField(blank=True)  # optional: store image url at time of order

    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # unit price at purchase

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        if self.price is None or self.quantity is None:
            return Decimal("0.00")
        return self.price * self.quantity

    