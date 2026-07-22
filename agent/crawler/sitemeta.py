from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import requests

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class RobotsHandler:
    def __init__(self, base_url, user_agent="*", timeout=10):
        self.base_url = base_url
        self.user_agent = user_agent
        self.robots_url = urljoin(base_url, "/robots.txt")

        self.parser = RobotFileParser()
        self.parser.set_url(self.robots_url)

        # Fetch via requests (uses certifi's CA bundle) rather than
        # RobotFileParser.read()'s own urllib.request call, which relies on
        # the system CA store and fails on machines where that's misconfigured.
        try:
            response = requests.get(self.robots_url, timeout=timeout)
            response.raise_for_status()
            self.parser.parse(response.text.splitlines())
        except requests.RequestException:
            # No robots.txt / unreachable -- RobotFileParser treats an empty
            # ruleset as "everything allowed", which is the correct default.
            self.parser.parse([])

    def is_allowed(self, url):
        return self.parser.can_fetch(self.user_agent, url)

    def get_sitemap_urls(self):
        return list(self.parser.site_maps() or [])


class SitemapCrawler:
    def __init__(self, timeout=10):
        self.timeout = timeout

    def get_urls(self, sitemap_url):
        urls = []
        self._collect(sitemap_url, urls, seen=set())
        return urls

    def _collect(self, sitemap_url, urls, seen):
        if sitemap_url in seen:
            return
        seen.add(sitemap_url)

        response = requests.get(sitemap_url, timeout=self.timeout)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)

        tag = root.tag
        if tag == f"{_SITEMAP_NS}sitemapindex":
            for sitemap_el in root.findall(f"{_SITEMAP_NS}sitemap"):
                loc_el = sitemap_el.find(f"{_SITEMAP_NS}loc")
                if loc_el is not None and loc_el.text:
                    self._collect(loc_el.text.strip(), urls, seen)
        elif tag == f"{_SITEMAP_NS}urlset":
            for url_el in root.findall(f"{_SITEMAP_NS}url"):
                loc_el = url_el.find(f"{_SITEMAP_NS}loc")
                if loc_el is not None and loc_el.text:
                    urls.append(loc_el.text.strip())
