import re
from datetime import datetime
import requests
from unidecode import unidecode
from extensions import cache
from config import TMDB_API_KEY, TMDB_BASE_URL, ALLOWED_EXTENSIONS

tmdb_session = requests.Session()

# TMDB görsel yolunu tam URL'ye dönüştürür, yoksa yer tutucu görsel getirir.
def get_tmdb_image(path, size='w500'):
    if not path:
        return f"https://via.placeholder.com/{'500x750' if size == 'w500' else '1280x720'}?text=Resim+Yok"
    return f"https://image.tmdb.org/t/p/{size}{path}"

# TMDB API'sine belirtilen uç noktaya bir istek yapar.
def make_tmdb_request(endpoint, params=None):
    if not TMDB_API_KEY:
        print("TMDB API key is missing; request skipped.")
        return None
    url = f"{TMDB_BASE_URL}{endpoint}"
    default_params = {'api_key': TMDB_API_KEY, 'language': 'tr-TR'}
    if params:
        default_params.update(params)
    try:
        resp = tmdb_session.get(url, params=default_params, timeout=3)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"API Hatasi ({endpoint}): {e}")
        return None

# Belirtilen medya (film/dizi) için YouTube fragman anahtarını döndürür.
@cache.memoize(timeout=3600)
def get_trailer_key_cached(media_type, media_id):
    data = make_tmdb_request(f"/{media_type}/{media_id}/videos")
    if data:
        for video in data.get('results', []):
            if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                return video['key']
    return None

# Film ve TV dizileri için birleştirilmiş tür ID'si-adı haritasını döndürür.
@cache.cached(timeout=86400, key_prefix='all_genres_map_combined')
def get_genre_map():
    combined_genres = {}
    try:
        data_movie = make_tmdb_request('/genre/movie/list', {'language': 'tr-TR'})
        if data_movie and 'genres' in data_movie:
            for g in data_movie['genres']:
                combined_genres[g['id']] = g['name']
        data_tv = make_tmdb_request('/genre/tv/list', {'language': 'tr-TR'})
        if data_tv and 'genres' in data_tv:
            for g in data_tv['genres']:
                combined_genres[g['id']] = g['name']
    except Exception as e:
        print(f"Tur listesi alinamadi: {e}")
    return combined_genres

# Medya listesindeki öğelerin kullanıcının izleme listesinde olup olmadığını kontrol edip ekler.
def inject_watchlist_status(media_list, user):
    if not media_list:
        return []
    processed_list = [m.copy() for m in media_list]
    if user.is_authenticated:
        from models import Watchlist
        user_watchlist = {(item.media_id, item.media_type) for item in Watchlist.query.filter_by(user_id=user.id).all()}
        for item in processed_list:
            item['in_watchlist'] = (item['id'], item.get('media_type', 'movie')) in user_watchlist
    else:
        for item in processed_list:
            item['in_watchlist'] = False
    return processed_list

# Metni Latin alfabesine dönüştürür (Türkçe karakterleri de koruyan bir kontrol sonrası 'unidecode' kullanır).
def force_latin(text):
    if not text:
        return ""
    if re.match(r"^[a-zA-Z0-9\s\.,\-\'\"\:\!\?\(\)\&çÇğĞıİöÖşŞüÜ]+$", text):
        return text
    return unidecode(text)

# Ham TMDB öğe verilerini uygulamanın kullandığı standart bir formata dönüştürür.
def process_media_data(item, specific_type=None):
    if not item or not item.get('id'):
        return None
    media_type = item.get('media_type', specific_type)
    if not media_type:
        media_type = 'movie'
    if media_type == 'person':
        return None
    title = item.get('title') if media_type == 'movie' else item.get('name')
    original_title = item.get('original_title') if media_type == 'movie' else item.get('original_name')
    date_field = item.get('release_date') if media_type == 'movie' else item.get('first_air_date')
    overview = item.get('overview')
    orig_lang = item.get('original_language')
    poster_path = item.get('poster_path')
    is_title_latin = True
    if title and not re.match(r"^[a-zA-Z0-9\s\.,\-\'\"\:\!\?\(\)\&çÇğĞıİöÖşŞüÜ]+$", title):
        is_title_latin = False
    if not title or not overview or not is_title_latin:
        try:
            eng_data = make_tmdb_request(f"/{media_type}/{item['id']}", {'language': 'en-US'})
            if eng_data:
                if not overview and eng_data.get('overview'):
                    overview = eng_data['overview']
                eng_title = eng_data.get('title') if media_type == 'movie' else eng_data.get('name')
                if (not title or not is_title_latin) and eng_title:
                    title = eng_title
        except Exception:
            pass
    current_genre_map = get_genre_map()
    genre_names = []
    if 'genres' in item:
        genre_names = [g['name'] for g in item['genres']]
    elif 'genre_ids' in item:
        genre_names = [current_genre_map.get(gid) for gid in item['genre_ids'] if gid in current_genre_map]
    genres_str = ", ".join(genre_names[:2]) if genre_names else ""
    if not poster_path or orig_lang not in ['tr', 'en']:
        try:
            img_params = {'include_image_language': 'en,null', 'language': 'en-US'}
            images_data = make_tmdb_request(f"/{media_type}/{item['id']}/images", img_params)
            if images_data and images_data.get('posters'):
                poster_path = images_data['posters'][0]['file_path']
        except Exception:
            pass
    if not poster_path:
        return None
    return {
        "id": item.get('id'),
        "media_type": media_type,
        "title": title or force_latin(original_title),
        "overview": overview,
        "poster": get_tmdb_image(poster_path, 'w500'),
        "backdrop": get_tmdb_image(item.get('backdrop_path'), 'w1280'),
        "rating": round(item.get('vote_average', 0), 1),
        "release_date": (date_field or '')[:4],
        "genres": genres_str,
        "trailer_key": None
    }

# 'YYYY-MM-DD' formatındaki bir tarih dizesini Türkçe 'GG.AA.YYYY' formatına dönüştürür.
def format_date_tr(date_str):
    if not date_str:
        return "Bilinmiyor"
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%d.%m.%Y')
    except Exception:
        return date_str

# Veritabanındaki tüm gizlenmiş içeriklerin kümesini döndürür.
@cache.memoize(timeout=600)
def get_hidden_items_set():
    from models import HiddenContent
    return {(h.tmdb_id, h.media_type) for h in HiddenContent.query.all()}

# Verilen medya listesini, gizlenmiş içerikler kümesini kullanarak filtreler.
def filter_hidden_content(media_list):
    if not media_list:
        return []
    hidden_items = get_hidden_items_set()
    filtered_list = []
    for m in media_list:
        try:
            tmdb_id = int(m.get('id'))
            media_type = m.get('media_type', 'movie')
        except (TypeError, ValueError):
            continue
        if (tmdb_id, media_type) not in hidden_items:
            filtered_list.append(m)
    return filtered_list

# Bir aktör detay sorgusu için özel bir önbellek anahtarı oluşturur.
def make_actor_cache_key(*args, **kwargs):
    actor_id = kwargs.get('actor_id')
    return f'actor_detail_{actor_id}'

# Dosya adının uzantısının izin verilen uzantılar listesinde olup olmadığını kontrol eder.
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

