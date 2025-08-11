#!/usr/bin/env python3
"""
Test script for AI Advanced App
"""

import asyncio
import sys
import json
import time
import httpx

BASE_URL = "http://localhost:8000"

async def test_api():
    """Test all API endpoints and return True if all pass, False otherwise."""
    all_tests_passed = True
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing AI Advanced App API...")
        print("=" * 50)
        
        # Test health check
        print("1. Testing health check...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   Services: {health_data['services']}")
            print("   ✓ Health check passed\n")
        except Exception as e:
            print(f"   ✗ Health check failed: {e}\n")
            all_tests_passed = False

        # Test root endpoint
        print("2. Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✓ Root endpoint passed\n")
        except Exception as e:
            print(f"   ✗ Root endpoint failed: {e}\n")
            all_tests_passed = False

        # Test vector search
        print("3. Testing vector search...")
        try:
            search_data = {
                "query": "database system",
                "limit": 3
            }
            response = await client.post(f"{BASE_URL}/search", json=search_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Success: {result['success']}")
                if result['success']:
                    results = result['data']['results']
                    print(f"   Found {len(results)} documents")
                print("   ✓ Vector search passed\n")
        except Exception as e:
            print(f"   ✗ Vector search failed: {e}\n")
            all_tests_passed = False

        # Test add document
        print("4. Testing add document...")
        try:
            doc_data = {
                "content": "Test document about AI and machine learning concepts.",
                "metadata": {"type": "test", "category": "ai"}
            }
            response = await client.post(f"{BASE_URL}/add_document", json=doc_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Success: {result['success']}")
                if result['success']:
                    print(f"   Document ID: {result['data']['document_id']}")
                print("   ✓ Add document passed\n")
        except Exception as e:
            print(f"   ✗ Add document failed: {e}\n")
            all_tests_passed = False

        # Test process message with vector search
        print("5. Testing process message (with vector search)...")
        try:
            process_data = {
                "message": "What do you know about databases?",
                "session_id": "test-session",
                "use_vector_search": True
            }
            response = await client.post(f"{BASE_URL}/process", json=process_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Success: {result['success']}")
                print(f"   Source: {result.get('source', 'unknown')}")
                if result['success']:
                    ai_response = result['data']['ai_response']
                    print(f"   AI Response length: {len(ai_response)} chars")
                print("   ✓ Process message passed\n")
        except Exception as e:
            print(f"   ✗ Process message failed: {e}\n")
            all_tests_passed = False

        # Test direct Gemini
        print("6. Testing direct Gemini...")
        try:
            gemini_data = {
                "message": "Tell me a short fact about Python programming."
            }
            response = await client.post(f"{BASE_URL}/gemini_direct", json=gemini_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Success: {result['success']}")
                if result['success']:
                    ai_response = result['data']['ai_response']
                    print(f"   AI Response length: {len(ai_response)} chars")
                print("   ✓ Direct Gemini passed\n")
        except Exception as e:
            print(f"   ✗ Direct Gemini failed: {e}\n")
            all_tests_passed = False

        # Test chat history
        print("7. Testing chat history...")
        try:
            response = await client.get(f"{BASE_URL}/chat_history?session_id=test-session&limit=5")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Success: {result['success']}")
                if result['success']:
                    history = result['data']['history']
                    print(f"   Chat history entries: {len(history)}")
                print("   ✓ Chat history passed\n")
        except Exception as e:
            print(f"   ✗ Chat history failed: {e}\n")
            all_tests_passed = False

        # Test list MCP tools
        print("8. Testing list MCP tools...")
        try:
            response = await client.get(f"{BASE_URL}/mcp_tools")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    tools = result['data']['tools']
                    print(f"   Available tools: {len(tools)}")
                    for tool in tools:
                        print(f"     - {tool['name']}: {tool['description']}")
                print("   ✓ List MCP tools passed\n")
        except Exception as e:
            print(f"   ✗ List MCP tools failed: {e}\n")
            all_tests_passed = False

        print("=" * 50)
        if all_tests_passed:
            print("✅ All tests passed successfully!")
        else:
            print("❌ Some tests failed.")

        return all_tests_passed

if __name__ == "__main__":
    print("Starting API tests...")
    print("Make sure the services are running with: ./start.sh")
    print("Waiting 5 seconds before starting tests...")
    time.sleep(5)

    if not asyncio.run(test_api()):
        sys.exit(1)
