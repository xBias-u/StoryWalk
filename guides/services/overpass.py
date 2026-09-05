import json
import math
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class OverpassError(RuntimeError):
    """Raised when nearby place discovery cannot be completed safely."""


@dataclass(frozen=True)
class DiscoveredPlace:
    name: str
    latitude: float
    longitude: float
    category: str
    distance_m: int
    story_score: int
    source_id: str
    source_url: str
    tags: dict


class OverpassClient:
    DEFAULT_URL = 'https://overpass-api.de/api/interpreter'
    TRANSIENT_HTTP_CODES = {429, 502, 503, 504}

    def __init__(self, api_url=None, timeout=35):
        self.api_urls = [api_url] if api_url else getattr(
            settings,
            'OVERPASS_API_URLS',
            [self.DEFAULT_URL],
        )
        self.timeout = timeout

    def discover(self, latitude, longitude, radius_m=1200, limit=20):
        if not 100 <= radius_m <= 5000:
            raise OverpassError('Radius must be between 100 and 5,000 metres')
        if not 1 <= limit <= 50:
            raise OverpassError('Limit must be between 1 and 50')

        query = self._build_query(latitude, longitude, radius_m)
        payload = self._request(query)

        places = []
        for element in payload.get('elements', []):
            place = self._to_place(element, latitude, longitude)
            if place and place.distance_m <= radius_m:
                places.append(place)

        deduplicated = {}
        for place in places:
            key = place.name.casefold().replace('ё', 'е')
            current = deduplicated.get(key)
            if current is None or (place.story_score, -place.distance_m) > (
                current.story_score,
                -current.distance_m,
            ):
                deduplicated[key] = place

        return sorted(
            deduplicated.values(),
            key=lambda item: (-item.story_score, item.distance_m, item.name),
        )[:limit]

    def _request(self, query):
        last_error = None
        for api_url in self.api_urls:
            request = Request(
                api_url,
                data=urlencode({'data': query}).encode('utf-8'),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                    'User-Agent': 'StoryWalk-development/0.1',
                },
                method='POST',
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.load(response)
            except HTTPError as exc:
                details = exc.read().decode('utf-8', errors='replace')[:200]
                last_error = f'{api_url} returned HTTP {exc.code}: {details}'
                if exc.code in self.TRANSIENT_HTTP_CODES:
                    continue
                raise OverpassError(last_error) from exc
            except (URLError, TimeoutError) as exc:
                last_error = f'{api_url} is unavailable: {getattr(exc, "reason", exc)}'
                continue
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                last_error = f'{api_url} returned an invalid response'
                continue

        raise OverpassError(last_error or 'No Overpass API endpoints are configured')

    @staticmethod
    def _build_query(latitude, longitude, radius_m):
        latitude = float(latitude)
        longitude = float(longitude)
        latitude_delta = radius_m / 111_320
        longitude_delta = radius_m / (111_320 * max(math.cos(math.radians(latitude)), 0.2))
        bbox = (
            f'({latitude - latitude_delta:.6f},{longitude - longitude_delta:.6f},'
            f'{latitude + latitude_delta:.6f},{longitude + longitude_delta:.6f})'
        )
        return f'''[out:json][timeout:30];
(
  nw["name"]["historic"]{bbox};
  nw["name"]["tourism"~"^(museum|artwork)$"]{bbox};
  nw["name"]["heritage"]["wikipedia"]{bbox};
  nw["name"]["amenity"="place_of_worship"]["start_date"]{bbox};
);
out center tags 200;'''

    def _to_place(self, element, origin_latitude, origin_longitude):
        tags = element.get('tags') or {}
        name = (tags.get('name:ru') or tags.get('name') or '').strip()
        if not name:
            return None

        latitude = element.get('lat')
        longitude = element.get('lon')
        if latitude is None or longitude is None:
            center = element.get('center') or {}
            latitude = center.get('lat')
            longitude = center.get('lon')
        if latitude is None or longitude is None:
            return None

        element_type = element.get('type')
        element_id = element.get('id')
        if element_type not in {'node', 'way', 'relation'} or element_id is None:
            return None

        category = self._category(tags)
        score = self._story_score(tags, category)
        distance = round(self._distance_m(origin_latitude, origin_longitude, latitude, longitude))
        source_id = f'{element_type}/{element_id}'
        return DiscoveredPlace(
            name=name,
            latitude=float(latitude),
            longitude=float(longitude),
            category=category,
            distance_m=distance,
            story_score=score,
            source_id=source_id,
            source_url=f'https://www.openstreetmap.org/{source_id}',
            tags=tags,
        )

    @staticmethod
    def _category(tags):
        if tags.get('tourism') == 'museum':
            return 'museum'
        if tags.get('historic') == 'memorial':
            return 'memorial'
        if tags.get('tourism') == 'artwork':
            return 'artwork'
        if tags.get('amenity') == 'place_of_worship':
            return 'religious'
        if tags.get('historic') in {'building', 'manor', 'castle', 'palace'} or tags.get('architect'):
            return 'architecture'
        if tags.get('historic') or tags.get('heritage'):
            return 'historic'
        return 'other'

    @staticmethod
    def _story_score(tags, category):
        score = 1
        score += {
            'museum': 5,
            'historic': 4,
            'architecture': 4,
            'religious': 3,
            'memorial': 2,
            'artwork': 2,
            'other': 0,
        }[category]
        score += 3 if tags.get('heritage') else 0
        score += 2 if tags.get('wikipedia') else 0
        score += 2 if tags.get('wikidata') else 0
        score += 2 if tags.get('start_date') else 0
        score += 2 if tags.get('architect') else 0
        score += 1 if tags.get('description') or tags.get('description:ru') else 0
        if tags.get('memorial') == 'plaque':
            score = max(1, score - 2)
        return min(score, 20)

    @staticmethod
    def _distance_m(lat1, lon1, lat2, lon2):
        radius = 6_371_000
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        delta_phi = math.radians(float(lat2) - float(lat1))
        delta_lambda = math.radians(float(lon2) - float(lon1))
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
