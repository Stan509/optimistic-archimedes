"""
Aero Luxe Select — Sync Local Media to DigitalOcean Spaces

Django management command that uploads all files from the local media/
directory to DigitalOcean Spaces (S3-compatible storage).

This is called automatically from entrypoint.sh on each deployment
to ensure seed images are available in production.
"""

import os
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sync local media files to DigitalOcean Spaces'

    def handle(self, *args, **options):
        spaces_key = os.environ.get('DO_SPACES_KEY')
        spaces_secret = os.environ.get('DO_SPACES_SECRET')
        bucket_name = getattr(settings, 'DO_SPACES_BUCKET', 'aeroluxe-media')
        region = getattr(settings, 'DO_SPACES_REGION', 'nyc3')
        endpoint = f'https://{region}.digitaloceanspaces.com'

        if not spaces_key or not spaces_secret:
            self.stdout.write(self.style.WARNING(
                'DO_SPACES_KEY / DO_SPACES_SECRET not set. Skipping media sync.'
            ))
            return

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            self.stdout.write(self.style.ERROR('boto3 is not installed. Run: pip install boto3'))
            return

        # Initialize S3 client
        client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=spaces_key,
            aws_secret_access_key=spaces_secret,
        )

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write(self.style.WARNING(f'Media directory not found: {media_root}'))
            return

        uploaded = 0
        skipped = 0

        for file_path in media_root.rglob('*'):
            if file_path.is_dir():
                continue

            # Relative path becomes the S3 key
            relative = file_path.relative_to(media_root)
            s3_key = f'media/{relative.as_posix()}'

            # Check if file already exists in Spaces
            try:
                client.head_object(Bucket=bucket_name, Key=s3_key)
                skipped += 1
                continue
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    self.stdout.write(self.style.ERROR(
                        f'Error checking {s3_key}: {e}'
                    ))
                    continue

            # Detect content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            extra_args = {
                'ACL': 'public-read',
            }
            if content_type:
                extra_args['ContentType'] = content_type

            # Upload
            try:
                client.upload_file(
                    str(file_path),
                    bucket_name,
                    s3_key,
                    ExtraArgs=extra_args,
                )
                uploaded += 1
                self.stdout.write(f'  Uploaded: {s3_key}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed: {s3_key} — {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Media sync complete: {uploaded} uploaded, {skipped} already existed.'
        ))
