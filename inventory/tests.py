from django.test import TestCase
from django.test import override_settings
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse
from rest_framework.test import APIClient

from .models import OTPCode, Product, Supplier
from .utils import create_owner_company


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class InventoryApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(username="tester", email="tester@example.com", password="StrongPass123")
		self.company = create_owner_company(self.user, "Test Company", full_name="Test Owner")
		self.location = self.company.locations.get(is_default=True)
		self.supplier = Supplier.objects.create(name="Main Supplier", company=self.company)
		self.product = Product.objects.create(
			company=self.company,
			name="Laptop",
			sku="LP-100",
			category="Electronics",
			location=self.location,
			quantity=10,
			price="899.99",
			reorder_level=4,
			supplier=self.supplier,
		)

	def test_auth_required_for_products_api(self):
		response = self.client.get("/api/products/")
		self.assertEqual(response.status_code, 403)

	def test_stock_in_updates_quantity(self):
		self.client.login(username="tester", password="StrongPass123")
		payload = {
			"product": self.product.id,
			"transaction_type": "IN",
			"quantity": 5,
			"note": "restock",
		}
		response = self.client.post("/api/transactions/", payload, format="json")
		self.assertEqual(response.status_code, 201)
		self.product.refresh_from_db()
		self.assertEqual(self.product.quantity, 15)

	def test_stock_out_prevents_negative(self):
		self.client.login(username="tester", password="StrongPass123")
		payload = {
			"product": self.product.id,
			"transaction_type": "OUT",
			"quantity": 999,
			"note": "bad request",
		}
		response = self.client.post("/api/transactions/", payload, format="json")
		self.assertEqual(response.status_code, 400)
		self.product.refresh_from_db()
		self.assertEqual(self.product.quantity, 10)

	def test_low_stock_endpoint_returns_items(self):
		self.client.login(username="tester", password="StrongPass123")
		self.product.quantity = 3
		self.product.save()
		response = self.client.get("/api/low-stock/")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)

	def test_dashboard_summary_returns_inventory_totals(self):
		self.client.login(username="tester", password="StrongPass123")
		self.product.quantity = 3
		self.product.save()
		response = self.client.get("/api/dashboard/summary/")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["total_products"], 1)
		self.assertEqual(response.data["low_stock_items"], 1)
		self.assertEqual(response.data["active_suppliers"], 1)
		self.assertEqual(response.data["total_units"], 3)
		self.assertEqual(float(response.data["inventory_value"]), 2699.97)
		self.assertEqual(len(response.data["low_stock_products"]), 1)

	def test_register_logs_user_in_and_redirects(self):
		response = self.client.post(
			reverse("register"),
			{
				"company_name": "Orbit Supplies",
				"full_name": "New User",
				"email": "new-user@example.com",
				"password1": "NewStrongPass123",
				"password2": "NewStrongPass123",
			},
		)
		self.assertRedirects(response, reverse("verify-otp"))
		new_user = User.objects.get(email="new-user@example.com")
		self.assertFalse(new_user.is_active)
		self.assertEqual(self.client.session.get("pending_signup_email"), "new-user@example.com")
		self.assertTrue(OTPCode.objects.filter(email="new-user@example.com", purpose="signup", is_used=False).exists())

	@override_settings(
		SOCIALACCOUNT_PROVIDERS={
			"google": {
				"SCOPE": ["profile", "email"],
				"AUTH_PARAMS": {"access_type": "online"},
			}
		}
	)
	def test_google_login_redirects_cleanly_when_unconfigured(self):
		response = self.client.get("/accounts/google/login/", follow=True)
		self.assertRedirects(response, "/login/")
		messages = [message.message for message in get_messages(response.wsgi_request)]
		self.assertTrue(any("Google login is not configured yet" in message for message in messages))

