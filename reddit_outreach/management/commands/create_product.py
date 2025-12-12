from django.core.management.base import BaseCommand, CommandError
from reddit_outreach.services.product_service import ProductService


class Command(BaseCommand):
    help = 'Create a new product'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Product name to create',
        )

    def handle(self, *args, **options):
        product_name = options['name']
        
        if not product_name:
            raise CommandError('Product name is required')
        
        try:
            product_service = ProductService()
            product, created = product_service.get_or_create(product_name)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Successfully created product: {product.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Product already exists: {product.name}'))
                
        except Exception as e:
            raise CommandError(f'Failed to create product: {str(e)}')

