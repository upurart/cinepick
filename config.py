import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, 'TMDB_API_KEY.env')
load_dotenv(env_path)

# Evrensel ayarlar.
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
AVATAR_SIZE = (1024, 1024)
JPEG_QUALITY = 85
IMAGE_MAX_PIXELS = 12_000_000


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'gizli_anahtar')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    PER_PAGE = 20


