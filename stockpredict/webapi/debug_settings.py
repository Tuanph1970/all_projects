"""
Debug settings for Django development
Override default settings for enhanced debugging
"""
import os
from stockapi.settings import *

# Debug mode configuration
DEBUG = True
DJANGO_LOG_LEVEL = os.environ.get('DJANGO_LOG_LEVEL', 'DEBUG')

# Enhanced logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'colored': {
            'format': '🐛 {asctime} [{levelname}] {module}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stock': {  # Your app logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Security settings for development
ALLOWED_HOSTS = ['*']  # Allow all hosts in debug mode
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Enhanced CORS for debugging
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-debug-mode',
]

# Debug toolbar (if installed)
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        'SHOW_COLLAPSED': True,
    }
except ImportError:
    pass

# Database debugging
DATABASES['default']['OPTIONS'] = {
    **DATABASES['default'].get('OPTIONS', {}),
    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
}

# Cache debugging (disable caching in debug)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Email debugging (print to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static files debugging
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

print("🐛 DEBUG SETTINGS LOADED")
print(f"📊 Log level: {DJANGO_LOG_LEVEL}")
print("📝 Logs will be written to: debug.log")
print("🔍 SQL queries will be logged")
print("🌐 CORS configured for all origins")