"""Test extraction to see actual HTML structure"""

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

# Find post by ID
post_119769 = soup.find('div', id='p119769')
if post_119769:
    print("=" * 80)
    print("POST 119769 CONTENT:")
    print("=" * 80)
    content = post_119769.find('div', class_=re.compile('content|postbody|message', re.I))
    if content:
        # Get raw HTML
        print("\nHTML (first 2000 chars):")
        print(content.prettify()[:2000])
        
        print("\n" + "=" * 80)
        print("TEXT CONTENT:")
        print("=" * 80)
        text = content.get_text(separator='\n')
        print(text[:3000])
        
        print("\n" + "=" * 80)
        print("ALL LINKS IN POST:")
        print("=" * 80)
        links = content.find_all('a', href=True)
        for i, link in enumerate(links):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"{i+1}. {text[:60]:60} -> {href[:80]}")

