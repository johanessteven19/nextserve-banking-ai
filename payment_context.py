"""Evidence-based history analysis and bounded public merchant search."""
from datetime import datetime
from statistics import median
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import re
import html


MERCHANTS = {
    'google': ('Google', 'https://support.google.com/googlepay/answer/7644142?hl=en',
               'Google explains that a temporary hold may appear when a payment method is used through its services. This does not identify the specific purchase or who authorized it.'),
    'netflix': ('Netflix', 'https://help.netflix.com/en/node/41049',
                'Netflix describes subscription billing at the beginning of each billing cycle. Compare the payment with the billing history in your Netflix account.'),
    'grab': ('Grab', None, None), 'fairprice': ('FairPrice Finest', None, None),
    'uniqlo': ('Uniqlo', None, None), 'amazon': ('Amazon Marketplace', None, None),
    'sia': ('Singapore Airlines', None, None), 'fresh': ('Cold Storage Singapore', None, None),
    'kopi': ('Ya Kun Kaya Toast Singapore', None, None),
}


def date_of(t):
    return datetime.strptime(t['date'], '%d %b %Y · %H:%M')


def history_context(transactions, current):
    # Only use evidence available at the selected transaction's time.
    cutoff = date_of(current)
    matches = sorted([t for t in transactions if t['merchant_group'] == current['merchant_group']
                      and date_of(t) <= cutoff], key=date_of)
    # Group + descriptor distinguishes separate services from one parent merchant.
    series = [t for t in matches if t['status'] == 'Posted'
              and t['statement_descriptor'] == current['statement_descriptor']]
    gaps = [(date_of(b) - date_of(a)).days for a, b in zip(series, series[1:])]
    monthly = len(series) >= 3 and all(26 <= gap <= 35 for gap in gaps)
    amounts = [t['amount'] for t in series]
    stable = bool(amounts) and max(amounts) - min(amounts) <= .01
    if current['status'] == 'Pending':
        headline = 'A pending payment, not a confirmed recurring charge'
    elif monthly:
        headline = 'This looks like a monthly payment'
    elif len(series) >= 3:
        headline = 'Previous payments found, with no regular monthly pattern'
    else:
        headline = 'Not enough history to establish a recurring pattern'
    return dict(matches=matches, series=series, monthly=monthly, headline=headline,
                stable=stable, typical=median(amounts) if amounts else None,
                first=matches[0]['date'] if matches else None,
                elapsed=(date_of(series[-1]) - date_of(series[0])).days if series else 0)


def parse_search(raw):
    root = ET.fromstring(raw)
    rows = []
    for item in root.findall('./channel/item'):
        url = item.findtext('link', '')
        if urlparse(url).scheme != 'https':
            continue
        clean = lambda value: html.unescape(re.sub('<[^>]*>', '', value or '')).strip()
        rows.append({'title': clean(item.findtext('title')), 'url': url,
                     'snippet': clean(item.findtext('description'))[:600]})
    return rows[:3]


def search_merchant(group):
    # Only the predefined public merchant name leaves the app, never card/transaction data.
    merchant = MERCHANTS.get(group)
    if not merchant:
        return {'rows': [], 'error': 'No external merchant lookup is needed for this bank fee.', 'query': ''}
    query = merchant[0] + ' official merchant billing statement'
    try:
        request = Request('https://www.bing.com/search?' + urlencode({'q':query, 'format':'rss'}),
                          headers={'User-Agent':'Mozilla/5.0'})
        with urlopen(request, timeout=5) as response:
            rows = parse_search(response.read(250000))
        error = None if rows else 'No usable search results were returned.'
    except Exception:
        rows, error = [], 'External search is unavailable right now.'
    return {'rows': rows, 'error': error, 'query': query,
            'checked': datetime.now().strftime('%d %b %Y · %H:%M')}
