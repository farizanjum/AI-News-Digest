#!/usr/bin/env python3
"""
Test script for admin authentication and dashboard functionality.
"""

import requests
import os
from dotenv import load_dotenv

def test_admin_access():
    """Test admin access to the dashboard."""
    
    # Load environment variables
    load_dotenv()
    admin_key = os.getenv('ADMIN_API_KEY')
    
    if not admin_key:
        print("❌ ADMIN_API_KEY not found in .env file")
        return False
    
    print(f"🔑 Testing with admin key: {admin_key[:10]}...")
    
    # Test stats endpoint
    try:
        response = requests.get(
            'http://localhost:8000/api/stats',
            headers={'X-Admin-Key': admin_key},
            timeout=5
        )
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Admin authentication successful!")
            print(f"📊 Stats: {stats}")
            return True
        elif response.status_code == 401:
            print("❌ Admin authentication failed - Invalid key")
            return False
        elif response.status_code == 429:
            print("⚠️  Rate limited - Too many attempts")
            return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the server is running on http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout. Server might be slow to respond.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_dashboard_endpoints():
    """Test various dashboard endpoints."""
    
    load_dotenv()
    admin_key = os.getenv('ADMIN_API_KEY')
    
    endpoints = [
        '/api/stats',
        '/subscribers?limit=5',
        '/api/system-health',
        '/api/email-logs?limit=5'
    ]
    
    print("\n🧪 Testing dashboard endpoints:")
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                f'http://localhost:8000{endpoint}',
                headers={'X-Admin-Key': admin_key},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")

if __name__ == "__main__":
    print("🚀 AI News Digest - Admin Dashboard Test")
    print("=" * 50)
    
    if test_admin_access():
        test_dashboard_endpoints()
        print("\n✅ Admin dashboard is working!")
        print("🌐 Visit: http://localhost:8000/admin/login")
        print(f"🔑 Use admin key from .env file")
    else:
        print("\n❌ Admin dashboard test failed!")
        print("📝 Check:")
        print("   1. Server is running (python main.py)")
        print("   2. .env file exists with ADMIN_API_KEY")
        print("   3. No firewall blocking localhost:8000") 