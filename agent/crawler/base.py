import asyncio
import json
import os
import re

from crawl4ai import AsyncWebCrawler

from agent.crawler.config import Crawl4AIConfig
from agent.crawler.sitemeta import RobotsHandler, SitemapCrawler
from agent.crawler.url_manager import URLUtils


def _slug_for(url):
    path = re.sub(r"^https?://", "", url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
    return slug[:120] or "index"


class WebCrawler:
    def __init__(self, base_url, output_dir="./data", max_concurrency=3, crawl4ai_config=None):
        self.base_url = base_url
        self.domain = URLUtils.get_domain(base_url)
        self.output_dir = output_dir
        self.max_concurrency = max_concurrency
        self.crawl4ai_config = crawl4ai_config or Crawl4AIConfig()
        self.robots = RobotsHandler(base_url)

        self._active = 0
        self._max_active_seen = 0
        self.skipped = []  # (url, reason) pairs, for visibility/verification

    def _is_crawlable(self, url):
        if not URLUtils.is_content_url(url):
            self.skipped.append((url, "non-content extension"))
            return False
        if not self.robots.is_allowed(url):
            self.skipped.append((url, "disallowed by robots.txt"))
            return False
        return True

    async def get_website_urls(self, max_pages=10):
        """BFS-crawl the site for internal links, bounded to max_pages."""
        start = URLUtils.normalize_url(self.base_url)
        seen = {start}
        queue = [start]
        discovered = []

        async with AsyncWebCrawler(config=self.crawl4ai_config.get_browser_config()) as crawler:
            while queue and len(discovered) < max_pages:
                url = queue.pop(0)
                if not self._is_crawlable(url):
                    continue

                result = await crawler.arun(url=url, config=self.crawl4ai_config.get_run_config())
                if not result.success:
                    self.skipped.append((url, f"fetch failed: {result.error_message}"))
                    continue

                discovered.append(url)

                for link in result.links.get("internal", []):
                    href = link.get("href")
                    if not href:
                        continue
                    normalized = URLUtils.normalize_url(href, base_url=url)
                    if normalized in seen:
                        continue
                    if URLUtils.get_domain(normalized) != self.domain:
                        continue
                    seen.add(normalized)
                    queue.append(normalized)

        return discovered

    async def crawl_parallel(self, urls):
        """Crawl a list of URLs concurrently, bounded by a semaphore for politeness."""
        semaphore = asyncio.Semaphore(self.max_concurrency)
        results = []

        async with AsyncWebCrawler(config=self.crawl4ai_config.get_browser_config()) as crawler:
            async def _crawl_one(url):
                async with semaphore:
                    self._active += 1
                    self._max_active_seen = max(self._max_active_seen, self._active)
                    print(f"[WebCrawler] in-flight={self._active} (limit={self.max_concurrency}) -- {url}")
                    try:
                        return url, await crawler.arun(url=url, config=self.crawl4ai_config.get_run_config())
                    finally:
                        self._active -= 1

            results = await asyncio.gather(*(_crawl_one(url) for url in urls))

        return list(results)

    def _write_markdown(self, url, markdown_text):
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, f"{_slug_for(url)}.md")
        with open(path, "w") as f:
            f.write(markdown_text)
        return path

    def _write_manifest(self, records):
        os.makedirs(self.output_dir, exist_ok=True)
        # Dot-prefixed: SimpleDirectoryReader's default exclude_hidden=True
        # keeps this out of the document corpus DocumentHandler reads --
        # otherwise the manifest itself would get indexed as "content".
        path = os.path.join(self.output_dir, ".crawl_manifest.jsonl")
        with open(path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        return path

    def _discover_urls_from_sitemap(self, max_pages):
        sitemap_crawler = SitemapCrawler()
        sitemap_urls = self.robots.get_sitemap_urls() or [
            URLUtils.normalize_url("/sitemap.xml", base_url=self.base_url)
        ]

        discovered = []
        for sitemap_url in sitemap_urls:
            try:
                found = sitemap_crawler.get_urls(sitemap_url)
            except Exception as e:
                self.skipped.append((sitemap_url, f"sitemap fetch/parse failed: {e}"))
                continue

            for raw_url in found:
                normalized = URLUtils.normalize_url(raw_url)
                if URLUtils.get_domain(normalized) != self.domain:
                    continue
                if normalized in discovered:
                    continue
                if self._is_crawlable(normalized):
                    discovered.append(normalized)
                if len(discovered) >= max_pages:
                    return discovered

        return discovered

    async def _crawl_and_write(self, urls):
        crawled = await self.crawl_parallel(urls)

        manifest = []
        for url, result in crawled:
            if not result.success:
                manifest.append({"url": url, "success": False, "error": result.error_message})
                continue
            markdown_text = result.markdown.fit_markdown or result.markdown.raw_markdown
            path = self._write_markdown(url, markdown_text)
            manifest.append({"url": url, "success": True, "path": path})

        manifest_path = self._write_manifest(manifest)

        return {
            "urls_attempted": urls,
            "pages_written": sum(1 for m in manifest if m["success"]),
            "manifest_path": manifest_path,
            "max_concurrency_configured": self.max_concurrency,
            "max_concurrency_observed": self._max_active_seen,
            "skipped": list(self.skipped),
        }

    async def crawl_urls(self, urls):
        """Crawl exactly the given URLs -- no sitemap/BFS discovery. For
        targeted single-page (or small, explicit list) ingestion, where
        pulling in a site's wider sitemap would be wrong (too broad, or
        simply the wrong pages) rather than just 'not what was asked'."""
        filtered = [u for u in urls if self._is_crawlable(u)]
        return await self._crawl_and_write(filtered)

    async def get_data(self, max_pages=10):
        """Full pipeline: prefer sitemap-derived URLs, fall back to a BFS crawl
        if no sitemap is available; crawl the result set concurrently; write
        markdown + a JSONL manifest to output_dir."""
        urls = self._discover_urls_from_sitemap(max_pages)

        if not urls:
            urls = await self.get_website_urls(max_pages=max_pages)

        urls = urls[:max_pages]

        return await self._crawl_and_write(urls)
