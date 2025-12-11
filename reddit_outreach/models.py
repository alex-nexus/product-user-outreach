from django.db import models
from django.utils import timezone


class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ProductPage(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scraped', 'Scraped'),
        ('failed', 'Failed'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pages')
    url = models.URLField(max_length=500)
    subreddit = models.CharField(max_length=200)
    scraped_html = models.TextField(blank=True)
    scraped_text = models.TextField(blank=True)
    scraped_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ['-scraped_at']
        unique_together = ['product', 'url']

    def __str__(self):
        return f"{self.product.name} - {self.subreddit}"


class ProductUser(models.Model):
    product_page = models.ForeignKey(ProductPage, on_delete=models.CASCADE, related_name='users')
    username = models.CharField(max_length=200)
    profile_url = models.URLField(max_length=500)
    reason_text = models.TextField(help_text="Substring of text that demonstrates the user actually uses the product")
    extracted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-extracted_at']
        unique_together = ['product_page', 'username']

    def __str__(self):
        return f"{self.username} - {self.product_page.product.name}"

