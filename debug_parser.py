"""Debug script to inspect the HTML structure of the forum page."""

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

# Find all links
print("=" * 80)
print("ALL LINKS FOUND:")
print("=" * 80)
links = soup.find_all('a', href=True)
for i, link in enumerate(links[:50]):  # First 50 links
    href = link.get('href', '')
    text = link.get_text(strip=True)
    if 'forum' in href:
        print(f"{i+1}. {text[:50]:50} -> {href[:80]}")

print("\n" + "=" * 80)
print("LOOKING FOR SECTION MARKERS:")
print("=" * 80)

# Look for section markers
post_content = soup.find('div', class_=re.compile('postbody|content|post-content', re.I))
if not post_content:
    post_content = soup.find('body') or soup

# Look for text containing QCQ, PS, TC, etc.
text_content = post_content.get_text()
lines = text_content.split('\n')
for i, line in enumerate(lines):
    line_lower = line.lower().strip()
    if any(marker in line_lower for marker in ['qcq', 'ps -', 'tc -', 'se -', 'rc -', 'mac', 'ne -', 'di -']):
        print(f"Line {i}: {line[:100]}")

print("\n" + "=" * 80)
print("POST CONTENT STRUCTURE:")
print("=" * 80)
# Find the main post - look for post ID 119769
post_119769 = soup.find('div', id='p119769')
if post_119769:
    print("Found post #119769")
    content = post_119769.find('div', class_=re.compile('content|postbody', re.I))
    if content:
        print("\nContent:")
        print(content.get_text()[:1000])
        
        # Find links in this post
        print("\nLinks in this post:")
        links_in_post = content.find_all('a', href=True)
        for link in links_in_post[:20]:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"  {text[:40]:40} -> {href[:60]}")

# Also try finding posts by author "Carcass" (the expert who posted)
carcass_posts = soup.find_all('div', class_=re.compile('post', re.I))
print(f"\nFound {len(carcass_posts)} total posts")
for i, post in enumerate(carcass_posts[:5]):
    author = post.find(['a', 'span'], class_=re.compile('author|username', re.I))
    if author:
        author_text = author.get_text(strip=True)
        if 'carcass' in author_text.lower():
            print(f"\n--- Post by {author_text} ---")
            content = post.find('div', class_=re.compile('content|postbody', re.I))
            if content:
                text = content.get_text()[:800]
                print(text)
                # Get links
                links = content.find_all('a', href=True)
                print(f"\n  Found {len(links)} links in this post")
                for link in links[:10]:
                    print(f"    {link.get_text(strip=True)[:40]} -> {link.get('href', '')[:60]}")

