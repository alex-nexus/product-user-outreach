from django.core.management.base import BaseCommand, CommandError
from reddit_outreach.agents.product_user_extractor import ProductUserExtractor
from reddit_outreach.services.product_user_service import ProductUserService
from reddit_outreach.services.product_service import ProductService
from reddit_outreach.services.product_page_service import ProductPageService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Extract product users from Reddit pages for a specific product'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            required=True,
            help='Product name to extract users for',
        )
        parser.add_argument(
            '--page-url',
            type=str,
            default=None,
            help='Optional: Extract users from a specific page URL (if not provided, extracts from all scraped pages for the product)',
        )

    def handle(self, *args, **options):
        product_name = options['product']
        page_url = options.get('page_url')
        
        if not product_name:
            raise CommandError('Product name is required')
        
        self.stdout.write(self.style.SUCCESS(f'Extracting users for product: {product_name}'))
        
        try:
            # Get product
            product_service = ProductService()
            product = product_service.get_by_name(product_name)
            if not product:
                raise CommandError(f'Product not found: {product_name}. Run "find_product_pages" command first.')
            
            # Get pages to process
            product_page_service = ProductPageService()
            if page_url:
                # Extract from specific page
                pages = product_page_service.get_by_product(product)
                pages = [p for p in pages if p.url == page_url]
                if not pages:
                    raise CommandError(f'Page not found: {page_url}')
            else:
                # Extract from all scraped pages
                pages = product_page_service.get_by_product(product)
                pages = [p for p in pages if p.status == 'scraped']
            
            if not pages:
                self.stdout.write(self.style.WARNING('No scraped pages found for this product'))
                self.stdout.write('Run "find_product_pages" command first to find and scrape pages.')
                return
            
            self.stdout.write(f'Processing {len(pages)} page(s)...')
            
            # Extract users from pages
            user_extractor = ProductUserExtractor()
            product_user_service = ProductUserService()
            total_users = 0
            
            for page in pages:
                try:
                    # Get content from page
                    content = page.scraped_text or page.scraped_html
                    if not content:
                        self.stdout.write(self.style.WARNING(f'  No content for: {page.url}'))
                        continue
                    
                    # Extract users using extractor
                    users = user_extractor.extract_users(product_name, content)
                    
                    if users:
                        # Store users in database
                        created_count = product_user_service.bulk_create_users(page, users)
                        total_users += created_count
                        self.stdout.write(f'  ✓ Extracted {created_count} users from: {page.url}')
                    else:
                        self.stdout.write(f'  - No users found in: {page.url}')
                        
                except Exception as e:
                    logger.error(f"Error extracting users from {page.url}: {e}")
                    self.stdout.write(self.style.ERROR(f'  ✗ Error extracting from {page.url}: {str(e)}'))
            
            # Display final results
            self.stdout.write(self.style.SUCCESS('\n=== Results ==='))
            self.stdout.write(f"Product: {product.name}")
            self.stdout.write(f"Pages Processed: {len(pages)}")
            self.stdout.write(f"Users Extracted: {total_users}")
            
            if total_users > 0:
                self.stdout.write(self.style.SUCCESS('\n✓ Successfully extracted users!'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠ No users extracted from pages'))
                
        except Exception as e:
            logger.error(f"Error extracting product users: {e}", exc_info=True)
            raise CommandError(f'Command failed: {str(e)}')

