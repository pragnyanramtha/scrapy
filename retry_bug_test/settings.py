# retry_bug_test/settings.py

# ... existing settings ...

# Configure your custom RetryMiddleware
DOWNLOADER_MIDDLEWARES = {
    'retry_bug_test.custom_middlewares.RetryMiddleware': 500,
    # Set the original Scrapy RetryMiddleware to None to disable it,
    # so only your custom one runs.
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
    # Ensure other necessary middlewares are enabled if your project needs them
    # e.g., 'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
    # 'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500,
    # etc.
}

# Ensure these are set for the scenario
RETRY_ENABLED = True
RETRY_TIMES = 1 # We only need one retry for this test
RETRY_HTTP_CODES = [503] # Flask server will return this code

# Crucial for seeing the DupeFilter's action
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'

# Set logging level to DEBUG for detailed output
LOG_LEVEL = 'DEBUG'

# ... rest of your settings ...