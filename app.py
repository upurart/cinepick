from flask import Flask, render_template, url_for, redirect, request, jsonify, flash, session
from flask_login import login_required, login_user, logout_user, current_user
from sqlalchemy import or_
from functools import wraps
from datetime import datetime, date
import os
import textwrap
from PIL import Image

from config import Config, UPLOAD_FOLDER, AVATAR_SIZE, JPEG_QUALITY, IMAGE_MAX_PIXELS
from extensions import db, bcrypt, cache, login_manager
from helpers import (
    get_tmdb_image,
    make_tmdb_request,
    get_trailer_key_cached,
    get_genre_map,
    inject_watchlist_status,
    force_latin,
    process_media_data,
    format_date_tr,
    get_hidden_items_set,
    filter_hidden_content,
    make_actor_cache_key,
    allowed_file,
)

Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
bcrypt.init_app(app)
cache.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login_page'

from models import User, Watchlist, DailyStats, HiddenContent
# Login için gerekli; session ID'sinden kullanıcı nesnesini veritabanından çeker.
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Sadece yönetici yetkisine sahip kullanıcıların erişimine izin verir.
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Bu sayfaya erişim yetkiniz yok.", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


# Her sayfa isteğinden önce çalışarak günlük ziyaretçi sayısını tutar.
@app.before_request
def track_visits():
    if request.path.startswith('/static') or request.path.startswith('/admin'):
        return

    today = date.today()
    last_visit = session.get('last_visit_date')

    if last_visit == str(today):
        return

    try:
        stats = DailyStats.query.filter_by(date=today).first()

        if stats:
            stats.visit_count += 1
            print(f"[{datetime.now()}] Sayaç Artırıldı! Yeni Değer: {stats.visit_count}")
        else:
            stats = DailyStats(date=today, visit_count=1)
            db.session.add(stats)
            print(f"[{datetime.now()}] Yeni Sayaç Kaydı Oluşturuldu. Değer: 1")

        db.session.commit()

        session['last_visit_date'] = str(today)

    except Exception as e:
        db.session.rollback()
        print(f"Sayaç Hatası: {e}")




app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Kullanıcının yüklediği avatar dosyasını işler (Merkez noktasından 1024*1024 çözünürlüğünde kırpar ve /uploads klasörüne kaydeder).
@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar_file' not in request.files:
        flash('Dosya bulunamadı.', 'error')
        return redirect(url_for('account'))

    file = request.files['avatar_file']

    if file.filename == '':
        flash('Dosya seçilmedi.', 'error')
        return redirect(url_for('account'))

    if file and allowed_file(file.filename):
        try:
            filename_base = f"user_{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            file_extension = file.filename.rsplit('.', 1)[1].lower()

            unique_filename = f"{filename_base}.{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            img = Image.open(file)


            width, height = img.size
            min_dim = min(width, height)

            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            right = (width + min_dim) // 2
            bottom = (height + min_dim) // 2

            img = img.crop((left, top, right, bottom))

            img = img.resize(AVATAR_SIZE, Image.LANCZOS)

            if file_extension in ('jpg', 'jpeg'):
                img = img.convert("RGB")
                img.save(file_path, quality=JPEG_QUALITY)
            else:
                img.save(file_path)

            if current_user.avatar:
                old_avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)

            current_user.avatar = unique_filename
            db.session.commit()


            return redirect(url_for('account'))

        except Exception as e:
            db.session.rollback()
            print(f"Avatar yükleme/işleme hatası: {e}")
            flash('Dosya işlenirken bir hata oluştu.', 'error')
            return redirect(url_for('account'))
    else:
        flash('Geçersiz dosya türü. Sadece PNG, JPG, JPEG, GIF desteklenir.', 'error')
        return redirect(url_for('account'))


# Belirtilen kullanıcının avatar dosyasını sunucudan siler ve veritabanını günceller.
@app.route('/remove_avatar/<int:user_id>', methods=['POST'])
@login_required
def remove_avatar(user_id):
    user_id = int(user_id)
    user = User.query.get_or_404(user_id)

    if user.id != current_user.id and not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Bu işlemi yapmaya yetkiniz yok.'}), 403

    if user.avatar:
        old_avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], user.avatar)

        try:
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
                print(f"Avatar dosyası silindi: {old_avatar_path}")

            user.avatar = None
            db.session.commit()

            return jsonify({'status': 'success', 'message': 'Avatar başarıyla kaldırıldı.'})

        except OSError as e:
            db.session.rollback()
            print(f"Dosya silme hatası: {e}")
            return jsonify({'status': 'error', 'message': 'Dosya sisteminde hata oluştu.'}), 500

    else:
        return jsonify({'status': 'info', 'message': 'Kullanıcının zaten avatarları yok.'})


# Admin panelinin ana sayfasını; kullanıcı, film ve ziyaretçi istatistikleriyle birlikte getirir.
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():

    user_count = User.query.count()
    total_watchlist_items = Watchlist.query.count()

    hidden_content_count = HiddenContent.query.count()

    today = date.today()
    daily_stats = DailyStats.query.filter_by(date=today).first()
    daily_count = daily_stats.visit_count if daily_stats else 0

    stats = {
        'total_users': user_count,
        'total_movies': total_watchlist_items,
        'daily_visits': daily_count,
        'pending_comments': 0,
        'hidden_count': hidden_content_count
    }

    latest_users_query = User.query.order_by(User.id.desc())

    latest_users = latest_users_query.limit(10).all()

    return render_template('admin/dashboard.html',
                           stats=stats,
                           users=latest_users)


from datetime import datetime, date

# Kayıtlı kullanıcıları listeler; arama, sayfalama ve sıralama işlemlerini yönetir.
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    query = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', None)

    users_query = User.query

    if query:
        users_query = users_query.filter(or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        ))

    if sort_by:
        if sort_by == 'id_desc':
            users_query = users_query.order_by(User.id.desc())
        elif sort_by == 'id_asc':
            users_query = users_query.order_by(User.id.asc())
        elif sort_by == 'username_asc':
            users_query = users_query.order_by(User.username.asc())
        elif sort_by == 'username_desc':
            users_query = users_query.order_by(User.username.desc())
        elif sort_by == 'email_asc':
            users_query = users_query.order_by(User.email.asc())
        elif sort_by == 'email_desc':
            users_query = users_query.order_by(User.email.desc())
        elif sort_by == 'admin_asc':
            users_query = users_query.order_by(User.is_admin.asc())
        elif sort_by == 'admin_desc':
            users_query = users_query.order_by(User.is_admin.desc())

    pagination = users_query.paginate(page=page, per_page=app.config['PER_PAGE'], error_out=False)

    users_data = pagination.items

    today = date.today()

    for user in users_data:
        registration_date = user.created_at.date()

        delta = today - registration_date

        user.days_active = delta.days


    return render_template('admin/users.html',
                           users=users_data,
                           search_query=query,
                           current_page=pagination.page,
                           total_pages=pagination.pages,
                           current_sort=sort_by)


# İçerik yönetimi için filmleri/dizileri listeler ve gizlilik durumlarını gösterir.
@app.route('/admin/movies')
@login_required
@admin_required
def admin_movies():
    query = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', None)

    movies_data = []
    tmdb_params = {'page': page, 'include_adult': 'false'}

    if query:
        tmdb_params['query'] = query
        data = make_tmdb_request('/search/multi', tmdb_params)
    else:
        data = make_tmdb_request('/trending/all/week', tmdb_params)

    api_total_pages = data.get('total_pages', 1) if data else 1
    total_pages = min(api_total_pages, 500)

    if data:
        for item in data.get('results', []):
            if item.get('media_type') in ['movie', 'tv'] or not item.get('media_type'):
                processed = process_media_data(item)
                if processed: movies_data.append(processed)

    hidden_items = get_hidden_items_set()

    for m in movies_data:
        try:
            tmdb_id = int(m['id'])
        except (TypeError, ValueError):
            tmdb_id = m['id']

        m['is_hidden'] = (tmdb_id, m['media_type']) in hidden_items

    if sort_by:
        if sort_by == 'id_desc':
            movies_data.sort(key=lambda x: int(x['id']), reverse=True)
        elif sort_by == 'id_asc':
            movies_data.sort(key=lambda x: int(x['id']), reverse=False)

        elif sort_by == 'title_asc':
            movies_data.sort(key=lambda x: x['title'].lower(), reverse=False)
        elif sort_by == 'title_desc':
            movies_data.sort(key=lambda x: x['title'].lower(), reverse=True)

        elif sort_by == 'type_movie':
            movies_data.sort(key=lambda x: 0 if x['media_type'] == 'movie' else 1)
        elif sort_by == 'type_tv':
            movies_data.sort(key=lambda x: 0 if x['media_type'] == 'tv' else 1)

        elif sort_by == 'status_active':
            movies_data.sort(key=lambda x: 0 if not x['is_hidden'] else 1)
        elif sort_by == 'status_hidden':
            movies_data.sort(key=lambda x: 0 if x['is_hidden'] else 1)

    current_page = page if page <= total_pages else 1

    return render_template('admin/movies.html',
                           movies=movies_data,
                           search_query=query,
                           current_page=current_page,
                           total_pages=total_pages,
                           current_sort=sort_by)


# Yönetici panelinden bir kullanıcının bilgilerini (ad, e-posta, yetki) günceller.
@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_id = int(user_id)

    user = User.query.get_or_404(user_id)

    new_username = request.form.get('username')
    new_email = request.form.get('email')
    is_admin_checked = 'is_admin' in request.form

    if user.id == current_user.id and user.is_admin and not is_admin_checked:
        flash("Güvenlik nedeniyle kendi Admin yetkinizi bu ekrandan kaldıramazsınız.", "error")
        return redirect(url_for('admin_users'))

    try:
        user.username = new_username
        user.email = new_email
        user.is_admin = is_admin_checked

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Güncelleme sırasında hata oluştu (Kullanıcı adı veya e-posta kullanımda olabilir).", "error")

    return redirect(url_for('admin_users'))

# Yönetici panelinden bir kullanıcıyı ve ona ait verileri kalıcı olarak siler.
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user_id = int(user_id)
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'status': 'error', 'message': 'Kendinizi silemezsiniz!'}), 403
    if user.id == 1:
        return jsonify({'status': 'error', 'message': 'Birincil Admin hesabı silinemez!'}), 403

    try:
        Watchlist.query.filter_by(user_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()

        return jsonify({'status': 'success', 'message': f"'{user.username}' adlı kullanıcı silindi."})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Silme işleminde veritabanı hatası oluştu.'}), 500

# Bir içeriği (film/dizi) veritabanına ekleyerek gizler veya veritabanından silerek görünür yapar.
@app.route('/admin/toggle_visibility', methods=['POST'])
@login_required
@admin_required
def toggle_visibility():
    data = request.json
    tmdb_id = int(data.get('id'))
    media_type = data.get('media_type')
    title = data.get('title')

    existing = HiddenContent.query.filter_by(tmdb_id=tmdb_id, media_type=media_type).first()

    try:
        if existing:
            db.session.delete(existing)
            db.session.commit()
            status = 'visible'
        else:
            new_hidden = HiddenContent(tmdb_id=tmdb_id, media_type=media_type, title=title)
            db.session.add(new_hidden)
            db.session.commit()
            status = 'hidden'

        cache.delete('home_slider_content')
        cache.delete('home_weekly_content')
        cache.delete_memoized(get_hidden_items_set)


        return jsonify({'status': status, 'message': 'İçerik artık görünür.' if status == 'visible' else 'İçerik gizlendi.'})

    except Exception as e:
        db.session.rollback()
        print(f"Gizleme/Gösterme Hatası: {e}")
        return jsonify({'status': 'error', 'message': 'Veritabanı hatası.'}), 500



# Ana sayfayı oluşturur, slider, trendler ve kullanıcı izleme listesi içerir.
@app.route('/')
def home():
    slider_content_raw = cache.get('home_slider_content')

    if not slider_content_raw:
        slider_content_raw = []
        data_day = make_tmdb_request('/trending/all/day')
        if data_day:
            for m in data_day.get('results', [])[:10]:
                processed = process_media_data(m)
                if processed:
                    if processed.get('overview'):
                        processed['overview'] = textwrap.shorten(processed['overview'], width=200, placeholder="...")

                    key = get_trailer_key_cached(processed['media_type'], m['id'])
                    processed['trailer_url'] = f"https://www.youtube.com/watch?v={key}" if key else None
                    slider_content_raw.append(processed)

        if not slider_content_raw:
             slider_content_raw = [{"id":0, "title":"Yukleniyor", "poster": get_tmdb_image(None), "overview": "...", "media_type": "movie"}]

        slider_content_raw = filter_hidden_content(slider_content_raw)

        cache.set('home_slider_content', slider_content_raw, timeout=600)

    final_slider = inject_watchlist_status(slider_content_raw, current_user)

    weekly_content_raw = cache.get('home_weekly_content')

    if not weekly_content_raw:
        weekly_content_raw = []
        data_week = make_tmdb_request('/trending/all/week')
        if data_week:
            weekly_content_raw = [m for m in (process_media_data(m) for m in data_week.get('results', [])) if m is not None]

        weekly_content_raw = filter_hidden_content(weekly_content_raw)

        cache.set('home_weekly_content', weekly_content_raw, timeout=600)

    final_weekly = inject_watchlist_status(weekly_content_raw, current_user)

    hidden_items = get_hidden_items_set()
    watchlist_items = []
    if current_user.is_authenticated:
        user_list = Watchlist.query.filter_by(user_id=current_user.id).limit(5).all()
        for item in user_list:
            if not item.poster_path: continue

            if (item.media_id, item.media_type) in hidden_items:
                continue

            watchlist_items.append({
                "id": item.media_id,
                "media_type": item.media_type,
                "title": item.title,
                "poster": get_tmdb_image(item.poster_path),
                "rating": item.rating,
                "release_date": (item.release_date or '')[:4]
            })

    return render_template('index.html',
                           movies=final_slider,
                           weekly_movies=final_weekly,
                           watchlist_movies=watchlist_items)

# Seçilen film veya dizinin tüm detaylarını (oyuncular, fragman, benzer içerikler vb.) gösterir.
@app.route('/content/<string:media_type>/<int:id>')
def content_detail(media_type, id):
    if media_type not in ['movie', 'tv']:
        return redirect(url_for('home'))

    if not (current_user.is_authenticated and current_user.is_admin):
        hidden_items = get_hidden_items_set()
        if (id, media_type) in hidden_items:
            flash("Bu içerik şu anda gizlenmiştir.", "warning")
            return redirect(url_for('home'))

    hidden_items = get_hidden_items_set()

    params = {
        'append_to_response': 'credits,videos,images,translations,recommendations,similar',
        'include_image_language': 'en,tr,null',
        'include_video_language': 'tr,en'
    }
    item = make_tmdb_request(f"/{media_type}/{id}", params)

    if not item: return redirect(url_for('home'))

    title = item.get('title') if media_type == 'movie' else item.get('name')
    original_title = item.get('original_title') if media_type == 'movie' else item.get('original_name')
    date_field = item.get('release_date') if media_type == 'movie' else item.get('first_air_date')

    season_count = item.get('number_of_seasons') if media_type == 'tv' else None
    episode_count = item.get('number_of_episodes') if media_type == 'tv' else None
    seasons = item.get('seasons', []) if media_type == 'tv' else []

    processed_seasons = []
    if seasons:
        for s in seasons:
            if s.get('season_number') > 0:
                processed_seasons.append({
                    'name': s.get('name'),
                    'episode_count': s.get('episode_count'),
                    'air_date': (s.get('air_date') or '')[:4],
                    'poster': get_tmdb_image(s.get('poster_path'), 'w185'),
                    'overview': s.get('overview')
                })

    overview = item.get('overview')

    if not overview or item.get('original_language') not in ['tr', 'en']:
        for t in item.get('translations', {}).get('translations', []):
            if t['iso_639_1'] == 'en':
                data = t['data']
                if not overview and data.get('overview'): overview = data['overview']
                eng_title = data.get('title') if media_type == 'movie' else data.get('name')
                if title == original_title and eng_title: title = eng_title
                break

    images = item.get('images', {}).get('posters', [])
    poster_path = item.get('poster_path')
    for lang in ['en', 'tr', 'null']:
        found = next((img['file_path'] for img in images if img['iso_639_1'] == lang), None)
        if found:
            poster_path = found
            break

    director = "Bilinmiyor"
    crew = item.get('credits', {}).get('crew', [])

    if media_type == 'movie':
        director = next((force_latin(m['name']) for m in crew if m['job'] == 'Director'), "Bilinmiyor")
    else:
        created_by = item.get('created_by', [])
        if created_by:
            director = ", ".join([force_latin(c['name']) for c in created_by])

    cast = item.get('credits', {}).get('cast', [])[:10]
    processed_cast = [{
        'id': a['id'],
        'name': force_latin(a['name']),
        'character': a['character'],
        'photo': f"https://image.tmdb.org/t/p/w185{a['profile_path']}" if a.get('profile_path') else None
    } for a in cast]

    videos = item.get('videos', {}).get('results', [])

    all_trailers = [v for v in videos if v.get('site') == 'YouTube' and v.get('type') == 'Trailer']

    trailer_key = None
    if all_trailers:
        tr_trailer = next((v for v in all_trailers if v.get('iso_639_1') == 'tr'), None)
        en_trailer = next((v for v in all_trailers if v.get('iso_639_1') == 'en'), None)

        if tr_trailer:
            trailer_key = tr_trailer['key']
        elif en_trailer:
            trailer_key = en_trailer['key']
        else:
            trailer_key = all_trailers[0]['key']

    recommendations = item.get('recommendations', {}).get('results', [])
    if len(recommendations) < 3:
        recommendations += item.get('similar', {}).get('results', [])

    similar = []
    ids_seen = set()
    for s in recommendations:
        if s['id'] in ids_seen: continue
        ids_seen.add(s['id'])

        if not s.get('media_type'): s['media_type'] = media_type

        processed_sim = process_media_data(s, specific_type=media_type)

        if processed_sim:
            if (processed_sim['id'], processed_sim['media_type']) not in hidden_items:
                if processed_sim.get('title'):
                    processed_sim['title'] = textwrap.shorten(processed_sim['title'], width=22, placeholder="...")
                similar.append(processed_sim)

        if len(similar) >= 6: break

    in_watchlist = False
    if current_user.is_authenticated:
        in_watchlist = bool(Watchlist.query.filter_by(user_id=current_user.id, media_id=id, media_type=media_type).first())

    context = {
        'id': item['id'],
        'media_type': media_type,
        'title': title,
        'original_title': original_title,
        'overview': overview,
        'poster': get_tmdb_image(poster_path),
        'backdrop': get_tmdb_image(item.get('backdrop_path'), 'w1280'),
        'release_date': date_field,
        'genres': [g['name'] for g in item.get('genres', [])],
        'vote_average': round(item.get('vote_average', 0), 1),
        'director': director,
        'cast': processed_cast,
        'trailer_url': f"https://www.youtube.com/embed/{trailer_key}" if trailer_key else None,
        'similar_movies': similar,
        'in_watchlist': in_watchlist,
        'season_count': season_count,
        'episode_count': episode_count,
        'seasons': processed_seasons,
        'runtime': item.get('runtime')
    }

    return render_template('movie-details.html', movie=context)

# Oyuncu detay sorgusu için unique bir önbellek anahtarı oluşturur.
def make_actor_cache_key(*args, **kwargs):
    actor_id = kwargs.get('actor_id')
    return f'actor_detail_{actor_id}'

# Oyuncunun biyografisini, kişisel bilgilerini ve rol aldığı yapımları (filmografi) getirir.
@app.route('/actor/<int:actor_id>')
@cache.cached(timeout=86400, make_cache_key=make_actor_cache_key)
def actor_detail(actor_id):
    params = {
        'append_to_response': 'combined_credits,images,translations',
        'language': 'tr-TR'
    }

    actor_data = make_tmdb_request(f"/person/{actor_id}", params)

    if not actor_data:
        flash("Oyuncu bilgileri şu anda bulunamadı.", "error")
        return redirect(url_for('home'))

    name = actor_data.get('name')
    biography = actor_data.get('biography')

    if not biography or biography.strip() == "":
        eng_data = make_tmdb_request(f"/person/{actor_id}", {'language': 'en-US', 'append_to_response': 'translations'})
        if eng_data:
            eng_biography = eng_data.get('biography')
            if eng_biography and eng_biography.strip() != "":
                biography = eng_biography
            if name == actor_data.get('original_name') and eng_data.get('name'):
                 name = eng_data.get('name')

        if not biography or biography.strip() == "":
            translations = actor_data.get('translations', {}).get('translations', [])
            for t in translations:
                if t['iso_639_1'] == 'en' and t['data'].get('biography'):
                     biography = t['data']['biography']
                     break
            if not biography or biography.strip() == "":
                biography = actor_data.get('original_biography')

    if not biography or biography.strip() == "":
        biography = "Bu oyuncu/yönetmen hakkında detaylı biyografi bulunmamaktadır."

    credits_raw_cast = actor_data.get('combined_credits', {}).get('cast', [])
    credits_raw_crew = actor_data.get('combined_credits', {}).get('crew', [])

    all_credits = credits_raw_cast + credits_raw_crew

    processed_credits = []
    known_for_candidates = []
    ids_seen = set()

    for credit in all_credits:
        media_type = credit.get('media_type')
        item_id = credit.get('id')

        if media_type not in ['movie', 'tv'] or item_id in ids_seen:
            continue

        ids_seen.add(item_id)

        processed = process_media_data(credit, specific_type=media_type)

        if processed:
            processed['vote_count'] = credit.get('vote_count', 0)

            if processed.get('poster'):
                known_for_candidates.append(processed)

            is_cast = 'character' in credit

            if is_cast:
                role_key = credit.get('character', 'Bilinmiyor')
            else:
                role_key = credit.get('job', 'Ekip Üyesi')

            release_date_field = credit.get('release_date') if media_type == 'movie' else credit.get('first_air_date')
            release_year = (release_date_field or '9999')[:4]

            # Tablo için sadeleştirilmiş veri
            processed_credits.append({
                'id': processed['id'],
                'media_type': processed['media_type'],
                'title': processed['title'],
                'year': release_year,
                'character': role_key,
                'is_cast': is_cast,
                'sort_key': release_year
            })

    # Filmografiyi yıla göre sırala (Yeniden eskiye)
    processed_credits.sort(key=lambda x: x['sort_key'], reverse=True)

    # Bilinen yapımları OY SAYISINA (vote_count) göre sırala ve ilk 10'u al
    known_for_candidates.sort(key=lambda x: x.get('vote_count', 0), reverse=True)
    top_known_for = known_for_candidates[:10]

    context = {
        'id': actor_id,
        'name': force_latin(name),
        'original_name': actor_data.get('original_name'),
        'known_for_department': actor_data.get('known_for_department'),
        'biography': biography,
        'birthday': format_date_tr(actor_data.get('birthday')),
        'deathday': format_date_tr(actor_data.get('deathday')) if actor_data.get('deathday') else None,
        'place_of_birth': actor_data.get('place_of_birth') or 'Bilinmiyor',
        'profile_path': get_tmdb_image(actor_data.get('profile_path')),

        'known_for': top_known_for,  # <--- EKLENEN KISIM

        'filmography': processed_credits,
        'credits': processed_credits, # Yedek uyumluluk
        'homepage': actor_data.get('homepage')
    }

    return render_template('actor-details.html', actor=context)

# Tüm filmleri/dizileri listeler; sayfalama, filtreleme (tür, puan) ve sıralama seçenekleri sunar.
@app.route('/all_movies')
def all_movies():
    page = request.args.get('page', 1, type=int)
    sort_val = request.args.get('sort', 'popularity.desc')
    media_type = request.args.get('type', 'all')
    genres_val = request.args.get('genres')
    rating_val = request.args.get('rating')

    if media_type not in ['movie', 'tv', 'all']: media_type = 'all'

    params = {
        'page': page,
        'language': 'tr-TR',
        'sort_by': sort_val,
        'vote_count.gte': 10,
        'include_adult': 'false'
    }

    if rating_val: params['vote_average.gte'] = rating_val
    if genres_val: params['with_genres'] = genres_val

    content_raw = []
    total_pages = 1

    if media_type == 'all':
        is_filtering = (genres_val or rating_val or sort_val != 'popularity.desc')

        if not is_filtering:
            data = make_tmdb_request('/trending/all/week', {'page': page, 'language': 'tr-TR'})
            if data:
                content_raw = data.get('results', [])
                total_pages = data.get('total_pages', 1)
        else:

            movies_data = make_tmdb_request('/discover/movie', params)
            tv_data = make_tmdb_request('/discover/tv', params)

            m_results = movies_data.get('results', []) if movies_data else []
            t_results = tv_data.get('results', []) if tv_data else []

            for m in m_results: m['media_type'] = 'movie'
            for t in t_results: t['media_type'] = 'tv'

            content_raw = m_results + t_results

            is_reverse = 'desc' in sort_val
            sort_key = sort_val.split('.')[0]

            def get_sort_value(item):
                if sort_key == 'original_title':
                    return item.get('title') or item.get('name') or ''
                return item.get(sort_key, 0)

            content_raw.sort(key=get_sort_value, reverse=is_reverse)

            m_pages = movies_data.get('total_pages', 1) if movies_data else 1
            t_pages = tv_data.get('total_pages', 1) if tv_data else 1
            total_pages = max(m_pages, t_pages)

    else:
        endpoint = f'/discover/{media_type}'
        data = make_tmdb_request(endpoint, params)

        if data:
            content_raw = data.get('results', [])
            total_pages = data.get('total_pages', 1)
            if total_pages > 500: total_pages = 500

    final_content = []
    for item in content_raw:
        current_item_type = item.get('media_type', media_type)

        proc = process_media_data(item, specific_type=current_item_type)
        if proc:
            final_content.append(proc)

    final_content = filter_hidden_content(final_content)
    final_content = inject_watchlist_status(final_content, current_user)

    return render_template('all-movies.html',
                           movies=final_content,
                           current_page=page,
                           total_pages=total_pages,
                           current_type=media_type)


# Eski URL yapısı ile gelen istekleri yeni içerik detay sayfasına yönlendirir.
@app.route('/film/<int:movie_id>')
def movie_detail(movie_id):
    return redirect(url_for('content_detail', media_type='movie', id=movie_id))

# Kullanıcının arama sorgusunu alır, TMDB'de arar ve sonuçları listeler.
@app.route('/search')
def search():
    query = request.args.get('q')
    if not query: return redirect(url_for('home'))

    data = make_tmdb_request('/search/multi', {'query': query, 'include_adult': 'false'})
    results_raw = []
    if data:
        for m in data.get('results', []):
            proc = process_media_data(m)
            if proc: results_raw.append(proc)

    final_results = inject_watchlist_status(results_raw, current_user)
    return render_template('search.html', movies=final_results, query=query)

# Belirtilen içeriği kullanıcının izleme listesine ekler.
@app.route('/add_to_watchlist/<string:media_type>/<int:id>', methods=['POST'])
@login_required
def add_to_watchlist(media_type, id):
    if media_type not in ['movie', 'tv']:
        return jsonify({'status': 'error', 'message': 'Geçersiz medya türü.'}), 400

    exists = Watchlist.query.filter_by(user_id=current_user.id, media_id=id, media_type=media_type).first()
    if exists:
        return jsonify({'status': 'exists', 'message': 'Listenizde zaten var.'})

    data = make_tmdb_request(f'/{media_type}/{id}')
    if not data:
        return jsonify({'status': 'error', 'message': 'Bilgiler alınamadı.'}), 404

    title = data.get('title') if media_type == 'movie' else data.get('name')
    date_val = data.get('release_date') if media_type == 'movie' else data.get('first_air_date')
    poster_path = data.get('poster_path')
    rating = str(round(data.get('vote_average', 0), 1))

    orig_lang = data.get('original_language')
    if (not poster_path or orig_lang not in ['tr', 'en']):
        try:
            img_params = {'include_image_language': 'en,null', 'language': 'en-US'}
            images_data = make_tmdb_request(f"/{media_type}/{id}/images", img_params)
            if images_data and images_data.get('posters'):
                poster_path = images_data['posters'][0]['file_path']
        except Exception: pass

    if not poster_path:
        return jsonify({'status': 'error', 'message': 'Posteri olmayan içerik eklenemez.'}), 404

    try:
        new_item = Watchlist(
            user_id=current_user.id,
            media_id=id,
            media_type=media_type,
            title=title or "Bilinmiyor",
            poster_path=poster_path,
            rating=rating,
            release_date=date_val or ""
        )
        db.session.add(new_item)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Listeye eklendi.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Veritabanı hatası.'}), 500

# Belirtilen içeriği kullanıcının izleme listesinden kaldırır.
@app.route('/remove_from_watchlist/<string:media_type>/<int:id>', methods=['POST'])
@login_required
def remove_from_watchlist(media_type, id):
    item = Watchlist.query.filter_by(user_id=current_user.id, media_id=id, media_type=media_type).first()

    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'status': 'removed', 'message': 'Çıkarıldı.'})
    else:
        return jsonify({'status': 'error', 'message': 'Listede bulunamadı.'})


# Kullanıcının izleme listesindeki filmleri ve dizileri listeler.
@app.route('/watchlist')
@login_required
def watchlist():
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    content = []

    hidden_items = get_hidden_items_set()

    for item in user_watchlist:
        if not item.poster_path: continue

        if (item.media_id, item.media_type) in hidden_items:
            continue

        content.append({
            'id': item.media_id,
            'media_type': item.media_type,
            'title': item.title,
            'poster': get_tmdb_image(item.poster_path),
            'rating': item.rating,
            'year': item.release_date[:4] if item.release_date else '',
            'overview': ''
        })
    return render_template('watchlist.html', movies=content)


from flask import request, url_for, redirect, render_template, flash


# Kullanıcı giriş sayfasını gösterir ve giriş işlemini (oturum açma) yönetir.
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if current_user.is_authenticated: return redirect(url_for('home'))

    active_tab = request.args.get('tab', 'login')

    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter(or_(
            User.username == username_or_email,
            User.email == username_or_email
        )).first()

        if user and bcrypt.check_password_hash(user.password, password):
            remember = True if request.form.get('remember') else False
            login_user(user, remember=remember)
            return redirect(url_for('home'))

        flash("Hatalı kullanıcı adı veya şifre.", "error")
        return redirect(url_for('login_page', tab='login'))

    return render_template('login.html', active_tab=active_tab)

# Yeni kullanıcı kaydı oluşturur, kullanıcı adı/e-posta kontrolü yapar.
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('reg_username')
    email = request.form.get('reg_email')
    password = request.form.get('reg_password')

    user_exists = User.query.filter_by(username=username).first()
    email_exists = User.query.filter_by(email=email).first()

    error_message = None

    if user_exists and email_exists:
        error_message = "Kullanıcı adı ve E-posta zaten kullanımda."
    elif user_exists:
        error_message = "Kullanıcı adı zaten kullanımda."
    elif email_exists:
        error_message = "E-posta zaten kullanımda."

    if error_message:
        flash(error_message, "error")
        return redirect(url_for('login_page', tab='register'))

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.add(User(username=username, email=email, password=hashed))
    db.session.commit()
    login_user(User.query.filter_by(username=username).first())
    return redirect(url_for('home'))

# Kullanıcı profil sayfasını, üyelik süresini ve izleme listesi özetini gösterir.
@app.route('/account')
@login_required
def account():
    user = current_user
    registration_date = user.created_at
    delta = datetime.now() - registration_date
    days_active = delta.days

    raw_watchlist = user.watchlist[::-1]

    watchlist_display = []
    hidden_items = get_hidden_items_set()

    for item in raw_watchlist:
        if not item.poster_path: continue

        if (item.media_id, item.media_type) in hidden_items:
            continue

        watchlist_display.append({
            'id': item.media_id,
            'media_type': item.media_type,
            'title': item.title,
            'poster_url': get_tmdb_image(item.poster_path),
            'rating': item.rating,
            'release_year': item.release_date[:4] if item.release_date else 'Bilinmiyor'
        })

    return render_template('user-account.html',
                            user=user,
                            days_active=days_active,
                            watchlist_count=len(watchlist_display),
                            watchlist_movies=watchlist_display)

# Kullanıcının kendi hesabını ve tüm verilerini silmesini sağlar.
@app.route('/delete_account')
@login_required
def delete_account():

    if current_user.id == 1:
        flash('Birincil Admin hesabı güvenlik nedeniyle silinemez.', 'error')
        return redirect(url_for('account'))

    try:
        Watchlist.query.filter_by(user_id=current_user.id).delete()
        user_to_delete = db.session.get(User, current_user.id)
        db.session.delete(user_to_delete)
        db.session.commit()
        logout_user()
        flash('Hesabınız ve tüm verileriniz başarıyla silindi.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('account'))

# Kullanıcının oturumunu güvenli bir şekilde kapatır.
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Arama çubuğu için canlı film/dizi önerileri sunar.
@app.route('/suggest')
def suggest_movies():
    query = request.args.get('q')
    if not query or len(query) < 2: return jsonify([])

    data = make_tmdb_request('/search/multi', {'query': query})
    suggestions = []

    if data:
        for m in data.get('results', [])[:5]:
            if not m.get('poster_path'): continue

            if m.get('media_type') == 'person': continue

            media_type = m.get('media_type', 'movie')
            poster_path = m.get('poster_path')
            orig_lang = m.get('original_language')

            if orig_lang not in ['tr', 'en']:
                try:
                    img_params = {'include_image_language': 'tr,en,null', 'language': 'en-US'}
                    images_data = make_tmdb_request(f"/{media_type}/{m['id']}/images", img_params)

                    if images_data and images_data.get('posters'):
                        poster_path = images_data['posters'][0]['file_path']
                except Exception:
                    pass

            title = m.get('title') if media_type == 'movie' else m.get('name')
            date_val = m.get('release_date') if media_type == 'movie' else m.get('first_air_date')

            suggestions.append({
                'id': m['id'],
                'media_type': media_type,
                'title': title,
                'year': (date_val or '')[:4],
                'poster': get_tmdb_image(poster_path, 'w92')
            })
    return jsonify(suggestions)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        user = User.query.filter_by(username='upur').first()

        if user:
            user.is_admin = True
            db.session.commit()
            print(">>> Başarılı: 'upur' artık admin.")
        else:
            print(">>> Hata: 'upur' adında bir kullanıcı bulunamadı.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
