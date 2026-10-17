from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, SizeGuide


class ProductSizeGuideTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Apparel')
        self.product = Product.objects.create(
            name='Graphic Tee',
            category=self.category,
            price='25.00',
        )

    def test_product_detail_displays_its_assigned_size_guide(self):
        SizeGuide.objects.create(
            name='Tee measurements',
            image_guide='size_guides/tee-chart.png',
        )
        self.product.size_guide = SizeGuide.objects.get()
        self.product.save()

        response = self.client.get(reverse(
            'products:product_detail',
            kwargs={'slug': self.product.slug},
        ))

        self.assertContains(response, 'Tee measurements')
        self.assertContains(response, '/media/size_guides/tee-chart.png')

    def test_product_without_a_size_guide_does_not_show_the_guide_section(self):
        response = self.client.get(reverse(
            'products:product_detail',
            kwargs={'slug': self.product.slug},
        ))

        self.assertNotContains(response, 'id="guide-toggle"')
