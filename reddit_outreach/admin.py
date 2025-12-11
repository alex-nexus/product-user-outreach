from django.contrib import admin
from reddit_outreach.models import Product, ProductPage, ProductUser


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']
    list_filter = ['created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProductPage)
class ProductPageAdmin(admin.ModelAdmin):
    list_display = ['product', 'subreddit', 'status', 'scraped_at', 'url']
    list_filter = ['status', 'scraped_at', 'product']
    search_fields = ['url', 'subreddit', 'product__name']
    readonly_fields = ['scraped_at']
    raw_id_fields = ['product']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


@admin.register(ProductUser)
class ProductUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'product_page', 'extracted_at']
    list_filter = ['extracted_at', 'product_page__product']
    search_fields = ['username', 'reason_text', 'product_page__product__name']
    readonly_fields = ['extracted_at']
    raw_id_fields = ['product_page']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product_page', 'product_page__product')

