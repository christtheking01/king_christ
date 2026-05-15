# Church Management System - Backup & Restore Guide

## Overview

This backup system provides:
- **Automated database backups** to cloud storage (S3/Cloudflare R2)
- **Media file backups** (member photos, certificates, documents)
- **Point-in-time recovery** from any backup
- **Retention management** (auto-cleanup of old backups)
- **One-command restore** operations

---

## Quick Commands

### Create a Backup

```bash
# Create backup and upload to cloud
python manage.py create_backup

# Create compressed backup only (local)
python manage.py create_backup --local-only

# Custom filename
python manage.py create_backup --output=my_backup.sql
```

### List Available Backups

```bash
# List cloud backups (S3)
python manage.py list_backups

# List local backups
python manage.py list_backups --local

# Show more backups
python manage.py list_backups --limit=50
```

### Restore from Backup

```bash
# Restore from cloud backup (S3 key)
python manage.py restore_backup backups/db_backup_20250403_120000.sql.gz --from-s3 --confirm

# Restore from local file
python manage.py restore_backup /path/to/backup.sql.gz --confirm

# Restore and keep downloaded file
python manage.py restore_backup backups/xxx.sql.gz --from-s3 --confirm --keep-backup
```

⚠️ **WARNING**: Restore will DELETE ALL CURRENT DATA. Always confirm with `--confirm` flag.

### Cleanup Old Backups

```bash
# Delete backups older than 30 days (dry run first)
python manage.py cleanup_backups --days=30 --dry-run

# Actually delete old backups
python manage.py cleanup_backups --days=30
```

---

## Environment Setup

Add these variables to your `.env` file:

```env
# AWS/S3 Configuration (for Cloudflare R2, use endpoint)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=auto
AWS_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com

# Bucket names
BACKUP_BUCKET_NAME=church-backups
MEDIA_BUCKET_NAME=church-media

# Database (already configured)
DATABASE_URL=postgresql://...
```

---

## Restore Scenarios

### Scenario 1: Complete Database Corruption

```bash
# 1. List available backups
python manage.py list_backups

# 2. Note the backup key (e.g., backups/db_backup_20250403_120000.sql.gz)

# 3. Stop the application (prevent new writes)
# railway service stop or docker-compose stop

# 4. Restore from backup
python manage.py restore_backup backups/db_backup_20250403_120000.sql.gz --from-s3 --confirm

# 5. Restart the application
# railway service start or docker-compose up

# 6. Verify data integrity
python manage.py check
python manage.py migrate --check
```

### Scenario 2: Accidental Data Deletion (Specific Records)

If specific records were deleted but you don't want full restore:

```bash
# 1. Restore backup to a temporary database
python manage.py restore_backup backups/db_backup_xxx.sql.gz --from-s3 --confirm

# 2. Export the missing data to JSON
python manage.py dumpdata member.Member --indent 2 > members.json

# 3. Restore original database
# (Revert to previous state or restore from older backup)

# 4. Import the missing data
python manage.py loaddata members.json
```

### Scenario 3: Migration Failure

```bash
# If migration fails and database is in bad state:

# 1. Backup current state (even if broken)
python manage.py create_backup --local-only

# 2. Restore to last known good state
python manage.py restore_backup backups/db_backup_PREVIOUS.sql.gz --from-s3 --confirm

# 3. Fix migration issues in code

# 4. Re-run migrations
python manage.py migrate
```

---

## Automated Backups (Railway Scheduler)

Add to `railway.toml`:

```toml
[deploy]
startCommand = "python manage.py migrate && gunicorn christ_king_church.wsgi"

# Daily backup at 2 AM UTC
[[cron]]
name = "daily-backup"
schedule = "0 2 * * *"
command = "python manage.py create_backup"

# Weekly cleanup on Sundays at 3 AM
[[cron]]
name = "weekly-cleanup"
schedule = "0 3 * * 0"
command = "python manage.py cleanup_backups --days=30"
```

Or set up via Railway Dashboard:
1. Go to your project → Cron Jobs
2. Add Job:
   - **Name**: Daily Backup
   - **Schedule**: `0 2 * * *` (2 AM daily)
   - **Command**: `python manage.py create_backup`

---

## Backup Verification

Always test your backups! Monthly verification recommended:

```bash
# 1. Download latest backup without restoring
python manage.py list_backups

# 2. Test restore to temporary local database
# (Modify settings temporarily to point to test DB)
export DATABASE_URL=postgresql://localhost/test_restore_db
python manage.py restore_backup backups/latest.sql.gz --from-s3 --confirm

# 3. Run checks
python manage.py check
python manage.py migrate --check

# 4. Verify row counts
python manage.py shell -c "from member.models import Member; print(f'Members: {Member.objects.count()}')"
python manage.py shell -c "from users.models import User; print(f'Users: {User.objects.count()}')"

# 5. Clean up test database
dropdb test_restore_db
```

---

## Disaster Recovery Checklist

When complete data loss occurs:

- [ ] Stop all application instances immediately
- [ ] Identify most recent valid backup from `list_backups`
- [ ] Provision new database if needed
- [ ] Restore using `restore_backup` command
- [ ] Run `migrate` to ensure schema is current
- [ ] Run `collectstatic` for static files
- [ ] Verify critical data:
  - [ ] Member records
  - [ ] User accounts
  - [ ] Financial transactions
  - [ ] Event registrations
- [ ] Update DNS/URLs if infrastructure changed
- [ ] Notify users of any data loss window
- [ ] Document lessons learned

---

## Common Issues

### "AWS credentials not configured"
**Solution**: Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to environment variables.

### "pg_dump: command not found"
**Solution**: Install PostgreSQL client:
```bash
# On Railway (add to Dockerfile or nixpacks.toml)
apt-get update && apt-get install -y postgresql-client

# Or update nixpacks.toml
[phases.build]
cmds = ["apt-get update && apt-get install -y postgresql-client"]
```

### Restore hangs or fails
**Solution**: 
- Check database connection: `python manage.py dbshell`
- Verify backup file integrity: `gunzip -t backup.sql.gz`
- Try manual restore: `gunzip < backup.sql.gz | psql $DATABASE_URL`

---

## Storage Provider Setup

### Cloudflare R2 (Recommended - Free tier: 10GB)

1. Create R2 bucket at https://dash.cloudflare.com
2. Generate API token with **Object Read & Write** permission
3. Get S3-compatible credentials:
   - Access Key ID = Token ID
   - Secret Access Key = Token Secret
   - Endpoint URL from R2 dashboard

### AWS S3

1. Create S3 bucket
2. Create IAM user with `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` permissions
3. Generate access keys

### MinIO (Self-hosted)

Use same configuration with your MinIO endpoint URL.

---

## Backup Retention Policy

Default: 30 days of backups kept

Adjust in `settings.py`:
```python
DBBACKUP_CLEANUP_KEEP = 30  # Database backups
DBBACKUP_CLEANUP_KEEP_MEDIA = 30  # Media backups
```

Or run manual cleanup:
```bash
python manage.py cleanup_backups --days=7  # Keep only 7 days
```

---

## Need Help?

If restore fails or you need assistance:

1. **DO NOT PANIC** - Backups are safe in cloud storage
2. Check application logs: `railway logs` or `docker-compose logs`
3. Verify environment variables are set correctly
4. Try restoring to local database first for testing
5. Contact support with backup key (S3 path) if needed

---

**Last Updated**: April 2026  
**System Version**: Christ King Church Management v1.0
