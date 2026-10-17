from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/process/", views.process_checkout, name="process_checkout"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("payment/webhook/", views.paystack_webhook, name="paystack_webhook"),
    path("success/<str:order_id>/", views.order_success, name="order_success"),
    path("failed/", views.order_failed, name="order_failed"),
    path("track/", views.track_order, name="track_order"),
]