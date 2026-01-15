#!/bin/bash

# Test script for Quick Search API
API_BASE="http://localhost:8000"

echo "=== Testing Quick Search API ==="
echo ""

# Step 1: Login to get token
echo "1. Logging in to get auth token..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed. Response:"
  echo $LOGIN_RESPONSE | python3 -m json.tool 2>/dev/null || echo $LOGIN_RESPONSE
  exit 1
fi

echo "✓ Login successful"
echo ""

# Step 2: Test Quick Search
echo "2. Testing Quick Search (YouTube search for 'skincare')..."
SEARCH_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/quick-search/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider_type": "YOUTUBE",
    "search_value": "skincare routine",
    "search_type": "search",
    "result_count": 5
  }')

echo "Response:"
echo $SEARCH_RESPONSE | python3 -m json.tool 2>/dev/null || echo $SEARCH_RESPONSE
echo ""

echo "=== Test Complete ==="
