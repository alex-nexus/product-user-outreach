from reddit_outreach.models import Product


class ProductService:
    @staticmethod
    def get_or_create(name):
        """Get or create a product by name."""
        product, created = Product.objects.get_or_create(name=name)
        return product, created

    @staticmethod
    def get(product_id):
        """Get a product by ID."""
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None

    @staticmethod
    def get_by_name(name):
        """Get a product by name."""
        try:
            return Product.objects.get(name=name)
        except Product.DoesNotExist:
            return None

    @staticmethod
    def list_all():
        """List all products."""
        return Product.objects.all()

