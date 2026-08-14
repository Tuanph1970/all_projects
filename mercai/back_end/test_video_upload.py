#!/usr/bin/env python3
"""
Video Upload API Test Script
Tests the complete flow: Register seller → Login → Upload video

Architecture: Microservices with Traefik
- Auth Service: http://localhost:8002/api/v1/auth (port 8001 internally)
- Seller Service: http://localhost:8002/api/v1/seller (port 8005 internally)
"""

import requests
import subprocess
import os
import time
import sys
from datetime import datetime

# Configuration - Traefik routes all through port 8002
BASE_URL = "http://localhost:8002"
TEST_VIDEO_PATH = "/tmp/test_video_5sec.mp4"

# Test user credentials
TEST_USER = {
    "username": "user_1",
    "email": "user1@mercaitest.com",
    "password": "User@mercai123",
    "full_name": "Test User One",
    "role": "seller"
}


def log(message: str, level: str = "INFO"):
    """Print colored log messages"""
    colors = {
        "INFO": "\033[96m",
        "SUCCESS": "\033[92m",
        "ERROR": "\033[91m",
        "WARNING": "\033[93m",
        "STEP": "\033[95m"
    }
    reset = "\033[0m"
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{colors.get(level, '')}[{timestamp}] [{level}] {message}{reset}")


def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_test_video(output_path: str, duration: int = 5):
    """
    Create a simple test video using ffmpeg
    Generates a 5-second video with color bars and audio tone
    """
    log(f"Creating {duration}-second test video...", "STEP")
    
    # Remove existing file if present
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # ffmpeg command to create a simple test video
    # Uses testsrc2 video filter and sine audio filter
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
        "-f", "lavfi",
        "-i", f"testsrc2=duration={duration}:size=1280x720:rate=30",  # Video source
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",  # Audio source (440Hz tone)
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            log(f"✓ Test video created: {output_path}", "SUCCESS")
            log(f"  Size: {file_size:.2f} MB", "INFO")
            return True
        else:
            log(f"✗ Failed to create video: {result.stderr}", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ Error creating video: {str(e)}", "ERROR")
        return False


def register_seller_user(session: requests.Session) -> dict:
    """Register a new seller user"""
    log("Registering seller user...", "STEP")
    
    register_data = {
        "email": TEST_USER["email"],
        "password": TEST_USER["password"],
        "full_name": TEST_USER["full_name"],
        "role": TEST_USER["role"],
        "username": TEST_USER["username"]
    }
    
    try:
        response = session.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=register_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            log(f"✓ User registered successfully", "SUCCESS")
            log(f"  User ID: {data.get('user_id', 'N/A')}", "INFO")
            return {"success": True, "data": data}
        elif response.status_code == 400:
            # User might already exist
            error_detail = response.json().get("detail", "")
            if "already registered" in error_detail.lower() or "exists" in error_detail.lower():
                log(f"⚠ User already exists, will try to login", "WARNING")
                return {"success": True, "existing": True}
            else:
                log(f"✗ Registration failed: {error_detail}", "ERROR")
                return {"success": False, "error": error_detail}
        else:
            log(f"✗ Registration failed: HTTP {response.status_code}", "ERROR")
            log(f"  Response: {response.text}", "ERROR")
            return {"success": False, "error": response.text}
            
    except Exception as e:
        log(f"✗ Error during registration: {str(e)}", "ERROR")
        return {"success": False, "error": str(e)}


def login_user(session: requests.Session) -> dict:
    """Login and get access token"""
    log("Logging in to get access token...", "STEP")
    
    # Note: Auth service uses username for login, not email
    login_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    }
    
    try:
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            
            if access_token:
                log(f"✓ Login successful", "SUCCESS")
                log(f"  Token: {access_token[:30]}...", "INFO")
                return {"success": True, "token": access_token}
            else:
                log(f"✗ No access token in response", "ERROR")
                return {"success": False, "error": "No access token"}
        else:
            log(f"✗ Login failed: HTTP {response.status_code}", "ERROR")
            log(f"  Response: {response.text}", "ERROR")
            return {"success": False, "error": response.text}
            
    except Exception as e:
        log(f"✗ Error during login: {str(e)}", "ERROR")
        return {"success": False, "error": str(e)}


def upload_video(session: requests.Session, token: str, video_path: str) -> dict:
    """Upload video to the API"""
    log(f"Uploading video: {video_path}", "STEP")
    
    if not os.path.exists(video_path):
        log(f"✗ Video file not found: {video_path}", "ERROR")
        return {"success": False, "error": "Video file not found"}
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        with open(video_path, "rb") as video_file:
            files = {"file": (os.path.basename(video_path), video_file, "video/mp4")}
            
            log("  Sending upload request...", "INFO")
            start_time = time.time()
            
            response = session.post(
                f"{BASE_URL}/api/v1/seller/upload-video",
                files=files,
                headers=headers
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                log(f"✓ Video uploaded successfully in {elapsed_time:.2f}s", "SUCCESS")
                log(f"  URL: {data.get('url', 'N/A')}", "INFO")
                log(f"  Thumbnail: {data.get('thumbnail_url', 'N/A')}", "INFO")
                log(f"  Duration: {data.get('duration', 'N/A')}s", "INFO")
                log(f"  Resolution: {data.get('resolution', 'N/A')}", "INFO")
                log(f"  Size: {data.get('file_size_mb', 'N/A')} MB", "INFO")
                return {"success": True, "data": data}
            else:
                log(f"✗ Upload failed: HTTP {response.status_code}", "ERROR")
                try:
                    error_data = response.json()
                    log(f"  Error: {error_data.get('detail', 'Unknown error')}", "ERROR")
                    return {"success": False, "error": error_data.get('detail', 'Unknown error')}
                except:
                    log(f"  Response: {response.text}", "ERROR")
                    return {"success": False, "error": response.text}
                    
    except Exception as e:
        log(f"✗ Error during upload: {str(e)}", "ERROR")
        return {"success": False, "error": str(e)}


def main():
    """Main test execution"""
    log("=" * 60, "INFO")
    log("Video Upload API Test", "INFO")
    log("=" * 60, "INFO")
    log(f"Base URL: {BASE_URL}", "INFO")
    log(f"Test User: {TEST_USER['username']} ({TEST_USER['email']})", "INFO")
    log(f"Test Video: {TEST_VIDEO_PATH}", "INFO")
    log("=" * 60, "INFO")
    
    # Step 0: Check prerequisites
    log("Checking prerequisites...", "STEP")
    
    # Check ffmpeg
    if not check_ffmpeg():
        log("✗ ffmpeg not found. Please install ffmpeg first:", "ERROR")
        log("  Ubuntu/Debian: sudo apt-get install ffmpeg", "ERROR")
        log("  macOS: brew install ffmpeg", "ERROR")
        log("  Windows: Download from https://ffmpeg.org/download.html", "ERROR")
        sys.exit(1)
    log("✓ ffmpeg is installed", "SUCCESS")
    
    # Check backend connectivity
    try:
        # Test auth endpoint availability (no health endpoint in microservices)
        test_response = requests.options(
            f"{BASE_URL}/api/v1/auth/login",
            timeout=5
        )
        if test_response.status_code in [200, 405, 422]:
            log("✓ Backend is running", "SUCCESS")
        else:
            log(f"✗ Backend check failed: HTTP {test_response.status_code}", "ERROR")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        log(f"✗ Cannot connect to backend at {BASE_URL}", "ERROR")
        log("  Make sure docker containers are running: docker ps", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"✗ Backend check error: {str(e)}", "ERROR")
        sys.exit(1)
    
    # Create session
    session = requests.Session()
    
    # Step 1: Register seller user
    log("\n" + "=" * 60, "STEP")
    log("STEP 1: Register Seller User", "STEP")
    log("=" * 60, "STEP")
    
    register_result = register_seller_user(session)
    if not register_result["success"]:
        log("✗ Registration failed. Cannot continue.", "ERROR")
        sys.exit(1)
    
    # Step 2: Login
    log("\n" + "=" * 60, "STEP")
    log("STEP 2: Login to Get Token", "STEP")
    log("=" * 60, "STEP")
    
    login_result = login_user(session)
    if not login_result["success"]:
        log("✗ Login failed. Cannot continue.", "ERROR")
        sys.exit(1)
    
    token = login_result["token"]
    
    # Step 3: Create test video
    log("\n" + "=" * 60, "STEP")
    log("STEP 3: Create Test Video (5 seconds)", "STEP")
    log("=" * 60, "STEP")
    
    if not create_test_video(TEST_VIDEO_PATH, duration=5):
        log("✗ Failed to create test video. Cannot continue.", "ERROR")
        sys.exit(1)
    
    # Step 4: Upload video
    log("\n" + "=" * 60, "STEP")
    log("STEP 4: Upload Video to API", "STEP")
    log("=" * 60, "STEP")
    
    upload_result = upload_video(session, token, TEST_VIDEO_PATH)
    
    # Final Summary
    log("\n" + "=" * 60, "INFO")
    log("TEST SUMMARY", "INFO")
    log("=" * 60, "INFO")
    
    if upload_result["success"]:
        log("✓ ALL TESTS PASSED", "SUCCESS")
        log(f"  User: {TEST_USER['username']}", "INFO")
        log(f"  Video: {TEST_VIDEO_PATH}", "INFO")
        log(f"  Upload URL: {upload_result['data'].get('url', 'N/A')}", "INFO")
        log("=" * 60, "SUCCESS")
        sys.exit(0)
    else:
        log("✗ TEST FAILED", "ERROR")
        log(f"  Error: {upload_result.get('error', 'Unknown')}", "ERROR")
        log("=" * 60, "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
