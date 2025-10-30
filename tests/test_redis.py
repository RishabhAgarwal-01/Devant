import redis
import sys

def test_redis_connection():
    try:
        # Connect to Redis (default Docker Compose settings)
        r = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_connect_timeout=3,
            decode_responses=True  # Convert bytes to strings
        )
        
        # Test basic operations
        print("1. Connection Test:", r.ping())  # Should return True
        
        r.set("test_key", "hello_redis")
        print("2. Set Test:", r.get("test_key"))  # Should print 'hello_redis'
        
        r.delete("test_key")
        print("3. Delete Test:", r.get("test_key"))  # Should print None
        
        # Test persistence (only works if you're using volumes)
        r.set("persistent_key", "survives_restart")
        print("4. Persistence Test: Value set")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n🔍 Testing Redis Connection...")
    success = test_redis_connection()
    print("✅ Test completed successfully!" if success else "❌ Tests failed")
    sys.exit(0 if success else 1)