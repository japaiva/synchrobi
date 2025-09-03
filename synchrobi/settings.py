# synchrobi/settings.py

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
import sys

# Debug para identificar problemas de logging
print("=== INICIANDO CONFIGURAÇÃO SYNCHROBI ===")
print(f"Diretório de execução atual: {os.getcwd()}")

# Carrega variáveis do arquivo .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
print(f"BASE_DIR: {BASE_DIR}")

# Criar diretório de logs
logs_dir = os.path.join(BASE_DIR, 'logs')
print(f"Criando diretório de logs em: {logs_dir}")
try:
    os.makedirs(logs_dir, exist_ok=True)
    print(f"✓ Diretório de logs criado com sucesso: {logs_dir}")
except Exception as e:
    print(f"✗ ERRO ao criar diretório de logs: {str(e)}")

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,portal.rssynchro.com.br').split(',')

# Configuração MinIO (via django-storages)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'synchrobi')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', '')
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_ADDRESSING_STYLE = 'path'

# Storage configuration
DEFAULT_FILE_STORAGE = 'core.storage.MinioStorage'
MEDIA_URL = '/media/'

# Static Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Aplicações instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'formtools',
    
    # Apps do SynchroBI
    'core',
    'gestor',
    'api',
    'storage',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'synchrobi.middleware.NotificacaoMiddleware',
    'synchrobi.middleware.AppContextMiddleware',  
]

ROOT_URLCONF = 'synchrobi.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'synchrobi.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Auth settings
AUTH_USER_MODEL = 'core.Usuario'
LOGIN_REDIRECT_URL = '/gestor/'
LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = '/login/'

# Mensagens
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Segurança (desabilitar em desenvolvimento)
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'https://portal.rssynchro.com.br',
        'http://portal.rssynchro.com.br',
    ]

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações de logging
LOG_DEBUG_PATH = os.path.join(logs_dir, 'debug.log')
LOG_DIAGNOSTIC_PATH = os.path.join(logs_dir, 'diagnostic.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': sys.stdout,
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_DEBUG_PATH,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'synchrobi': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

print("=== CONFIGURAÇÃO SYNCHROBI CONCLUÍDA ===")

# Configurações específicas do SynchroBI
SYNCHROBI_CONFIG = {
    'EMPRESA_NOME': os.getenv('EMPRESA_NOME', 'SynchroBI'),
    'EMPRESA_LOGO': os.getenv('EMPRESA_LOGO', '/static/img/logo.png'),
    'DRE_AUTO_REFRESH': int(os.getenv('DRE_AUTO_REFRESH', '300')),  # 5 minutos
    'CACHE_TIMEOUT': int(os.getenv('CACHE_TIMEOUT', '1800')),  # 30 minutos
}