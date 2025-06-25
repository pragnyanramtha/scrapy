# test_server.py
from flask import Flask, redirect, Response, make_response
import time

app = Flask(__name__)

# Counter to track hits for /first_fail
# This must be reset for each test run if running multiple times.
# For a simple local test, it's fine.
first_fail_hit_count = 0

@app.route('/sbn/')
def initial_page():
    global first_fail_hit_count
    first_fail_hit_count = 0 # Reset counter for a fresh test run
    print(f"Server: Hit /sbn/ (initial)")
    # Redirect immediately to the page that will fail/retry/redirect
    return redirect('/first_fail', code=307) # Use 307 to preserve method if needed

@app.route('/first_fail')
def temp_error_page():
    global first_fail_hit_count
    first_fail_hit_count += 1
    print(f"Server: Hit /first_fail. Count: {first_fail_hit_count}")

    if first_fail_hit_count == 1:
        # First hit: Return 503 to trigger Scrapy's retry
        print("Server: Returning 503 for /first_fail (to trigger retry)")
        return Response("Service Unavailable", status=503)
    else:
        # Second hit (the retry): Redirect to the previously crawled /sbn
        print("Server: Redirecting from /first_fail (retried) to /sbn")
        # Using 307 to ensure the Request method is preserved (though GET is default)
        return redirect('/sbn', code=307)

@app.route('/sbn') # Note: No trailing slash here, as per your log
def final_sbn_page():
    print(f"Server: Hit /sbn (final page, should be filtered if from redirect chain)")
    return "You reached the final SBN page!"

if __name__ == '__main__':
    app.run(port=8000, debug=True)