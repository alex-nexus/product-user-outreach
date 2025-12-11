from openai import OpenAI
import json
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class UserExtractionAgent:
    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in settings")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4"  # Using GPT-4 for better extraction
        self.max_tokens = getattr(settings, 'AI_MAX_TOKENS', 2000)
        self.temperature = getattr(settings, 'AI_TEMPERATURE', 0.7)

    def extract_users(self, product_name, page_content):
        """
        Extract Reddit users who actually use the product from page content.
        
        Args:
            product_name: Name of the product
            page_content: HTML or text content from Reddit page
            
        Returns:
            list of dicts with keys: username, profile_url, reason_text
        """
        try:
            # Truncate content if too long (to avoid token limits)
            max_content_length = 10000
            if len(page_content) > max_content_length:
                page_content = page_content[:max_content_length] + "... [truncated]"
            
            prompt = f"""Analyze the following Reddit page content and extract Reddit usernames of users who actually use or have used the product "{product_name}".

For each user, provide:
1. Their Reddit username
2. Their profile URL (format: https://reddit.com/user/username)
3. The specific text/substring from the page that demonstrates they actually use the product

Only include users who clearly demonstrate actual usage of the product (not just mentioning it).

Format your response as JSON array with this structure:
[
  {{
    "username": "username_here",
    "profile_url": "https://reddit.com/user/username_here",
    "reason_text": "exact quote or substring showing product usage"
  }}
]

Product: {product_name}

Reddit Page Content:
{page_content}"""

            logger.info(f"Extracting users for product: {product_name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts Reddit usernames from content. You identify users who actually use products based on their comments and posts. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            content = response.choices[0].message.content.strip()
            users = self._parse_response(content)
            
            logger.info(f"Extracted {len(users)} users for {product_name}")
            return users
            
        except Exception as e:
            logger.error(f"Error extracting users for {product_name}: {e}")
            return []

    def _parse_response(self, content):
        """Parse AI response into list of user dicts."""
        users = []
        
        # Try to extract JSON from response
        try:
            # Look for JSON array in the response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                users = json.loads(json_str)
            else:
                # Try parsing the entire content as JSON
                users = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to extract users manually from text
            logger.warning("Could not parse JSON, attempting manual extraction")
            users = self._manual_extraction(content)
        
        # Validate and clean user data
        validated_users = []
        for user in users:
            if isinstance(user, dict) and 'username' in user:
                validated_user = {
                    'username': user.get('username', '').strip(),
                    'profile_url': user.get('profile_url', '').strip() or self._build_profile_url(user.get('username', '')),
                    'reason_text': user.get('reason_text', '').strip()
                }
                if validated_user['username']:
                    validated_users.append(validated_user)
        
        return validated_users

    def _build_profile_url(self, username):
        """Build Reddit profile URL from username."""
        if username:
            return f"https://reddit.com/user/{username}"
        return ""

    def _manual_extraction(self, content):
        """Manual extraction fallback if JSON parsing fails."""
        users = []
        # This is a simple fallback - could be enhanced
        username_pattern = r'u/(\w+)'
        matches = re.findall(username_pattern, content)
        for username in set(matches):
            users.append({
                'username': username,
                'profile_url': f"https://reddit.com/user/{username}",
                'reason_text': 'Extracted from page content'
            })
        return users

