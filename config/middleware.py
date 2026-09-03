from urllib.parse import urlparse

from django.conf import settings
from whitenoise.middleware import WhiteNoiseMiddleware


class DemoMediaWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """Serve explicitly public media for the small, filesystem-backed demo.

    This mode supports byte-range requests used by the audio player. Persistent
    user uploads still require object storage in a production product.
    """

    def __init__(self, get_response=None, settings=settings):
        super().__init__(get_response=get_response, settings=settings)
        if settings.SERVE_MEDIA_FILES:
            prefix = urlparse(settings.MEDIA_URL).path
            self.add_files(settings.MEDIA_ROOT, prefix=prefix)
