import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class ValhallaError(RuntimeError):
    """Raised when a pedestrian route cannot be calculated or validated."""


@dataclass(frozen=True)
class RouteLeg:
    distance_m: int
    duration_seconds: int
    coordinates: list


@dataclass(frozen=True)
class PedestrianRoute:
    distance_m: int
    duration_seconds: int
    legs: list

    @property
    def geojson(self):
        return {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {'position': position},
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': leg.coordinates,
                    },
                }
                for position, leg in enumerate(self.legs, start=1)
            ],
        }


class ValhallaClient:
    def __init__(self, api_url=None, timeout=30):
        self.api_url = api_url or settings.VALHALLA_API_URL
        self.timeout = timeout

    def route(self, locations):
        if len(locations) < 2:
            raise ValhallaError('A pedestrian route needs at least two locations')

        payload = {
            'locations': [
                {
                    'lat': round(float(location['latitude']), 6),
                    'lon': round(float(location['longitude']), 6),
                    'type': 'break',
                }
                for location in locations
            ],
            'costing': 'pedestrian',
            'units': 'kilometers',
            'shape_format': 'polyline6',
            'directions_options': {
                'language': 'ru-RU',
                'units': 'kilometers',
            },
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'StoryWalk-development/0.1',
            },
            method='POST',
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_payload = json.load(response)
        except HTTPError as exc:
            details = exc.read().decode('utf-8', errors='replace')[:300]
            raise ValhallaError(
                f'Valhalla returned HTTP {exc.code}: {details}'
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise ValhallaError(
                f'Valhalla is unavailable: {getattr(exc, "reason", exc)}'
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValhallaError('Valhalla returned an invalid response') from exc

        return self._parse_route(response_payload, expected_legs=len(locations) - 1)

    @classmethod
    def _parse_route(cls, payload, expected_legs):
        trip = payload.get('trip') or {}
        raw_legs = trip.get('legs') or []
        if len(raw_legs) != expected_legs:
            raise ValhallaError(
                f'Valhalla returned {len(raw_legs)} legs instead of {expected_legs}'
            )

        legs = []
        for raw_leg in raw_legs:
            summary = raw_leg.get('summary') or {}
            shape = raw_leg.get('shape')
            if summary.get('length') is None or summary.get('time') is None or not shape:
                raise ValhallaError('Valhalla returned an incomplete route leg')
            coordinates = cls.decode_polyline6(shape)
            if len(coordinates) < 2:
                raise ValhallaError('Valhalla returned an empty route shape')
            legs.append(RouteLeg(
                distance_m=round(float(summary['length']) * 1000),
                duration_seconds=round(float(summary['time'])),
                coordinates=coordinates,
            ))

        return PedestrianRoute(
            distance_m=sum(leg.distance_m for leg in legs),
            duration_seconds=sum(leg.duration_seconds for leg in legs),
            legs=legs,
        )

    @staticmethod
    def decode_polyline6(shape):
        coordinates = []
        index = latitude = longitude = 0
        while index < len(shape):
            deltas = []
            for _ in range(2):
                result = shift = 0
                while True:
                    if index >= len(shape):
                        raise ValhallaError('Valhalla returned a malformed route shape')
                    value = ord(shape[index]) - 63
                    index += 1
                    result |= (value & 0x1F) << shift
                    shift += 5
                    if value < 0x20:
                        break
                deltas.append(~(result >> 1) if result & 1 else result >> 1)
            latitude += deltas[0]
            longitude += deltas[1]
            coordinates.append([longitude / 1_000_000, latitude / 1_000_000])
        return coordinates
