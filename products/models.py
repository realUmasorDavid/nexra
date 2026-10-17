from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:category_detail', kwargs={'slug': self.slug})

class Collection(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)

    image = models.ImageField(upload_to='collections/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='collections/banners/', blank=True, null=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-start_date', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:collection_detail', kwargs={'slug': self.slug})

    @property
    def is_live(self):
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_active

class Product(models.Model):
    GENDER_CHOICES = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('unisex', 'Unisex'),
        ('kids', 'Kids'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    collections = models.ManyToManyField(
        Collection,
        related_name='products',
        blank=True
    )
    size_guide = models.ForeignKey(
        'SizeGuide',
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True
    )

    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unisex')

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    material = models.CharField(max_length=200, blank=True)
    care_instructions = models.TextField(blank=True)

    total_sold = models.PositiveIntegerField(default=0, editable=False)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'slug': self.slug})

    @property
    def is_on_sale(self):
        return self.compare_at_price and self.compare_at_price > self.price

    @property
    def discount_percentage(self):
        if self.is_on_sale:
            return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)
        return 0

    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()

    @property
    def is_sold_out(self):
        return not self.variants.filter(is_active=True, stock__gt=0).exists()

    @property
    def primary_image_url(self):
        img = self.main_image
        if img and img.image:
            return img.image.url
        return None

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(product=self.product, is_main=True).update(is_main=False)
        super().save(*args, **kwargs)

class Size(models.Model):
    name = models.CharField(max_length=20)
    code = models.CharField(max_length=10, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class SizeGuide(models.Model):
    name = models.CharField(max_length=50)
    image_guide = models.ImageField(upload_to='size_guides/')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    hex_code = models.CharField(max_length=7, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name='variants')

    sku = models.CharField(max_length=50, unique=True)

    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    total_sold = models.PositiveIntegerField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('product', 'size', 'color')]
        ordering = ['product', 'size__order', 'color__order']

    def __str__(self):
        return f"{self.product.name} - {self.size.name} / {self.color.name}"

    @property
    def price(self):
        return self.price_override if self.price_override is not None else self.product.price

    @property
    def in_stock(self):
        return self.stock > 0