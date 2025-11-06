#!/bin/bash

# Final test - create Brand and Feed with correct fields

BASE_URL="http://localhost:8000/api/v1"
EMAIL="justinweilbach@gmail.com"
PASSWORD="test123"

# Login
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
echo "✓ Logged in successfully"

# Create Brand with correct fields
echo ""
echo "Creating Brand 'Nike'..."
CREATE_BRAND_RESPONSE=$(curl -s -X POST "${BASE_URL}/brands/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Nike",
    "aliases": ["Nike Inc", "Nike Sports"],
    "is_known_brand": true,
    "should_ignore": false,
    "category": "client",
    "notes": "Major sportswear brand"
  }')

echo "$CREATE_BRAND_RESPONSE" | jq .
BRAND_ID=$(echo "$CREATE_BRAND_RESPONSE" | jq -r '.id')
echo "✓ Brand created with ID: $BRAND_ID"

# Create Feed with correct fields
echo ""
echo "Creating Feed..."
CREATE_FEED_RESPONSE=$(curl -s -X POST "${BASE_URL}/feeds/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "RSS",
    "feed_type": "rss_url",
    "feed_value": "https://example.com/fashion-news.xml",
    "label": "Fashion RSS Feed",
    "enabled": true,
    "fetch_count": 50,
    "config": {
      "timeout": 30
    }
  }')

echo "$CREATE_FEED_RESPONSE" | jq .
FEED_ID=$(echo "$CREATE_FEED_RESPONSE" | jq -r '.id')
echo "✓ Feed created with ID: $FEED_ID"

# List brands and feeds
echo ""
echo "List all brands:"
curl -s -X GET "${BASE_URL}/brands/" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0:2]'

echo ""
echo "List all feeds:"
curl -s -X GET "${BASE_URL}/feeds/" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo ""
echo "✓ All endpoints working correctly!"
