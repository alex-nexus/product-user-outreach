# Reddit User Outreach Tool

A Django application that automates finding real Reddit users who use specific products by:
1. Using AI with web search to discover Reddit pages mentioning products
2. Scraping discovered Reddit pages
3. Using AI to extract real users with evidence of product usage

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers (required for web scraping):
```bash
playwright install chromium
```

3. Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here (optional, for Google search)
GOOGLE_CSE_ID=your_google_cse_id_here (optional, for Google search)
BING_API_KEY=your_bing_api_key_here (optional, for Bing search)
```

Note: The search client defaults to Google Custom Search. You can use DuckDuckGo without API keys, or configure Bing/Google with API keys.

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser to access Django admin:
```bash
python manage.py createsuperuser
```

## Usage

1. Start the Django development server:
```bash
python manage.py runserver
```

2. Access Django admin at `http://localhost:8000/admin/` and create a Product.

3. Run the workflow command to find users:
```bash
python manage.py find_product_users --product "Product Name"
```

You can also specify a search provider (default is 'google'):
```bash
python manage.py find_product_users --product "Product Name" --search-provider duckduckgo
```

Available search providers: `google`, `duckduckgo`, `bing`

The command will:
- Search for Reddit pages mentioning the product using AI
- Scrape each discovered Reddit page
- Extract users who actually use the product with evidence
- Store all data in the database

4. View results in Django admin:
- Products: List of all products
- Product Pages: Reddit pages that were scraped
- Product Users: Extracted users with evidence of product usage

## Architecture

- **workflows/**: Main workflow orchestrator that ties everything together
- **agents/**: LLM-related code for AI interactions
- **services/**: CRUD managers for database operations
- **clients/**: Web scraper for Reddit pages
- **management/commands/**: Django management command that calls the workflow

## Models

- **Product**: Stores product names
- **ProductPage**: Stores scraped Reddit pages with HTML/text content
- **ProductUser**: Stores extracted users with evidence of product usage

## Configuration

Settings can be configured in `outreach/settings.py`:
- `OPENAI_API_KEY`: Your OpenAI API key (from .env)
- `SCRAPER_USER_AGENT`: User agent for web scraping
- `SCRAPER_REQUEST_TIMEOUT`: Timeout for HTTP requests
- `SCRAPER_MAX_RETRIES`: Maximum retry attempts
- `AI_MAX_TOKENS`: Maximum tokens for AI responses
- `AI_TEMPERATURE`: Temperature for AI responses

