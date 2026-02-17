from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_login import LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
cache = Cache()
login_manager = LoginManager()