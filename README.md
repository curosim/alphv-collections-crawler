# alphv-collections-crawler
Crawls the collections of the Alphv ransomware leaks hidden service.
<br>
You can browse the files of each collection, download them or generate a list of each file path.

*INFO*: This project is not finished yet. Some functions may break or not work at all...

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
<br>
Make sure to have the TOR Socks proxy running before executing.

```
python crawler.py
```
