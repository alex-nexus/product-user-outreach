from django.core.management.base import BaseCommand, CommandError
from reddit_outreach.workflows.find_reddit_pages import FindRedditPagesWorkflow
from reddit_outreach.agents.product_user_extractor import ProductUserExtractor
from reddit_outreach.services.product_user_service import ProductUserService
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
            '--max-urls',
            type=int,
            default=20,
            help='Maximum number of Reddit URLs per LLM provider to search for (default: 20)',
        )

    def handle(self, *args, **options):
        product_name = options['product']
        max_urls = options.get('max_urls', 20)
        
        if not product_name:
            raise CommandError('Product name is required')
        
        self.stdout.write(self.style.SUCCESS(f'Starting workflow for product: {product_name}'))
        self.stdout.write('Using LLM providers: OpenAI, Gemini, Grok')
        self.stdout.write(f'Max URLs per LLM provider: {max_urls}')
        
        try:
            # Step 1: Find and scrape Reddit pages
            self.stdout.write(self.style.SUCCESS('\n=== Step 1: Finding Reddit Pages ==='))
            find_pages_workflow = FindRedditPagesWorkflow()
            pages_result = find_pages_workflow.execute(product_name, max_urls=max_urls)
            
            self.stdout.write(f"URLs Found: {pages_result['urls_found']}")
            self.stdout.write(f"Pages Scraped: {pages_result['pages_scraped']}")
            
            if not pages_result['success'] or not pages_result.get('pages'):
                self.stdout.write(self.style.WARNING(f'\n⚠ {pages_result["message"]}'))
                return
            
            # Step 2: Extract users from each page
            self.stdout.write(self.style.SUCCESS('\n=== Step 2: Extracting Users ==='))
            user_extractor = ProductUserExtractor()
            product_user_service = ProductUserService()
            total_users = 0
            
            for page in pages_result['pages']:
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
                        self.stdout.write(f'  Extracted {created_count} users from: {page.url}')
                    else:
                        self.stdout.write(f'  No users found in: {page.url}')
                        
                except Exception as e:
                    logger.error(f"Error extracting users from {page.url}: {e}")
                    self.stdout.write(self.style.ERROR(f'  Error extracting from {page.url}: {str(e)}'))
            
            # Display final results
            self.stdout.write(self.style.SUCCESS('\n=== Final Results ==='))
            self.stdout.write(f"Product: {pages_result['product'].name}")
            self.stdout.write(f"URLs Found: {pages_result['urls_found']}")
            self.stdout.write(f"Pages Scraped: {pages_result['pages_scraped']}")
            self.stdout.write(f"Users Extracted: {total_users}")
            
            if total_users > 0:
                self.stdout.write(self.style.SUCCESS('\n✓ Workflow completed successfully!'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠ No users extracted from pages'))
                
        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            raise CommandError(f'Workflow failed: {str(e)}')

