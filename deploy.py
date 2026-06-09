#!/usr/bin/env python3
"""
AeroLux Select -- DigitalOcean Deployment Script

Automates the full production deployment:
  1. Creates a DigitalOcean Spaces bucket for media files
  2. Generates Spaces API keys
  3. Creates (or updates) the App Platform application
  4. Configures all environment variables

Usage:
    python deploy.py

Requirements:
    pip install requests boto3

Environment:
    DO_TOKEN — DigitalOcean API personal access token
    (or it will use the hardcoded token from development)
"""

import json
import os
import sys
import time
import secrets
import string

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Run: pip install requests")
    sys.exit(1)

# -----------------------------------------------
#  Configuration
# -----------------------------------------------

DO_TOKEN = os.environ.get('DO_TOKEN', '')

if not DO_TOKEN:
    print("ERROR: DO_TOKEN environment variable is required.")
    print("       Set it with: $env:DO_TOKEN = 'your_token_here'")
    sys.exit(1)

HEADERS = {
    'Authorization': f'Bearer {DO_TOKEN}',
    'Content-Type': 'application/json',
}

APP_NAME = 'aeroluxe-select'
SPACES_BUCKET = 'aeroluxe-media'
SPACES_REGION = 'nyc3'
GITHUB_REPO = 'Stan509/optimistic-archimedes'
GITHUB_BRANCH = 'main'


def generate_secret_key(length=50):
    """Generate a cryptographically secure Django secret key."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))


# -----------------------------------------------
#  Step 1: Create Spaces Bucket
# -----------------------------------------------

def create_spaces_bucket():
    """Create a DigitalOcean Spaces bucket for media files."""
    print("\n" + "=" * 60)
    print("STEP 1: Creating DigitalOcean Spaces bucket...")
    print("=" * 60)

    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("WARNING: boto3 not installed. Skipping Spaces bucket creation.")
        print("         Install with: pip install boto3")
        return None, None

    # First, create Spaces access keys via DO API
    print("  Creating Spaces access keys...")
    keys_res = requests.post(
        'https://api.digitalocean.com/v2/spaces/keys',
        headers=HEADERS,
        json={'name': f'{APP_NAME}-spaces-key'}
    )

    if keys_res.status_code in (200, 201):
        key_data = keys_res.json().get('key', keys_res.json())
        spaces_key = key_data.get('access_key', key_data.get('id', ''))
        spaces_secret = key_data.get('secret', key_data.get('secret_key', ''))
        print(f"  [OK] Spaces keys created: {spaces_key[:10]}...")
    else:
        print(f"  [INFO] Could not create Spaces keys via API (status: {keys_res.status_code})")
        print(f"         Response: {keys_res.text[:200]}")
        print("         You may need to create keys manually in the DO console.")
        print("         Go to: API -> Spaces Keys -> Generate New Key")
        spaces_key = input("  Enter Spaces Access Key (or press Enter to skip): ").strip()
        spaces_secret = input("  Enter Spaces Secret Key (or press Enter to skip): ").strip()

        if not spaces_key or not spaces_secret:
            print("  Skipping Spaces setup. Media will use local filesystem.")
            return None, None

    # Create the bucket
    print(f"  Creating bucket '{SPACES_BUCKET}' in {SPACES_REGION}...")
    endpoint = f'https://{SPACES_REGION}.digitaloceanspaces.com'

    try:
        s3_client = boto3.client(
            's3',
            region_name=SPACES_REGION,
            endpoint_url=endpoint,
            aws_access_key_id=spaces_key,
            aws_secret_access_key=spaces_secret,
        )

        try:
            s3_client.head_bucket(Bucket=SPACES_BUCKET)
            print(f"  [OK] Bucket '{SPACES_BUCKET}' already exists.")
        except ClientError:
            s3_client.create_bucket(Bucket=SPACES_BUCKET)
            print(f"  [OK] Bucket '{SPACES_BUCKET}' created.")

            # Set CORS for the bucket
            s3_client.put_bucket_cors(
                Bucket=SPACES_BUCKET,
                CORSConfiguration={
                    'CORSRules': [
                        {
                            'AllowedOrigins': ['*'],
                            'AllowedMethods': ['GET', 'HEAD'],
                            'AllowedHeaders': ['*'],
                            'MaxAgeSeconds': 3600,
                        }
                    ]
                }
            )
            print("  [OK] CORS configured for public image access.")

    except Exception as e:
        print(f"  [ERROR] Failed to create bucket: {e}")
        return spaces_key, spaces_secret

    return spaces_key, spaces_secret


# -----------------------------------------------
#  Step 2: Create App Platform Application
# -----------------------------------------------

def create_or_update_app(spaces_key=None, spaces_secret=None):
    """Create or update the DigitalOcean App Platform application."""
    print("\n" + "=" * 60)
    print("STEP 2: Deploying to DigitalOcean App Platform...")
    print("=" * 60)

    django_secret = generate_secret_key()

    # Build environment variables
    envs = [
        {"key": "DJANGO_SECRET_KEY", "value": django_secret, "type": "SECRET"},
        {"key": "DJANGO_DEBUG", "value": "False"},
        {"key": "DJANGO_ALLOWED_HOSTS", "value": ".ondigitalocean.app,aeroluxeselect-nyc.com,aeroluxeselect-dr.com,www.aeroluxeselect-nyc.com,www.aeroluxeselect-dr.com,localhost"},
        {"key": "CSRF_TRUSTED_ORIGINS", "value": "https://aeroluxeselect-nyc.com,https://aeroluxeselect-dr.com,https://www.aeroluxeselect-nyc.com,https://www.aeroluxeselect-dr.com"},
    ]

    if spaces_key and spaces_secret:
        envs.extend([
            {"key": "DO_SPACES_KEY", "value": spaces_key, "type": "SECRET"},
            {"key": "DO_SPACES_SECRET", "value": spaces_secret, "type": "SECRET"},
            {"key": "DO_SPACES_BUCKET", "value": SPACES_BUCKET},
            {"key": "DO_SPACES_REGION", "value": SPACES_REGION},
        ])

    # App spec
    app_spec = {
        "spec": {
            "name": APP_NAME,
            "region": "nyc",
            "services": [
                {
                    "name": "web",
                    "github": {
                        "repo": GITHUB_REPO,
                        "branch": GITHUB_BRANCH,
                        "deploy_on_push": True,
                    },
                    "dockerfile_path": "Dockerfile",
                    "http_port": 8000,
                    "instance_count": 1,
                    "instance_size_slug": "apps-s-1vcpu-0.5gb",
                    "routes": [{"path": "/"}],
                    "envs": envs,
                }
            ],
            "databases": [
                {
                    "name": "db",
                    "engine": "PG",
                    "production": False,
                    "version": "16",
                }
            ],
        }
    }

    # Check if app already exists
    print("  Checking for existing app...")
    apps_res = requests.get('https://api.digitalocean.com/v2/apps', headers=HEADERS)
    existing_app = None

    if apps_res.status_code == 200:
        for app in apps_res.json().get('apps', []):
            if app.get('spec', {}).get('name') == APP_NAME:
                existing_app = app
                break

    if existing_app:
        app_id = existing_app['id']
        print(f"  [INFO] App '{APP_NAME}' exists (ID: {app_id}). Updating...")

        # Update the app
        update_res = requests.put(
            f'https://api.digitalocean.com/v2/apps/{app_id}',
            headers=HEADERS,
            json=app_spec,
        )

        if update_res.status_code == 200:
            app_data = update_res.json()['app']
            print(f"  [OK] App updated successfully!")
        else:
            print(f"  [ERROR] Failed to update app: {update_res.status_code}")
            print(f"  {update_res.text[:500]}")
            return None
    else:
        print(f"  Creating new app '{APP_NAME}'...")

        create_res = requests.post(
            'https://api.digitalocean.com/v2/apps',
            headers=HEADERS,
            json=app_spec,
        )

        if create_res.status_code in (200, 201):
            app_data = create_res.json()['app']
            app_id = app_data['id']
            print(f"  [OK] App created! ID: {app_id}")
        else:
            print(f"  [ERROR] Failed to create app: {create_res.status_code}")
            print(f"  {create_res.text[:500]}")
            return None

    return app_data


# -----------------------------------------------
#  Step 3: Wait for deployment
# -----------------------------------------------

def wait_for_deployment(app_id):
    """Monitor deployment progress."""
    print("\n" + "=" * 60)
    print("STEP 3: Monitoring deployment...")
    print("=" * 60)

    max_wait = 600  # 10 minutes
    elapsed = 0
    interval = 15

    while elapsed < max_wait:
        res = requests.get(
            f'https://api.digitalocean.com/v2/apps/{app_id}',
            headers=HEADERS,
        )

        if res.status_code != 200:
            print(f"  [ERROR] Could not check app status: {res.status_code}")
            break

        app = res.json()['app']
        phase = app.get('active_deployment', {}).get('phase', 'UNKNOWN')
        live_url = app.get('live_url', 'Not yet available')

        print(f"  [{elapsed}s] Phase: {phase} | URL: {live_url}")

        if phase in ('ACTIVE', 'DEPLOYED'):
            print(f"\n  [OK] DEPLOYMENT SUCCESSFUL!")
            print(f"  Live URL: {live_url}")
            print(f"  NYC Site: {live_url}nyc/")
            print(f"  DR Site:  {live_url}dr/")
            print(f"  Dashboard: {live_url}dashboard/")
            return True

        if phase in ('ERROR', 'FAILED'):
            print(f"\n  [FAIL] DEPLOYMENT FAILED!")
            # Get deployment logs
            deployments_res = requests.get(
                f'https://api.digitalocean.com/v2/apps/{app_id}/deployments',
                headers=HEADERS,
            )
            if deployments_res.status_code == 200:
                deployments = deployments_res.json().get('deployments', [])
                if deployments:
                    latest = deployments[0]
                    print(f"  Deployment ID: {latest.get('id')}")
                    print(f"  Phase: {latest.get('phase')}")
                    print(f"  Progress: {json.dumps(latest.get('progress', {}), indent=2)}")
            return False

        time.sleep(interval)
        elapsed += interval

    print(f"\n  [TIMEOUT] Timeout after {max_wait}s. Check the DigitalOcean dashboard for status.")
    return False


# -----------------------------------------------
#  Main
# -----------------------------------------------

def main():
    print("+" + "=" * 58 + "+")
    print("|    AEROLUX SELECT -- Production Deployment             |")
    print("|    DigitalOcean App Platform                            |")
    print("+" + "=" * 58 + "+")

    # Verify token
    print("\nVerifying DigitalOcean API token...")
    account_res = requests.get(
        'https://api.digitalocean.com/v2/account',
        headers=HEADERS,
    )
    if account_res.status_code != 200:
        print(f"ERROR: Invalid DigitalOcean token. Status: {account_res.status_code}")
        sys.exit(1)

    account = account_res.json()['account']
    print(f"  Authenticated as: {account.get('email')}")
    print(f"  Status: {account.get('status')}")

    # Step 1: Spaces
    spaces_key, spaces_secret = create_spaces_bucket()

    # Step 2: App
    app_data = create_or_update_app(spaces_key, spaces_secret)
    if not app_data:
        print("\nFailed to create/update app. Exiting.")
        sys.exit(1)

    app_id = app_data['id']

    # Step 3: Monitor
    success = wait_for_deployment(app_id)

    if success:
        print("\n" + "=" * 60)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print(f"\nApp ID: {app_id}")
        print(f"Live URL: {app_data.get('live_url', 'check dashboard')}")
        print("\nNext steps:")
        print("  1. Visit the live URL to verify the site")
        print("  2. Test /nyc/ and /dr/ routes")
        print("  3. Access /dashboard/ to manage content")
        print("  4. Configure custom domains in DO dashboard")
    else:
        print("\nDeployment may still be in progress.")
        print(f"Check: https://cloud.digitalocean.com/apps/{app_id}")


if __name__ == '__main__':
    main()
