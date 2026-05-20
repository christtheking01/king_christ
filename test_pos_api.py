#!/usr/bin/env python3
"""
POS API Test Script
Tests the POS API endpoint with various security configurations.

Usage:
    1. Basic test (no security):
       python test_pos_api.py --member-id 1 --amount 50000
    
    2. With API key only:
       python test_pos_api.py --member-id 1 --amount 50000 --api-key "your-key"
    
    3. Full security test:
       python test_pos_api.py --member-id 1 --amount 50000 --api-key "your-key" --secret "your-secret"
"""

import argparse
import json
import time
import hmac
import hashlib
import sys

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Install with: pip install requests")
    sys.exit(1)


def generate_signature(secret_key, timestamp, body):
    """Generate HMAC-SHA256 signature"""
    message = f"{timestamp}:{body}"
    return hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def test_pos_api(base_url, member_id, amount, api_key=None, secret_key=None, 
                 payment_method="cash", auto_print=True):
    """
    Test the POS API endpoint
    """
    url = f"{base_url}/tithe/pos/submit/"
    
    # Prepare request body
    data = {
        "member_id": member_id,
        "amount": amount,
        "payment_method": payment_method,
        "auto_print": auto_print
    }
    body = json.dumps(data)
    
    # Generate timestamp
    timestamp = str(int(time.time()))
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-Request-Timestamp": timestamp,
    }
    
    # Add API key if provided
    if api_key:
        headers["X-POS-API-Key"] = api_key
    
    # Add signature if secret key provided
    if secret_key:
        signature = generate_signature(secret_key, timestamp, body)
        headers["X-Request-Signature"] = signature
    
    print(f"\n{'='*60}")
    print("POS API Test")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Body: {body}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(url, headers=headers, data=body, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS: Payment processed!")
            return True
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server. Is it running?")
        return False
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out.")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


def test_pos_settings(base_url, api_key=None):
    """Test the POS settings endpoint"""
    url = f"{base_url}/tithe/pos/settings/"
    
    headers = {}
    if api_key:
        headers["X-POS-API-Key"] = api_key
    
    print(f"\n{'='*60}")
    print("POS Settings Test")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Test POS API Endpoint')
    parser.add_argument('--url', default='http://localhost:8000', 
                        help='Base URL (default: http://localhost:8000)')
    parser.add_argument('--member-id', type=int, required=True,
                        help='Member ID for the tithe payment')
    parser.add_argument('--amount', type=float, required=True,
                        help='Tithe amount')
    parser.add_argument('--api-key', 
                        help='POS API Key (if configured)')
    parser.add_argument('--secret-key',
                        help='Secret key for HMAC signature (if configured)')
    parser.add_argument('--payment-method', default='cash',
                        choices=['cash', 'bank'],
                        help='Payment method (default: cash)')
    parser.add_argument('--test-settings', action='store_true',
                        help='Also test the settings endpoint')
    
    args = parser.parse_args()
    
    # Test settings endpoint first if requested
    if args.test_settings:
        test_pos_settings(args.url, args.api_key)
    
    # Test payment submission
    success = test_pos_api(
        base_url=args.url,
        member_id=args.member_id,
        amount=args.amount,
        api_key=args.api_key,
        secret_key=args.secret_key,
        payment_method=args.payment_method
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
