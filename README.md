## this repo is being used for testing bugs in scrapy , and this is unofficial 

go here for original project 
https://github.com/scrapy/scrapy


how to reproduce bug:

1. clone this repo 
2. navigate to retry_test_bug 
3. activate a venv install dependecies 
4. install local scrapy are other dependencies 
5. navigate to retry_test bug and start local server 
6. read logs from crawler.py 

you can execute the code to directly by running the following:
```bash
git clone https://github.com/pragnyanramtha/scrapy
cd scrapy 
python -m venv .venv 
source .venv/bin/activate
cd retry_test_bug
pip install -r requirements.txt
cd ..
pip install -e ".[dev]"
cd retry_test_bug
python test_server.py 
```

7. open another terminal and execute the following to see debug logs.

```bash
cd scrapy/retry_test_bug
python crawler.py
```


