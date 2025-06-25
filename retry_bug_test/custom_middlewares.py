# retry_bug_test/custom_middlewares.py

import logging
from twisted.internet import defer
from twisted.internet.error import (
    TimeoutError,
    DNSLookupError,
    ConnectionRefusedError,
    ConnectionDone,
    ConnectError,
    ConnectionLost,
    TCPTimedOutError
)
from scrapy.utils.request import referer_str
from scrapy.utils.python import global_object_name
from weakref import WeakKeyDictionary

logger = logging.getLogger(__name__)

# This function must be defined *before* the RetryMiddleware class if it's called within it.
def get_retry_request(request, spider, reason="unspecified", max_retry_times=None):
    """
    Returns a new Request object to retry the given request, or None if retries
    have been exhausted.
    """
    settings = spider.settings
    retries = request.meta.get('retry_times', 0) + 1
    if max_retry_times is None:
        max_retry_times = settings.getint('RETRY_TIMES')

    logger.debug(
        "[MyRetryMiddleware:get_retry_request] Original request dont_filter: %s, URL: %s",
        request.dont_filter, request.url
    )

    if retries <= max_retry_times:
        retry_req = request.copy()
        retry_req.meta['retry_times'] = retries
        
        # --- CRITICAL CHANGE FOR THE DONT_FILTER BUG ---
        # When retrying, we *always* want the new retry request to be filterable
        # UNLESS the spider explicitly requested dont_filter for THIS specific request.
        # The default behavior of Request.copy() carries over dont_filter.
        # So we explicitly set it to False.
        # The exception would be if you have custom logic in your spider that sets dont_filter=True
        # for a specific retry. For this bug, we assume that's not the case here.
        retry_req.dont_filter = False # <-- THIS IS THE PRIMARY FIX LOCATION
        logger.debug(
            "[MyRetryMiddleware:get_retry_request] Created retry_req for %s. NEW dont_filter: %s",
            retry_req.url, retry_req.dont_filter
        )
        # --- END CRITICAL CHANGE ---

        if referer_str(request):
            retry_req.headers['Referer'] = referer_str(request)

        return retry_req
    else:
        logger.error(
            "Gave up retrying %(request)s (failed %(retry_times)d times): %(reason)s",
            {"request": request, "retry_times": max_retry_times, "reason": reason},
            extra={"spider": spider},
        )
        return None

class RetryMiddleware:
    def __init__(self, settings):
        self.max_retry_times = settings.getint("RETRY_TIMES")
        self.stats = None # Will be set by Scrapy via from_crawler
        self.priority_adjust = settings.getint("RETRY_PRIORITY_ADJUST")
        self.retry_http_codes = settings.getlist("RETRY_HTTP_CODES")

        self.exceptions_to_retry = (
            defer.TimeoutError,
            TimeoutError,
            DNSLookupError,
            ConnectionRefusedError,
            ConnectionDone,
            ConnectError,
            ConnectionLost,
            TCPTimedOutError,
            IOError
        )
        self.logger = logger # Use the module-level logger

        # This dictionary will store requests that were initially
        # `dont_filter=True` AND were subsequently retried by this middleware.
        # The key is the original request, value can be anything (e.g., True).
        self._requests_dont_filter_bug_tracker = WeakKeyDictionary()

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.settings)
        o.stats = crawler.stats
        return o

    def process_response(self, request, response, spider):
        self.logger.debug(
            "[MyRetryMiddleware] Entering process_response for %s. Current dont_filter: %s",
            request.url, request.dont_filter
        )

        if request.meta.get('dont_retry', False):
            self.logger.debug("[MyRetryMiddleware] dont_retry meta key is True. Not retrying %s.", request.url)
            return response

        # Check if the request came from a retry that *we initiated* and had dont_filter=True initially
        # This part is for the specific bug where dont_filter propagates through redirect after retry.
        # The idea is that if a request with dont_filter=True triggers a retry,
        # the *subsequent* response (even if it's a redirect) should not keep dont_filter=True.
        # This attempts to fix the dont_filter that gets carried over by RedirectMiddleware.
        if request in self._requests_dont_filter_bug_tracker:
            self.logger.debug(
                "[MyRetryMiddleware] Request %s was part of a dont_filter bug chain. Explicitly setting dont_filter=False.",
                request.url
            )
            # Create a new request object with dont_filter=False
            # This is important if `response` itself is a redirect that will be handled by RedirectMiddleware
            # if this middleware is returning the response.
            # However, if it's a redirect that *we are about to process*, we need to ensure the next request is filtered.
            # The most effective place is where the *new* request is generated (i.e., in get_retry_request or on redirect).

            # For the current situation, the dont_filter=False in get_retry_request is the primary.
            # This block might be redundant if get_retry_request fix is fully effective.
            # Keep it for now, as a safeguard or if there's a misunderstanding of flow.
            # However, the key is the `dont_filter=False` on the *retried* request.
            # If the request coming *into* this `process_response` still has `dont_filter=True`
            # and it's the final request after the full chain, then the bug is still happening
            # due to `RedirectMiddleware` copying the initial `dont_filter=True`.
            # We need to ensure that the request that *leaves* this middleware, if it's not a retry,
            # has its dont_filter property correctly set.
            if request.dont_filter:
                new_request = request.replace(dont_filter=False)
                self.logger.debug(
                    "[MyRetryMiddleware] Request %s dont_filter was True. Replaced with new request having dont_filter: %s",
                    request.url, new_request.dont_filter
                )
                return new_request # Return the modified request to the engine


        if response.status in self.retry_http_codes:
            reason = response.status
            self.logger.debug(
                "[MyRetryMiddleware] Response status %s is in retry_http_codes. Attempting retry for %s.",
                response.status, request.url
            )
            
            # If the original request that is now getting a 503 was dont_filter=True,
            # mark it for tracking so subsequent redirect from its retry can be handled.
            if request.dont_filter:
                self._requests_dont_filter_bug_tracker[request] = True

            retry_req = self._retry(request, reason, spider)
            if retry_req:
                self.logger.debug(
                    "[MyRetryMiddleware] Returning retry request for %s. New dont_filter on retry_req: %s",
                    retry_req.url, retry_req.dont_filter
                )
                return retry_req
            else:
                self.logger.warning(
                    "[MyRetryMiddleware] Failed to retry %s after %d tries. Reason: %s",
                    request.url, request.meta.get('retry_times', 0), reason
                )
                return response # Return original response if retry fails
        
        self.logger.debug(
            "[MyRetryMiddleware] Exiting process_response for %s. Final dont_filter: %s",
            request.url, request.dont_filter
        )
        return response

    def process_exception(self, request, exception, spider):
        self.logger.debug(
            "[MyRetryMiddleware] Entering process_exception for %s. Current dont_filter: %s. Exception: %s",
            request.url, request.dont_filter, type(exception).__name__
        )

        if isinstance(exception, self.exceptions_to_retry) and \
                not request.meta.get('dont_retry', False):
            reason = global_object_name(exception.__class__)
            self.logger.debug(
                "[MyRetryMiddleware] Exception %s is in exceptions_to_retry. Attempting retry for %s.",
                reason, request.url
            )
            # If the original request that is now raising an exception was dont_filter=True,
            # mark it for tracking.
            if request.dont_filter:
                self._requests_dont_filter_bug_tracker[request] = True

            retry_req = self._retry(request, reason, spider)
            if retry_req:
                self.logger.debug(
                    "[MyRetryMiddleware] Returning retry request from exception for %s. New dont_filter on retry_req: %s",
                    retry_req.url, retry_req.dont_filter
                )
                return retry_req
        
        self.logger.debug(
            "[MyRetryMiddleware] Exiting process_exception for %s. Final dont_filter: %s",
            request.url, request.dont_filter
        )
        return None

    def _retry(self, request, reason, spider):
        max_retry_times = request.meta.get("max_retry_times", self.max_retry_times)
        
        # Call the standalone get_retry_request function
        retry_req = get_retry_request(
            request, spider, reason=reason, max_retry_times=max_retry_times
        )

        if retry_req:
            if self.priority_adjust:
                retry_req.priority = request.priority + self.priority_adjust
            self.stats.inc_value('retry/count', spider=spider)
            self.stats.inc_value(f'retry/reason_count/{reason}', spider=spider)
            self.logger.debug(
                "Retrying %(request)s (failed %(retry_times)d times): %(reason)s",
                {"request": request, "retry_times": retry_req.meta["retry_times"], "reason": reason},
                extra={"spider": spider},
            )
            return retry_req
        else:
            self.stats.inc_value('retry/max_reached', spider=spider)
            self.logger.error(
                "Gave up retrying %(request)s (failed %(retry_times)d times): %(reason)s",
                {"request": request, "retry_times": max_retry_times, "reason": reason},
                extra={"spider": spider},
            )
            return None