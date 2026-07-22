from crawl4ai import (
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
    PruningContentFilter,
)


class Crawl4AIConfig:
    def __init__(self, headless=True, prune_threshold=0.6, cache_mode=CacheMode.BYPASS):
        self.browser_config = BrowserConfig(headless=headless, verbose=False)

        # PruningContentFilter strips boilerplate (nav/footer/sidebar noise)
        # from the extracted markdown before it's written to disk.
        #
        # Tuned against a real leak: developers.facebook.com's nav renders as
        # plain <div>s, not semantic <nav>/<header> (which excluded_tags does
        # catch) -- it was surviving whole at the original threshold=0.48.
        # Verified via inspect.getsource on PruningContentFilter:
        #   - threshold=0.6 (up from 0.48): the existing density/tag-weight
        #     composite score is the main lever; 0.48 was letting a full nav
        #     block (several short menu labels + a login link) through.
        #   - min_word_threshold=2: guarantees removal (score=-1.0) for any
        #     remaining single-word leftover node the density score alone
        #     didn't catch (e.g. a lone "SupportSupportSupport" span).
        #   - preserve_tags=headings only, deliberately NOT "a": tried
        #     protecting all <a> tags too, which brought back the nav's own
        #     login link (also an <a>) -- so links are left subject to the
        #     same word-count floor as everything else. Real inline links
        #     inside surviving paragraphs mostly clear min_word_threshold=2
        #     on their own (e.g. "rate limit", "App Review", "development
        #     mode"); the one casualty found in testing is single-word link
        #     text ("Permissions" -> "See below" loses the link but the
        #     sentence stays readable) -- an accepted, minor tradeoff versus
        #     leaving nav junk in, verified by direct before/after diffing,
        #     not assumed.
        content_filter = PruningContentFilter(
            threshold=prune_threshold,
            threshold_type="fixed",
            min_word_threshold=2,
            preserve_tags=["h1", "h2", "h3", "h4", "h5", "h6"],
        )
        markdown_generator = DefaultMarkdownGenerator(content_filter=content_filter)

        self.run_config = CrawlerRunConfig(
            markdown_generator=markdown_generator,
            cache_mode=cache_mode,
        )

    def get_browser_config(self):
        return self.browser_config

    def get_run_config(self):
        return self.run_config
