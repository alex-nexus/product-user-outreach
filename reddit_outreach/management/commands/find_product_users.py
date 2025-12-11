from django.core.management.base import BaseCommand, CommandError
from reddit_outreach.workflows.find_product_users import FindProductUsersWorkflow
from reddit_outreach.services.product_service import ProductService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Find Reddit users who use a specific product'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            required=True,
            help='Product name to search for',
        )
        parser.add_argument(
            '--search-provider',
            type=str,
            default='google',
            choices=['google', 'duckduckgo', 'bing'],
            help='Search provider to use (default: google)',
        )
        parser.add_argument(
            '--max-urls',
            type=int,
            default=20,
            help='Maximum number of Reddit URLs to search for (default: 20)',
        )

    def handle(self, *args, **options):
        product_name = options['product']
        search_provider = options.get('search_provider', 'google')
        max_urls = options.get('max_urls', 20)
        
        if not product_name:
            raise CommandError('Product name is required')
        
        self.stdout.write(self.style.SUCCESS(f'Starting workflow for product: {product_name}'))
        self.stdout.write(f'Using search provider: {search_provider}')
        self.stdout.write(f'Max URLs to search: {max_urls}')
        
        try:
            # Initialize workflow
            workflow = FindProductUsersWorkflow(search_provider=search_provider)
            
            # Execute workflow
            result = workflow.execute(product_name, max_urls=max_urls)
            
            # Display results
            self.stdout.write(self.style.SUCCESS('\n=== Workflow Results ==='))
            self.stdout.write(f"Product: {result['product'].name}")
            self.stdout.write(f"URLs Found: {result['urls_found']}")
            self.stdout.write(f"Pages Scraped: {result['pages_scraped']}")
            self.stdout.write(f"Users Extracted: {result['users_extracted']}")
            self.stdout.write(f"Status: {'Success' if result['success'] else 'Failed'}")
            self.stdout.write(f"Message: {result['message']}")
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('\n✓ Workflow completed successfully!'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠ Workflow completed with warnings'))
                
        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            raise CommandError(f'Workflow failed: {str(e)}')

