"""Gunicorn configuration for Render deployment"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = 2
threads = 4
worker_class = "gthread"
worker_tmp_dir = "/dev/shm"
loglevel = "info"
errorlog = "-"
accesslog = "-"
capture_output = True
enable_stdio_inheritance = True
preload_app = True
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5