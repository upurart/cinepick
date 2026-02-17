from datetime import datetime
from flask_login import UserMixin
from extensions import db

# Kullanıcı Modeli
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    watchlist = db.relationship('Watchlist', backref='author', lazy=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    avatar = db.Column(db.String(100), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

# İzleme Listesi Modeli
class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), nullable=False, default='movie')
    title = db.Column(db.String(100), nullable=False)
    poster_path = db.Column(db.String(100))
    rating = db.Column(db.String(10), default="-")
    release_date = db.Column(db.String(20), default="")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# İstatistik Modeli
class DailyStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    visit_count = db.Column(db.Integer, default=0)

# Gizli içerikler modeli
class HiddenContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(200))
    __table_args__ = (db.UniqueConstraint('tmdb_id', 'media_type', name='_tmdb_media_uc'),)

