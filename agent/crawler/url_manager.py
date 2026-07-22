from urllib.parse import urldefrag, urljoin, urlencode, urlparse, parse_qsl

# Normalization rule (documented, applied consistently):
#   1. Relative URLs are resolved against a base URL.
#   2. Scheme and host are lowercased (paths are left case-sensitive --
#      many servers treat /Foo and /foo as different resources).
#   3. The fragment (#...) is dropped -- it's client-side only and never
#      distinguishes server-rendered content.
#   4. A trailing slash on a non-root path is dropped (/foo/ -> /foo), so
#      the same page isn't crawled twice under two spellings. The root
#      path "/" is left alone.
#   5. The query string is kept (some sites route real content through
#      query params), but its parameters are sorted so equivalent queries
#      in a different order normalize to the same URL.

NON_CONTENT_EXTENSIONS = {
    # images
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff",
    # documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
    # archives
    ".zip", ".tar", ".gz", ".rar", ".7z",
    # media
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".webm",
    # static assets
    ".css", ".js", ".json", ".xml", ".woff", ".woff2", ".ttf", ".eot",
    # executables/installers
    ".exe", ".dmg", ".apk",
}


class URLUtils:
    @staticmethod
    def get_domain(url):
        return urlparse(url).netloc.lower()

    @staticmethod
    def normalize_url(url, base_url=None):
        if base_url:
            url = urljoin(base_url, url)

        url, _fragment = urldefrag(url)

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        path = parsed.path or "/"
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        query = urlencode(sorted(parse_qsl(parsed.query)))

        return parsed._replace(scheme=scheme, netloc=netloc, path=path, query=query).geturl()

    @staticmethod
    def is_content_url(url):
        path = urlparse(url).path.lower()
        for ext in NON_CONTENT_EXTENSIONS:
            if path.endswith(ext):
                return False
        return True
