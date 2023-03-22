# alphv-collections-crawler
Crawls the collections mirrors of the Alphv hidden service.
<br>
The results are displayed in a CLI table, additionally results are saved to a JSON file (filename defined in config).

**Onion Service:**
```
alphvmmm27o3abo3r2mlmjrpdmzle3rykajqc5xsj7j7ejksbpsa36ad.onion
```

### Installation:
```
git clone https://github.com/curosim/alphv-collections-crawler
cd alphv-collections-crawler
python -m pip install -r requirements.txt
```

### Usage:

Simply run the script in the command line, no parameters needed.
<br>
Some options can be set in the source code (tor socks port, website cookie values, results filename).

```
python crawler.py
```
