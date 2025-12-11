from reddit_outreach.models import ProductUser, ProductPage


class ProductUserService:
    @staticmethod
    def create(product_page, username, profile_url, reason_text):
        """Create a new ProductUser."""
        user, created = ProductUser.objects.get_or_create(
            product_page=product_page,
            username=username,
            defaults={
                'profile_url': profile_url,
                'reason_text': reason_text,
            }
        )
        
        if not created:
            # Update existing user
            user.profile_url = profile_url
            user.reason_text = reason_text
            user.save()
        
        return user, created

    @staticmethod
    def get_by_product_page(page):
        """Get all users for a product page."""
        return ProductUser.objects.filter(product_page=page)

    @staticmethod
    def get_by_product(product):
        """Get all users for a product across all pages."""
        return ProductUser.objects.filter(product_page__product=product)

    @staticmethod
    def bulk_create_users(product_page, users_data):
        """Bulk create users from a list of user data dicts."""
        created_count = 0
        for user_data in users_data:
            username = user_data.get('username')
            profile_url = user_data.get('profile_url', '')
            reason_text = user_data.get('reason_text', '')
            
            if username:
                _, created = ProductUserService.create(
                    product_page, username, profile_url, reason_text
                )
                if created:
                    created_count += 1
        
        return created_count

