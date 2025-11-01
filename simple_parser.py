"""Simple test to see actual post structure"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://gre.myprepclub.com/forum/the-5-lb-book-of-gre-practice-problems-34935.html#p119769"

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

response = session.get(url, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')

# Find post 119769
post = soup.find('div', id='p119769')
if post:
    print("Found post p119769")
    # Find content div
    content = post.find('div', class_=re.compile('content|postbody|message', re.I))
    if content:
        print("\n" + "="*80)
        print("TEXT CONTENT (first 5000 chars):")
        print("="*80)
        text = content.get_text(separator='\n')
        print(text[:5000])
        
        print("\n" + "="*80)
        print("LINKS:")
        print("="*80)
        links = content.find_all('a', href=True)
        for i, link in enumerate(links[:30]):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            if 'forum' in href and '.html' in href:
                print(f"{i+1}. [{link_text[:50]:50}] -> {href}")

