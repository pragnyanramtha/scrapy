# crawler.py
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
import scrapy
class TestSpider(scrapy.Spider):
    name = 'test_spider'
    start_urls = ['http://localhost:8000/sbn/'] # This initiates the chain

    # Use a class-level list to collect processed URLs for easier verification
    processed_urls = []

    def parse(self, response):
        self.logger.info(f"Spider: Parsed {response.url} (from parse method)")
        self.processed_urls.append(response.url)

        # This is the crucial check:
        if response.url == 'http://localhost:8000/sbn':
            self.logger.info(f"Spider: Processing final target URL {response.url}. Request.dont_filter IS: {response.request.dont_filter}")
            if response.request.dont_filter:
                self.logger.error(f"BUG: {response.url} still had dont_filter=True! The fix is NOT working for this case.")
            else:
                self.logger.info(f"FIXED: {response.url} correctly has dont_filter=False.")

        # No further requests needed from here for this specific test case,
        # as the server takes care of the redirect chain.






def main():
    custom_settings = Settings()
    custom_settings.set('DOWNLOADER_MIDDLEWARES', {
        'retry_bug_test.custom_middlewares.RetryMiddleware': 500,
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': None, # Disable default
        'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
        'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500, # Example of other default you might need
        'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700, # Example
        # Add any other essential default middlewares you want to keep
        # Check Scrapy's default_settings.py for common ones if you encounter issues
    })

    custom_settings.set('RETRY_ENABLED', True)
    custom_settings.set('RETRY_TIMES', 1)
    custom_settings.set('RETRY_HTTP_CODES', [503])
    custom_settings.set('DUPEFILTER_CLASS', 'scrapy.dupefilters.RFPDupeFilter')
    custom_settings.set('LOG_LEVEL', 'DEBUG')

    
    # Initialize CrawlerProcess with your custom settings
    process = CrawlerProcess(settings=custom_settings) # This is the CORRECTED line
    process.crawl(TestSpider)
    process.start()

if __name__ == '__main__':
    main()