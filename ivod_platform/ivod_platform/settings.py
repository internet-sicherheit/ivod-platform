"""
Django settings for ivod_platform project.

Generated by 'django-admin startproject' using Django 3.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
from random import getrandbits
from base64 import b64encode
import os
from sys import stderr
import datetime

# Build paths inside the project like this: BASE_DIR / 'subdir'.


BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = (os.environ.get('DEBUG', 'False').upper() == 'TRUE')

SECRET_KEY = os.environ.get('SECRET_KEY')
ADMIN_PASS = os.environ.get('ADMIN_PASS')

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'NOT_SAFE_FOR_PRODUCTION'
        print(f'----------------\nWARNING: No secret key set.\nTHIS WILL FAIL WITHOUT DEBUG!\nSecret key defaulted to {SECRET_KEY}\n----------------', file=stderr)
    else:
        raise ValueError("No secret key set. Use environment variable SECRET_KEY!")

if not ADMIN_PASS:
    if DEBUG:
        ADMIN_PASS = 'NOT_SAFE_FOR_PRODUCTION'
        print(
            f'----------------\nWARNING: No admin password set.\nTHIS WILL FAIL WITHOUT DEBUG!\nAdmin password defaulted to {SECRET_KEY}\n----------------',
            file=stderr)
    else:
        raise ValueError("No admin password set. Use environment variable ADMIN_PASS!")



# SECURITY WARNING: don't run with debug turned on in production!


if 'ALLOWED_HOSTS' in os.environ:
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split(',')
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    #'django.contrib.staticfiles',
    'corsheaders',
    'platformAPI',
    'rest_framework',
    'django_filters',
    'rest_framework_jwt',
    'rest_framework_jwt.blacklist',
    #'rest_framework_simplejwt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'platformAPI.middleware.TokenCopierMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        #'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        #'rest_framework_simplejwt.authentication.JWTAuthentication'
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
}

JWT_AUTH = {
    'JWT_AUTH_COOKIE': "JWT-Cookie",
    'JWT_EXPIRATION_DELTA': datetime.timedelta(hours=1),
}

ROOT_URLCONF = 'ivod_platform.urls'

#TODO: Manage load order of templates if specific cases occurr.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [Path(BASE_DIR).resolve().joinpath('platformFrontend').joinpath('templates')],
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

WSGI_APPLICATION = 'ivod_platform.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
AUTHENTICATION_BACKENDS = ['platformAPI.backends.EmailAuthBackend']
AUTH_USER_MODEL = "platformAPI.User"


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

# STATIC_URL = '/static/'
# STATICFILES_DIRS = [
#     str(BASE_DIR.joinpath('static'))
# ]


DATASET_BASE_URL = "./"
CHART_BASE_PATH = str(BASE_DIR.joinpath("chart_data"))
DATASOURCE_BASE_PATH = str(BASE_DIR.joinpath("datasources"))
JS_BASE_PATH = str(BASE_DIR.joinpath("code"))
#CHART_TEMPLATE = "/Path/To/Template/File"


#CORS Config
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost').split(',')

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT =True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
