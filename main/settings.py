import os
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG')

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'waffle',
    'core',
    'products',
    'store',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'waffle.middleware.WaffleMiddleware',
]

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PROD_DB_NAME'),
        'USER': os.getenv('PROD_DB_USER'),
        'PASSWORD': os.getenv('PROD_DB_PASSWORD'),
        'HOST': os.getenv('PROD_DB_HOST'),
        'PORT': os.getenv('PROD_DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/' 
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

# SUPABASE STORAGE CONFIG
SUPABASE_STORAGE_ENABLED = os.getenv(
    'SUPABASE_STORAGE_ENABLED',
    'false',
).strip().lower() in {'1', 'true', 'yes'}

if SUPABASE_STORAGE_ENABLED:
    from django.core.exceptions import ImproperlyConfigured

    supabase_s3_endpoint = os.getenv('SUPABASE_S3_ENDPOINT_URL')
    supabase_s3_region = os.getenv('SUPABASE_S3_REGION')
    supabase_s3_access_key = os.getenv('SUPABASE_S3_ACCESS_KEY_ID')
    supabase_s3_secret_key = os.getenv('SUPABASE_S3_SECRET_ACCESS_KEY')
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_static_bucket = os.getenv('SUPABASE_STATIC_BUCKET', 'nexra-static')
    supabase_media_bucket = os.getenv('SUPABASE_MEDIA_BUCKET', 'nexra-media')

    required_supabase_settings = {
        'SUPABASE_S3_ENDPOINT_URL': supabase_s3_endpoint,
        'SUPABASE_S3_REGION': supabase_s3_region,
        'SUPABASE_S3_ACCESS_KEY_ID': supabase_s3_access_key,
        'SUPABASE_S3_SECRET_ACCESS_KEY': supabase_s3_secret_key,
        'SUPABASE_URL': supabase_url,
        'SUPABASE_STATIC_BUCKET': supabase_static_bucket,
        'SUPABASE_MEDIA_BUCKET': supabase_media_bucket,
    }
    missing_supabase_settings = [
        name for name, value in required_supabase_settings.items() if not value
    ]
    if missing_supabase_settings:
        raise ImproperlyConfigured(
            'Supabase storage is enabled, but these settings are missing: '
            + ', '.join(missing_supabase_settings)
        )

    supabase_public_objects_url = (
        f"{supabase_url.rstrip('/')}/storage/v1/object/public"
    )
    supabase_public_objects_domain = (
        f"{urlsplit(supabase_url).netloc}/storage/v1/object/public"
    )
    common_s3_options = {
        'access_key': supabase_s3_access_key,
        'secret_key': supabase_s3_secret_key,
        'endpoint_url': supabase_s3_endpoint,
        'region_name': supabase_s3_region,
        'addressing_style': 'path',
        'signature_version': 's3v4',
        'querystring_auth': False,
        'default_acl': None,
        'url_protocol': 'https:',
    }

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                **common_s3_options,
                'bucket_name': supabase_media_bucket,
                'custom_domain': (
                    f'{supabase_public_objects_domain}/{supabase_media_bucket}'
                ),
                'location': 'media',
                'file_overwrite': False,
            },
        },
        'staticfiles': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                **common_s3_options,
                'bucket_name': supabase_static_bucket,
                'custom_domain': (
                    f'{supabase_public_objects_domain}/{supabase_static_bucket}'
                ),
                'location': 'static',
            },
        },
    }
    STATIC_URL = (
        f'{supabase_public_objects_url}/{supabase_static_bucket}/static/'
    )
    MEDIA_URL = f'{supabase_public_objects_url}/{supabase_media_bucket}/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
