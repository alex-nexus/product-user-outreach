"""Database models for the Reddit outreach app."""

from django.db import models


class Product(models.Model):
    """A product we want to find users for."""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Model metadata."""

        ordering = ["-created_at"]

    def __str__(self):
        """Return a human-readable name."""
        return self.name


class ProductPage(models.Model):
    """A scraped Reddit page (post/thread) relevant to a product."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("scraped", "Scraped"),
        ("failed", "Failed"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="pages")
    url = models.URLField(max_length=500)
    subreddit = models.CharField(max_length=200)
    scraped_html = models.TextField(blank=True)
    scraped_text = models.TextField(blank=True)
    scraped_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        """Model metadata."""

        ordering = ["-scraped_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "url"],
                name="uniq_productpage_product_url",
            )
        ]

    def __str__(self):
        """Return a human-readable representation."""
        return f"{self.product.name} - {self.subreddit}"


class ProductUser(models.Model):
    """A Reddit user extracted from a ProductPage."""

    product_page = models.ForeignKey(
        ProductPage, on_delete=models.CASCADE, related_name="users"
    )
    username = models.CharField(max_length=200)
    profile_url = models.URLField(max_length=500)
    reason_text = models.TextField(
        help_text=(
            "Substring of text that demonstrates the user actually uses the product"
        )
    )
    extracted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Model metadata."""

        ordering = ["-extracted_at"]
        unique_together = ["product_page", "username"]

    def __str__(self):
        """Return a human-readable representation."""
        return f"{self.username} - {self.product_page.product.name}"
