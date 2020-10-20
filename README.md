# Charity Parser

Parses the charity informations (general and financial) from CRA website and stores them as a csv.
The csv can be read a `multiindex` pandas dataframe.

Please use a delay between each request to not make CRA servers busy.

To run the code, make sure you have the requirements mentioned in `requirements.txt` (should work for most versions), then in linux or mac run the following command in a terminal

```
python bs4cra.py > craOutput 2 > craErrors
```
