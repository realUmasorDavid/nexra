import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from products.models import Category, Color, Product, ProductVariant, Size

from .models import Order, OrderItem
from .views import get_shipping_fee


@override_settings(PAYSTACK_SECRET_KEY="test-paystack-secret")
class PaystackWebhookTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Apparel")
        size = Size.objects.create(name="Medium", code="M")
        color = Color.objects.create(name="Black", code="black")
        product = Product.objects.create(
            name="Test Tee",
            category=category,
            price=Decimal("25.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            size=size,
            color=color,
            sku="TEST-TEE-M-BLACK",
            stock=5,
        )
        self.order = Order.objects.create(
            name="Test Customer",
            email="customer@example.com",
            phone="08000000000",
            address="1 Test Street",
            city="Lagos",
            state="Lagos",
            total_price=Decimal("50.00"),
            service_fee=Decimal("0.00"),
            reference="TEST-PAYSTACK-REFERENCE",
        )
        OrderItem.objects.create(
            order=self.order,
            product_id=product.pk,
            variant_id=self.variant.pk,
            product_name=product.name,
            quantity=2,
            price=Decimal("25.00"),
        )

    def post_webhook(self, payload, signature=None):
        body = json.dumps(payload).encode()
        if signature is None:
            signature = hmac.new(
                b"test-paystack-secret",
                body,
                hashlib.sha512,
            ).hexdigest()
        return self.client.post(
            reverse("orders:paystack_webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

    def payment_payload(self, **overrides):
        data = {
            "status": "success",
            "reference": self.order.reference,
            "amount": 5000,
            "currency": "NGN",
        }
        data.update(overrides)
        return {"event": "charge.success", "data": data}

    @patch("orders.views._send_order_confirmation")
    def test_valid_webhook_marks_paid_and_decrements_stock_once(self, send_email):
        response = self.post_webhook(self.payment_payload())

        self.assertEqual(response.status_code, 200)
        self.variant.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)
        self.assertEqual(self.variant.total_sold, 2)
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(self.order.status, "processing")
        send_email.assert_called_once()

        duplicate = self.post_webhook(self.payment_payload())
        self.variant.refresh_from_db()
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(self.variant.stock, 3)
        self.assertEqual(self.variant.total_sold, 2)
        send_email.assert_called_once()

    def test_invalid_signature_does_not_change_order_or_stock(self):
        response = self.post_webhook(
            self.payment_payload(),
            signature="not-a-valid-signature",
        )

        self.variant.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.variant.stock, 5)
        self.assertEqual(self.order.payment_status, "pending")

    @patch("orders.views._send_order_confirmation")
    def test_successful_payment_with_insufficient_stock_is_flagged(self, _send_email):
        self.variant.stock = 1
        self.variant.save(update_fields=["stock"])

        response = self.post_webhook(self.payment_payload())

        self.variant.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["inventory_issue"])
        self.assertEqual(self.variant.stock, 1)
        self.assertEqual(self.variant.total_sold, 0)
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(self.order.status, "pending")

    def test_mismatched_amount_is_not_accepted_as_payment(self):
        response = self.post_webhook(self.payment_payload(amount=4999))

        self.variant.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.variant.stock, 5)
        self.assertEqual(self.order.payment_status, "pending")

    def test_shipping_fees_are_calculated_by_shipping_type_and_state(self):
        self.assertEqual(get_shipping_fee("local", "Lagos"), Decimal("2000.00"))
        self.assertEqual(get_shipping_fee("local", "LAGOS STATE"), Decimal("2000.00"))
        self.assertEqual(get_shipping_fee("local", "Oyo"), Decimal("4000.00"))
        self.assertEqual(get_shipping_fee("local", "Kano"), Decimal("10000.00"))
        self.assertEqual(
            get_shipping_fee("international", "California"),
            Decimal("20000.00"),
        )

    def test_order_success_page_renders_subtotal_shipping_and_service_fee(self):
        self.order.subtotal = Decimal("50000.00")
        self.order.shipping_fee = Decimal("2000.00")
        self.order.service_fee = Decimal("2000.00")
        self.order.total_price = Decimal("54000.00")
        self.order.save()

        response = self.client.get(
            reverse("orders:order_success", kwargs={"order_id": self.order.order_id})
        )

        self.assertContains(response, "₦50,000")
        self.assertContains(response, "Shipping (Local)")
        self.assertContains(response, "₦2,000")
        self.assertContains(response, "₦54,000")

    def test_track_order_shows_status_for_matching_order_and_email(self):
        response = self.client.get(
            reverse("orders:track_order"),
            {
                "order_id": self.order.order_id.lower(),
                "email": self.order.email.upper(),
            },
        )

        self.assertContains(response, self.order.order_id)
        self.assertContains(response, "Order received — awaiting payment")
        self.assertContains(response, "Test Tee")
        self.assertContains(response, "Order Total")

    def test_track_order_does_not_reveal_order_for_wrong_email(self):
        response = self.client.get(
            reverse("orders:track_order"),
            {
                "order_id": self.order.order_id,
                "email": "wrong@example.com",
            },
        )

        self.assertContains(response, "We couldn’t find an order")
        self.assertNotContains(response, "Test Tee")

    @patch("orders.views._send_order_confirmation")
    @patch("orders.views.requests.get")
    def test_verified_payment_callback_uses_the_same_stock_completion(
        self,
        paystack_get,
        _send_email,
    ):
        paystack_get.return_value.json.return_value = {
            "status": True,
            "data": self.payment_payload()["data"],
        }

        response = self.client.get(
            reverse("orders:payment_success"),
            {"reference": self.order.reference},
        )

        self.variant.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.variant.stock, 3)
        self.assertEqual(self.order.payment_status, "paid")

    @patch("orders.views.requests.post")
    def test_checkout_uses_server_prices_and_persists_shipping_breakdown(
        self,
        paystack_post,
    ):
        paystack_post.return_value.json.return_value = {
            "status": True,
            "data": {"authorization_url": "https://paystack.test/checkout"},
        }
        response = self.client.post(
            reverse("orders:process_checkout"),
            data=json.dumps(
                {
                    "full_name": "Test Customer",
                    "email": "customer@example.com",
                    "phone": "08000000000",
                    "address": "1 Test Street",
                    "city": "Lagos",
                    "state": "Lagos",
                    "shipping_type": "international",
                    "service_fee": 0,
                    "cart_items": [
                        {
                            "product_id": self.variant.product_id,
                            "variant_id": self.variant.pk,
                            "quantity": 2,
                            "price": "1.00",
                            "name": "Test Tee",
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.variant.refresh_from_db()
        created_order = Order.objects.exclude(pk=self.order.pk).get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.variant.stock, 5)
        self.assertEqual(created_order.subtotal, Decimal("50.00"))
        self.assertEqual(created_order.shipping_type, "international")
        self.assertEqual(created_order.shipping_fee, Decimal("20000.00"))
        self.assertEqual(created_order.service_fee, Decimal("2000.00"))
        self.assertEqual(created_order.total_price, Decimal("22050.00"))
        self.assertEqual(
            paystack_post.call_args.kwargs["json"]["amount"],
            2205000,
        )
