import hashlib
import hmac
import json
import logging
import uuid
from collections import defaultdict
from decimal import Decimal

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from products.models import Product, ProductVariant

from .models import Order, OrderItem

logger = logging.getLogger(__name__)

SERVICE_FEE = Decimal("2000.00")
LOCAL_SHIPPING_FEES = {
    "lagos": Decimal("2000.00"),
    "oyo": Decimal("4000.00"),
}
INTERNATIONAL_SHIPPING_FEE = Decimal("20000.00")


class InsufficientStockError(Exception):
    pass


def get_shipping_fee(shipping_type, state):
    if shipping_type == "international":
        return INTERNATIONAL_SHIPPING_FEE
    if shipping_type != "local":
        raise ValueError("Select a valid shipping type.")

    normalized_state = " ".join(state.casefold().split())
    if normalized_state.endswith(" state"):
        normalized_state = normalized_state[:-6].strip()
    return LOCAL_SHIPPING_FEES.get(normalized_state, Decimal("10000.00"))


def check_stock(variant, quantity):
    if variant.stock < quantity:
        raise InsufficientStockError(
            f"Only {variant.stock} left of {variant.product.name} "
            f"({variant.size.name}/{variant.color.name})"
        )


def _send_order_confirmation(order):
    try:
        subject = f"Order Confirmed – #{order.order_id}"
        context = {"order": order}
        text_content = render_to_string("orders/email/order_confirmation.txt", context)
        html_content = render_to_string("orders/email/order_confirmation.html", context)

        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info("Order confirmation email sent for %s", order.order_id)
    except Exception:
        logger.exception("Failed to send order confirmation for %s", order.order_id)


def _complete_paid_order(order, transaction_data):
    if (
        not isinstance(transaction_data, dict)
        or transaction_data.get("status") != "success"
        or transaction_data.get("reference") != order.reference
        or transaction_data.get("currency") != "NGN"
    ):
        return False, False

    try:
        paid_amount = int(transaction_data.get("amount"))
    except (TypeError, ValueError):
        return False, False
    if paid_amount != int(order.total_price * 100):
        return False, False

    inventory_issue = False
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.payment_status == "paid":
            return False, False

        items = list(order.items.all())
        quantities = defaultdict(int)
        product_sales = defaultdict(lambda: [0, Decimal("0.00")])
        for item in items:
            if item.variant_id:
                quantities[item.variant_id] += item.quantity
            if item.product_id:
                product_sales[item.product_id][0] += item.quantity
                product_sales[item.product_id][1] += item.price * item.quantity

        variants = {
            variant.pk: variant
            for variant in ProductVariant.objects.select_for_update().filter(
                pk__in=quantities
            )
        }
        inventory_issue = any(
            variant_id not in variants
            or variants[variant_id].stock < quantity
            for variant_id, quantity in quantities.items()
        )

        if not inventory_issue:
            try:
                with transaction.atomic():
                    for variant_id, quantity in quantities.items():
                        updated = ProductVariant.objects.filter(
                            pk=variant_id,
                            stock__gte=quantity,
                        ).update(
                            stock=F("stock") - quantity,
                            total_sold=F("total_sold") + quantity,
                        )
                        if updated != 1:
                            raise InsufficientStockError
            except InsufficientStockError:
                inventory_issue = True

        for product_id, (quantity, revenue) in product_sales.items():
            Product.objects.filter(pk=product_id).update(
                total_sold=F("total_sold") + quantity,
                total_revenue=F("total_revenue") + revenue,
            )

        order.payment_status = "paid"
        order.paid_at = timezone.now()
        update_fields = ["payment_status", "paid_at", "updated_at"]
        if not inventory_issue:
            order.status = "processing"
            update_fields.append("status")
        order.save(update_fields=update_fields)

    if inventory_issue:
        logger.error(
            "Payment %s succeeded but inventory could not be deducted; "
            "order %s requires manual review",
            order.reference,
            order.order_id,
        )
    return True, inventory_issue


@require_POST
@csrf_exempt
def process_checkout(request):
    order = None
    try:
        data = json.loads(request.body)
        cart_items = data.get("cart_items", [])

        if not cart_items:
            return JsonResponse({"error": "Cart is empty"}, status=400)

        required = ["full_name", "email", "phone", "address", "city", "state"]
        for field in required:
            if not data.get(field, "").strip():
                return JsonResponse(
                    {"error": f"{field.replace('_', ' ').title()} is required"},
                    status=400,
                )

        quantities = defaultdict(int)
        for item in cart_items:
            try:
                variant_id = int(item.get("variant_id"))
                quantity = int(item.get("quantity", 1))
            except (TypeError, ValueError):
                return JsonResponse({"error": "Invalid cart item"}, status=400)
            if variant_id < 1 or quantity < 1:
                return JsonResponse({"error": "Invalid cart item"}, status=400)
            item["variant_id"] = variant_id
            quantities[variant_id] += quantity

        shipping_type = data.get("shipping_type", "local")
        try:
            shipping_fee = get_shipping_fee(shipping_type, data["state"])
        except ValueError as error:
            return JsonResponse({"error": str(error)}, status=400)

        variants = {
            variant.pk: variant
            for variant in ProductVariant.objects.filter(
                pk__in=quantities,
                is_active=True,
            ).select_related("product", "size", "color")
        }
        if len(variants) != len(quantities):
            return JsonResponse(
                {"error": "One or more items are no longer available."},
                status=400,
            )

        for variant_id, quantity in quantities.items():
            try:
                check_stock(variants[variant_id], quantity)
            except InsufficientStockError as error:
                return JsonResponse({"error": str(error)}, status=400)

        subtotal = sum(
            variants[item["variant_id"]].price * int(item["quantity"])
            for item in cart_items
        )
        total = subtotal + shipping_fee + SERVICE_FEE

        order = Order.objects.create(
            name=data.get("full_name").strip(),
            email=data.get("email").strip().lower(),
            phone=data.get("phone").strip(),
            address=data.get("address").strip(),
            city=data.get("city").strip(),
            state=data.get("state").strip(),
            postal_code=data.get("postal_code", "").strip(),
            additional_notes=data.get("additional_notes", "").strip(),
            shipping_type=shipping_type,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total_price=total,
            service_fee=SERVICE_FEE,
            payment_status="pending",
            status="pending",
            reference=f"NR-{uuid.uuid4().hex[:12].upper()}",
        )

        for item in cart_items:
            variant = variants[item["variant_id"]]
            OrderItem.objects.create(
                order=order,
                product_id=variant.product_id,
                variant_id=variant.pk,
                quantity=int(item["quantity"]),
                price=variant.price,
                product_name=variant.product.name,
                size=variant.size.name,
                color=variant.color.name,
                sku=variant.sku,
                image=variant.product.primary_image_url or "",
            )

        secret_key = settings.PAYSTACK_SECRET_KEY
        if not secret_key:
            raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")

        payload = {
            "email": order.email,
            "amount": int(total * 100),
            "currency": "NGN",
            "reference": order.reference,
            "callback_url": request.build_absolute_uri("/orders/payment/success/"),
            "metadata": {
                "order_id": str(order.order_id),
                "custom_fields": [
                    {"display_name": "Name", "variable_name": "name", "value": order.name},
                    {"display_name": "Phone", "variable_name": "phone", "value": order.phone},
                ],
            },
        }

        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("status"):
            return JsonResponse(
                {
                    "success": True,
                    "authorization_url": response_data["data"]["authorization_url"],
                }
            )

        order.payment_status = "failed"
        order.status = "failed"
        order.save(update_fields=["payment_status", "status"])
        return JsonResponse(
            {
                "error": response_data.get(
                    "message", "Payment initialization failed"
                )
            },
            status=400,
        )

    except Exception as error:
        logger.exception("Checkout process failed")
        if order:
            order.payment_status = "failed"
            order.status = "failed"
            order.save(update_fields=["payment_status", "status"])
        return JsonResponse({"error": str(error)}, status=500)


def payment_success(request):
    reference = request.GET.get("reference") or request.GET.get("trxref")
    if not reference:
        logger.warning("No reference received in Paystack callback")
        return redirect("store:cart")

    order = get_object_or_404(Order, reference=reference)
    if order.payment_status == "paid":
        return redirect("orders:order_success", order_id=order.order_id)

    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        logger.error("PAYSTACK_SECRET_KEY is not configured")
        return redirect("orders:order_failed")

    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=12,
        )
        response.raise_for_status()
        verification = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("Paystack verification failed for %s", reference)
        return redirect("orders:order_failed")

    if not isinstance(verification, dict):
        logger.error("Paystack verification returned invalid data for %s", reference)
        return redirect("orders:order_failed")

    transaction_data = verification.get("data", {}) if verification.get("status") else {}
    if not isinstance(transaction_data, dict):
        logger.error("Paystack verification returned invalid transaction for %s", reference)
        return redirect("orders:order_failed")

    if transaction_data.get("status") == "success":
        newly_paid, _inventory_issue = _complete_paid_order(
            order,
            transaction_data,
        )
        order.refresh_from_db()
        if not newly_paid and order.payment_status != "paid":
            logger.error("Paystack verification did not match order %s", order.order_id)
            return redirect("orders:order_failed")
        if newly_paid:
            _send_order_confirmation(order)
        request.session["clear_cart_after_success"] = True
        return redirect("orders:order_success", order_id=order.order_id)

    if transaction_data.get("status") in {"failed", "abandoned"}:
        Order.objects.filter(pk=order.pk, payment_status="pending").update(
            payment_status="failed",
            status="failed",
            updated_at=timezone.now(),
        )
    return redirect("orders:order_failed")


@require_POST
@csrf_exempt
def paystack_webhook(request):
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        logger.error("PAYSTACK_SECRET_KEY is not configured")
        return JsonResponse({"error": "Webhook is not configured"}, status=503)

    signature = request.headers.get("x-paystack-signature", "")
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        request.body,
        hashlib.sha512,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning("Rejected Paystack webhook with invalid signature")
        return JsonResponse({"error": "Invalid signature"}, status=401)

    try:
        event = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not isinstance(event, dict) or event.get("event") != "charge.success":
        return JsonResponse({"status": "ignored"})

    transaction_data = event.get("data")
    if not isinstance(transaction_data, dict):
        logger.error("Paystack charge.success webhook has no transaction data")
        return JsonResponse({"status": "accepted"})

    reference = transaction_data.get("reference")
    if not reference:
        logger.error("Paystack charge.success webhook has no reference")
        return JsonResponse({"status": "accepted"})

    order = Order.objects.filter(reference=reference).first()
    if not order:
        logger.error("Paystack webhook references unknown order %s", reference)
        return JsonResponse({"status": "accepted"})

    newly_paid, inventory_issue = _complete_paid_order(order, transaction_data)
    order.refresh_from_db()
    if not newly_paid and order.payment_status != "paid":
        logger.error("Paystack payment data did not match order %s", order.order_id)
        return JsonResponse({"status": "accepted"})
    if newly_paid:
        _send_order_confirmation(order)
    if inventory_issue:
        return JsonResponse({"status": "accepted", "inventory_issue": True})
    return JsonResponse({"status": "ok"})


def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    should_clear = request.session.pop("clear_cart_after_success", False)

    return render(
        request,
        "orders/order_success.html",
        {"order": order, "should_clear_cart": should_clear},
    )


def order_failed(request):
    return render(request, "orders/order_failed.html")


ORDER_STATUS_STEPS = [
    ("pending", "Order Placed"),
    ("processing", "Processing"),
    ("shipped", "Shipped"),
    ("delivered", "Delivered"),
]

_STATUS_KEYS = [step[0] for step in ORDER_STATUS_STEPS]


def track_order(request):
    order = None
    error = None
    submitted_order_id = request.GET.get("order_id", "").strip()
    submitted_email = request.GET.get("email", "").strip()

    if submitted_order_id and submitted_email:
        try:
            order = Order.objects.get(
                order_id__iexact=submitted_order_id,
                email__iexact=submitted_email,
            )
        except Order.DoesNotExist:
            error = (
                "We couldn’t find an order matching that ID and email. "
                "Please double-check both."
            )

    context = {
        "order": order,
        "error": error,
        "submitted_order_id": submitted_order_id,
        "submitted_email": submitted_email,
    }

    if order:
        try:
            status_index = _STATUS_KEYS.index(order.status)
        except ValueError:
            status_index = -1
        context["order_status_steps"] = ORDER_STATUS_STEPS
        context["order_status_index"] = status_index

    return render(request, "orders/track_order.html", context)
