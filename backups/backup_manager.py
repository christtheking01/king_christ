"""
Management commands for database backup and restore operations.
This module provides commands for:
- Creating database backups
- Restoring from backups
- Listing available backups
- Cleaning up old backups
"""

import os
import sys
import gzip
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection


class BackupManager:
    """Manager class for backup operations."""
    
    def __init__(self):
        self.db_config = settings.DATABASES['default']
        self.backup_dir = Path('/tmp/backups')
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_local_backup(self, filename=None):
        """Create a local database backup using pg_dump."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"db_backup_{timestamp}.sql"
        
        backup_path = self.backup_dir / filename
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            # Use pg_dump with DATABASE_URL
            cmd = f"pg_dump {db_url} > {backup_path}"
        else:
            # Use settings
            db_name = self.db_config.get('NAME', 'db.sqlite3')
            if self.db_config['ENGINE'] == 'django.db.backends.sqlite3':
                # For SQLite, just copy the file
                shutil.copy(db_name, backup_path)
                return str(backup_path)
            else:
                host = self.db_config.get('HOST', 'localhost')
                port = self.db_config.get('PORT', '5432')
                user = self.db_config.get('USER', 'postgres')
                password = self.db_config.get('PASSWORD', '')
                cmd = f"PGPASSWORD={password} pg_dump -h {host} -p {port} -U {user} {db_name} > {backup_path}"
        
        result = os.system(cmd)
        if result != 0:
            raise CommandError(f"Backup failed with exit code {result}")
        
        return str(backup_path)
    
    def compress_backup(self, backup_path):
        """Compress a backup file using gzip."""
        compressed_path = f"{backup_path}.gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(backup_path)
        return compressed_path
    
    def upload_to_s3(self, local_path, bucket_name=None, key_prefix='backups/'):
        """Upload backup to S3/Cloudflare R2."""
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL
        )
        
        bucket = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        filename = os.path.basename(local_path)
        key = f"{key_prefix}{filename}"
        
        s3.upload_file(local_path, bucket, key)
        return f"s3://{bucket}/{key}"
    
    def list_s3_backups(self, bucket_name=None, key_prefix='backups/'):
        """List all backups in S3."""
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL
        )
        
        bucket = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        response = s3.list_objects_v2(Bucket=bucket, Prefix=key_prefix)
        
        backups = []
        for obj in response.get('Contents', []):
            backups.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'],
                'url': f"s3://{bucket}/{obj['Key']}"
            })
        
        return sorted(backups, key=lambda x: x['last_modified'], reverse=True)
    
    def download_from_s3(self, key, local_path=None, bucket_name=None):
        """Download a backup from S3."""
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL
        )
        
        bucket = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        if not local_path:
            local_path = self.backup_dir / os.path.basename(key)
        
        s3.download_file(bucket, key, local_path)
        return local_path
    
    def restore_from_backup(self, backup_path, confirm=False):
        """Restore database from a backup file."""
        if not confirm:
            raise CommandError(
                "Restoring will DELETE ALL CURRENT DATA. "
                "Use --confirm flag to proceed."
            )
        
        # Decompress if needed
        if backup_path.endswith('.gz'):
            decompressed_path = backup_path[:-3]
            with gzip.open(backup_path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path = decompressed_path
        
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            cmd = f"psql {db_url} < {backup_path}"
        else:
            db_name = self.db_config.get('NAME', 'db.sqlite3')
            if self.db_config['ENGINE'] == 'django.db.backends.sqlite3':
                # For SQLite, just copy the file
                shutil.copy(backup_path, db_name)
                return
            else:
                host = self.db_config.get('HOST', 'localhost')
                port = self.db_config.get('PORT', '5432')
                user = self.db_config.get('USER', 'postgres')
                password = self.db_config.get('PASSWORD', '')
                cmd = f"PGPASSWORD={password} psql -h {host} -p {port} -U {user} {db_name} < {backup_path}"
        
        result = os.system(cmd)
        if result != 0:
            raise CommandError(f"Restore failed with exit code {result}")
    
    def cleanup_old_backups(self, days=30, bucket_name=None):
        """Remove backups older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL
        )
        
        bucket = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        response = s3.list_objects_v2(Bucket=bucket, Prefix='backups/')
        
        deleted = []
        for obj in response.get('Contents', []):
            if obj['LastModified'] < cutoff_date:
                s3.delete_object(Bucket=bucket, Key=obj['Key'])
                deleted.append(obj['Key'])
        
        return deleted
