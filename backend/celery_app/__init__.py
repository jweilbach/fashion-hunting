"""
Celery application for background task processing
"""
from .celery import app as celery_app

__all__ = ['celery_app']
