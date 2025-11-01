"""
Script to extract GRE practice questions from GRE Prep Club forum
and organize them into categorized folders as JSON files.
"""

import os
import json
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path


class GREQuestionExtractor:
    def __init__(self, base_url, output_dir="."):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Mapping of category abbreviations to full folder names
        self.category_mapping = {
            'QCQ': 'Quantitative Comparison (QCQ)',
            'PS': 'Problem Solving (PS)',
            'MAC': 'Multiple Answer Choices (MAC)',
            'NE': 'Numeric Entry (NE)',
            'DI': 'Data Interpretation (DI)',
            'TC': 'Text Completion (TC)',
            'SE': 'Sentence Equivalence (SE)',
            'RC': 'Reading Comprehension (RC)',
        }
        
        # Folder structure for main sections
        self.folder_structure = {
            'Math Diagnostic Test': [
                'Quantitative Comparison (QCQ)',
                'Problem Solving (PS)',
                'Multiple Answer Choices (MAC)',
                'Numeric Entry (NE)',
                'Data Interpretation (DI)'
            ],
            'Verbal Diagnostic Test': [
                'Text Completion (TC)',
                'Sentence Equivalence (SE)',
                'Reading Comprehension (RC)'
            ],
            'Quantitative Section': [
                'Arithmetic',
                'Exponents and Roots',
                'Linear and Quadratic Equations',
                'Functions, Formulas, and Sequences',
                'Inequalities and Absolute Values',
                'Divisibility and Primes',
                'Number Properties',
                'Fractions and Decimals',
                'Percents',
                'Ratios',
                'Word Problems',
                'Two Variables Word Problems',
                'Averages, Weighted Averages, Median, and Mode',
                'Standard Deviation and Normal Distribution',
                'Data Interpretation',
                'Triangles',
                'Polygons and Rectangular Solids',
                'Circles and Cylinders',
                'Coordinate Geometry',
                'Mixed Geometry',
                'Rates and Work',
                'Probability, Combinatorics, and Overlapping Sets',
                'Advanced Quant',
                'Quant Practice Sections',
                'Quant Practice Adaptive Sections'
            ],
            'Verbal Section': [
                'Text Completion',
                'Sentence Equivalence',
                'Reading Comprehension',
                'Passage Paragraph Argument'
            ]
        }
    
    def create_folder_structure(self):
        """Create the folder structure for organizing questions."""
        print("Creating folder structure...")
        for main_folder, subfolders in self.folder_structure.items():
            main_path = self.output_dir / main_folder
            main_path.mkdir(parents=True, exist_ok=True)
            for subfolder in subfolders:
                sub_path = main_path / subfolder
                sub_path.mkdir(parents=True, exist_ok=True)
        print("Folder structure created.")
    
    def fetch_page(self, url, retries=3):
        """Fetch a webpage with retry logic."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"Error fetching {url}: {e}")
                return None
        return None
    
    def parse_main_page(self, url):
        """Parse the main forum page to extract question links organized by category."""
        print(f"Parsing main page: {url}")
        response = self.fetch_page(url)
        if not response:
            print("Failed to fetch page")
            return {}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        questions_by_category = {}
        
        # Extract post ID from URL fragment if present
        post_id = None
        if '#p' in url:
            post_id = url.split('#p')[-1]
            print(f"Looking for post ID: p{post_id}")
        
        # Strategy 1: Find post by ID, then get its content div
        post_content = None
        if post_id:
            post_div = soup.find('div', id=f'p{post_id}')
            if post_div:
                print(f"Found post by ID: p{post_id}")
                # Get the content div within this post
                post_content = post_div.find('div', class_=re.compile('content|postbody|message', re.I))
                if post_content:
                    print(f"Found content div in post p{post_id}")
        
        # Strategy 2: Check first few posts (main content is usually in first post)
        if not post_content:
            all_posts = soup.find_all('div', class_=re.compile('post', re.I))
            print(f"Checking first 10 posts for main content...")
            for i, post in enumerate(all_posts[:10]):
                content_div = post.find('div', class_=re.compile('content|postbody|message', re.I))
                if content_div:
                    text = content_div.get_text()
                    links = content_div.find_all('a', href=True)
                    question_links = [l for l in links if self._is_question_link(l.get('href', ''))]
                    
                    print(f"  Post {i+1}: {len(question_links)} question links")
                    
                    # Look for section markers or many question links
                    has_markers = any(marker in text.lower() for marker in ['qcq', 'ps -', 'tc -', 'se -', 'rc -', 'diagnostic test', 'math diagnostic', 'verbal diagnostic', 'arithmetic', 'exponents'])
                    
                    if len(question_links) > 20 or (has_markers and len(question_links) > 5):
                        post_content = content_div
                        print(f"Found main post (post {i+1}) with {len(question_links)} links and markers={has_markers}")
                        break
        
        # Strategy 3: Find post with most question links AND section markers (scored approach)
        if not post_content:
            all_posts = soup.find_all('div', class_=re.compile('post', re.I))
            print(f"Scoring all {len(all_posts)} posts...")
            
            best_post_score = 0
            best_post_content = None
            
            for i, post in enumerate(all_posts):
                # Find the post content div
                content_div = post.find('div', class_=re.compile('content|postbody|message', re.I))
                if content_div:
                    text = content_div.get_text()
                    links = content_div.find_all('a', href=True)
                    question_links = [l for l in links if self._is_question_link(l.get('href', ''))]
                    
                    # Score based on: number of question links + presence of section markers
                    score = len(question_links)
                    
                    # Check for section markers (heavily weight these)
                    section_markers = ['qcq', 'ps -', 'tc -', 'se -', 'rc -', 'mac', 'ne -', 'di -', 'arithmetic', 'exponents', 'linear', 'functions']
                    marker_count = sum(1 for marker in section_markers if marker in text.lower())
                    score += marker_count * 20  # Heavy bonus for section markers
                    
                    # Prefer posts with many links AND section markers
                    if score > best_post_score:
                        best_post_score = score
                        best_post_content = content_div
                        if i < 5 or score > 50:  # Only print first 5 or high-scoring posts
                            print(f"  Post {i+1}: {len(question_links)} links, {marker_count} markers (score: {score})")
            
            if best_post_content:
                post_content = best_post_content
                print(f"Selected best post with score: {best_post_score}")
        
        if not post_content:
            print("ERROR: Could not find post content!")
            return {}
        
        # Extract all question links first
        all_question_links = []
        all_links = post_content.find_all('a', href=True)
        print(f"Found {len(all_links)} total links in post")
        
        # Debug: show first 20 links
        print("\nDEBUG - First 20 links found:")
        for i, link in enumerate(all_links[:20]):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            is_question = self._is_question_link(href)
            print(f"  {i+1}. [{text[:40]:40}] {href[:60]:60} -> {'QUESTION' if is_question else 'other'}")
        
        for link in all_links:
            href = link.get('href', '')
            if self._is_question_link(href):
                link_text = link.get_text(strip=True)
                # Normalize URL
                if href.startswith('/'):
                    full_url = urljoin(self.base_url, href)
                elif not href.startswith('http'):
                    full_url = urljoin(self.base_url, href)
                else:
                    full_url = href
                
                all_question_links.append({
                    'url': full_url,
                    'text': link_text or href,
                    'element': link
                })
        
        print(f"\nFound {len(all_question_links)} question links")
        
        # Debug: print first 2000 chars of text to see structure
        debug_text = post_content.get_text(separator='\n')[:2000]
        print(f"\nDEBUG - First 2000 chars of post text:")
        print(debug_text)
        print("\n" + "="*80 + "\n")
        
        # Now parse by walking through the DOM structure
        # Find section markers and associate following links
        current_category = None
        
        # Get text content with positions
        full_text = post_content.get_text(separator='\n')
        lines = full_text.split('\n')
        
        # Process line by line to find categories
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check for section marker
            category = self._detect_section_marker(line_stripped)
            if category:
                # Save previous category's links (links found before this marker)
                if current_category:
                    main_cat, sub_cat = current_category
                    if main_cat not in questions_by_category:
                        questions_by_category[main_cat] = {}
                    if sub_cat not in questions_by_category[main_cat]:
                        questions_by_category[main_cat][sub_cat] = []
                    print(f"Found category: {main_cat} > {sub_cat}")
                
                current_category = category
            
            # If we have a category, find question links near this line
            if current_category:
                main_cat, sub_cat = current_category
                if main_cat not in questions_by_category:
                    questions_by_category[main_cat] = {}
                if sub_cat not in questions_by_category[main_cat]:
                    questions_by_category[main_cat][sub_cat] = []
                
                # Check links in nearby lines (current line and next few lines)
                for j in range(i, min(len(lines), i+10)):
                    nearby_line = lines[j].lower()
                    for link_item in all_question_links:
                        link_url = link_item['url']
                        link_text_lower = link_item['text'].lower()
                        
                        # Check if link text appears in this line or nearby
                        if (link_text_lower in nearby_line or 
                            any(word in nearby_line for word in link_text_lower.split()[:3] if len(word) > 3)):
                            # Add if not already added
                            if not any(q['url'] == link_url for q in questions_by_category[main_cat][sub_cat]):
                                questions_by_category[main_cat][sub_cat].append({
                                    'url': link_url,
                                    'text': link_item['text']
                                })
        
        # Also do a final pass: for any unassigned links, assign to nearest category
        assigned_urls = set()
        for main_cat, subcats in questions_by_category.items():
            for subcat, links in subcats.items():
                for link in links:
                    assigned_urls.add(link['url'])
        
        # Assign remaining links to categories based on DOM position
        unassigned_links = [link for link in all_question_links if link['url'] not in assigned_urls]
        if unassigned_links and questions_by_category:
            # Use the last category found
            last_main_cat = list(questions_by_category.keys())[-1]
            last_sub_cat = list(questions_by_category[last_main_cat].keys())[-1]
            for link_item in unassigned_links:
                questions_by_category[last_main_cat][last_sub_cat].append({
                    'url': link_item['url'],
                    'text': link_item['text']
                })
        
        # Fallback: associate all question links with categories based on proximity
        if not questions_by_category:
            print("No categories found in text, using fallback method...")
            # Group links by finding category markers near them
            for link in all_links:
                href = link.get('href', '')
                if not self._is_question_link(href):
                    continue
                
                # Find the link's position in the HTML
                parent = link.find_parent(['div', 'p', 'li', 'td'])
                if parent:
                    # Get surrounding context
                    parent_text = parent.get_text()
                    category = self._determine_category(parent_text, link.get_text())
                    if category:
                        main_cat, sub_cat = category
                        if main_cat not in questions_by_category:
                            questions_by_category[main_cat] = {}
                        if sub_cat not in questions_by_category[main_cat]:
                            questions_by_category[main_cat][sub_cat] = []
                        
                        full_url = urljoin(self.base_url, href) if not href.startswith('http') else href
                        questions_by_category[main_cat][sub_cat].append({
                            'url': full_url,
                            'text': link.get_text(strip=True) or href
                        })
        
        print(f"\nExtracted questions by category:")
        for main_cat, subcats in questions_by_category.items():
            for subcat, links in subcats.items():
                print(f"  {main_cat} > {subcat}: {len(links)} questions")
        
        return questions_by_category
    
    def _is_question_link(self, href):
        """Check if a link URL points to a question."""
        if not href:
            return False
        
        href_lower = href.lower()
        
        # Skip common non-question links
        skip_patterns = ['search', 'member', 'profile', 'login', 'register', 'mchat', 'viewforum', 'viewtopic', 'download', 'attachment']
        if any(pattern in href_lower for pattern in skip_patterns):
            return False
        
        # Question links typically:
        # 1. Have forum path and .html extension
        # 2. Are relative URLs ending in .html (like /forum/question-name-12345.html)
        # 3. Have topic parameter (t=)
        # 4. Are on gre.myprepclub.com domain
        
        # Match patterns like: /forum/question-name-12345.html or question-name-12345.html
        if '.html' in href_lower:
            # Check if it's a forum question (not a general page)
            if 'forum' in href_lower or href_lower.count('/') <= 2:
                return True
        
        # Match topic links
        if 't=' in href_lower or '/t' in href_lower:
            return True
        
        # Match gre.myprepclub.com forum links
        if 'gre.myprepclub.com' in href_lower and 'forum' in href_lower:
            return True
        
        return False
    
    def _detect_section_marker(self, text):
        """Detect if text contains a section marker and return category tuple."""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Diagnostic Test markers - be more flexible with matching
        if 'qcq' in text_lower and ('-' in text_lower or len(text_lower) < 10):
            return ('Math Diagnostic Test', 'Quantitative Comparison (QCQ)')
        if ('ps -' in text_lower or text_lower.startswith('ps')) and len(text_lower) < 20:
            return ('Math Diagnostic Test', 'Problem Solving (PS)')
        if 'mac' in text_lower and ('-' in text_lower or len(text_lower) < 10):
            return ('Math Diagnostic Test', 'Multiple Answer Choices (MAC)')
        if ('ne -' in text_lower or (text_lower.startswith('ne') and len(text_lower) < 20)):
            return ('Math Diagnostic Test', 'Numeric Entry (NE)')
        if ('di -' in text_lower or (text_lower.startswith('di') and len(text_lower) < 30)):
            return ('Math Diagnostic Test', 'Data Interpretation (DI)')
        
        # Verbal Diagnostic Test markers
        if ('tc -' in text_lower or (text_lower.startswith('tc') and len(text_lower) < 20)):
            return ('Verbal Diagnostic Test', 'Text Completion (TC)')
        if ('se -' in text_lower or (text_lower.startswith('se') and len(text_lower) < 30)):
            return ('Verbal Diagnostic Test', 'Sentence Equivalence (SE)')
        if ('rc -' in text_lower or (text_lower.startswith('rc') and len(text_lower) < 30)):
            return ('Verbal Diagnostic Test', 'Reading Comprehension (RC)')
        
        # Quantitative Section markers (section headers)
        quant_headers = {
            'arithmetic': ('Quantitative Section', 'Arithmetic'),
            'exponents and roots': ('Quantitative Section', 'Exponents and Roots'),
            'linear and quadratic equations': ('Quantitative Section', 'Linear and Quadratic Equations'),
            'functions, formulas, and sequences': ('Quantitative Section', 'Functions, Formulas, and Sequences'),
            'inequalities and absolute values': ('Quantitative Section', 'Inequalities and Absolute Values'),
            'divisibility and primes': ('Quantitative Section', 'Divisibility and Primes'),
            'number properties': ('Quantitative Section', 'Number Properties'),
            'fractions and decimals': ('Quantitative Section', 'Fractions and Decimals'),
            'percents': ('Quantitative Section', 'Percents'),
            'ratios': ('Quantitative Section', 'Ratios'),
            'word problems': ('Quantitative Section', 'Word Problems'),
            'two variables word problems': ('Quantitative Section', 'Two Variables Word Problems'),
            'averages': ('Quantitative Section', 'Averages, Weighted Averages, Median, and Mode'),
            'standard deviation': ('Quantitative Section', 'Standard Deviation and Normal Distribution'),
            'data interpretation': ('Quantitative Section', 'Data Interpretation'),
            'triangles': ('Quantitative Section', 'Triangles'),
            'polygons': ('Quantitative Section', 'Polygons and Rectangular Solids'),
            'circles': ('Quantitative Section', 'Circles and Cylinders'),
            'coordinate geometry': ('Quantitative Section', 'Coordinate Geometry'),
            'mixed geometry': ('Quantitative Section', 'Mixed Geometry'),
            'rates and work': ('Quantitative Section', 'Rates and Work'),
            'probability': ('Quantitative Section', 'Probability, Combinatorics, and Overlapping Sets'),
            'advanced quant': ('Quantitative Section', 'Advanced Quant'),
            'quant practice sections': ('Quantitative Section', 'Quant Practice Sections'),
            'quant practice adaptive sections': ('Quantitative Section', 'Quant Practice Adaptive Sections'),
        }
        
        for key, value in quant_headers.items():
            if key in text_lower and len(text_lower) < 100:  # Section headers are usually short
                return value
        
        # Verbal Section markers
        if 'text completion' in text_lower and 'diagnostic' not in text_lower and len(text_lower) < 100:
            return ('Verbal Section', 'Text Completion')
        if 'sentence equivalence' in text_lower and 'diagnostic' not in text_lower and len(text_lower) < 100:
            return ('Verbal Section', 'Sentence Equivalence')
        if 'reading comprehension' in text_lower and 'diagnostic' not in text_lower and len(text_lower) < 100:
            return ('Verbal Section', 'Reading Comprehension')
        if 'paragraph argument' in text_lower or 'passage paragraph' in text_lower:
            return ('Verbal Section', 'Passage Paragraph Argument')
        
        return None
    
    def _determine_category(self, context_text, link_text):
        """Determine the category based on context."""
        context_lower = context_text.lower()
        
        # Diagnostic Test categories
        if 'qcq' in context_lower or 'quantitative comparison' in context_lower:
            return ('Math Diagnostic Test', 'Quantitative Comparison (QCQ)')
        if 'ps' in context_lower and ('problem solving' in context_lower or 'ps -' in context_lower):
            return ('Math Diagnostic Test', 'Problem Solving (PS)')
        if 'mac' in context_lower or 'multiple answer' in context_lower:
            return ('Math Diagnostic Test', 'Multiple Answer Choices (MAC)')
        if 'ne' in context_lower and ('numeric entry' in context_lower or 'ne -' in context_lower):
            return ('Math Diagnostic Test', 'Numeric Entry (NE)')
        if 'di' in context_lower and ('data interpretation' in context_lower or 'di -' in context_lower):
            return ('Math Diagnostic Test', 'Data Interpretation (DI)')
        
        # Verbal Diagnostic Test
        if 'tc' in context_lower and ('text completion' in context_lower or 'tc -' in context_lower):
            return ('Verbal Diagnostic Test', 'Text Completion (TC)')
        if 'se' in context_lower and ('sentence equivalence' in context_lower or 'se -' in context_lower):
            return ('Verbal Diagnostic Test', 'Sentence Equivalence (SE)')
        if 'rc' in context_lower and ('reading comprehension' in context_lower or 'rc -' in context_lower):
            return ('Verbal Diagnostic Test', 'Reading Comprehension (RC)')
        
        # Quantitative Section categories
        quant_sections = {
            'arithmetic': 'Arithmetic',
            'exponents and roots': 'Exponents and Roots',
            'linear and quadratic equations': 'Linear and Quadratic Equations',
            'functions, formulas, and sequences': 'Functions, Formulas, and Sequences',
            'inequalities and absolute values': 'Inequalities and Absolute Values',
            'divisibility and primes': 'Divisibility and Primes',
            'number properties': 'Number Properties',
            'fractions and decimals': 'Fractions and Decimals',
            'percents': 'Percents',
            'ratios': 'Ratios',
            'word problems': 'Word Problems',
            'two variables word problems': 'Two Variables Word Problems',
            'averages': 'Averages, Weighted Averages, Median, and Mode',
            'standard deviation': 'Standard Deviation and Normal Distribution',
            'triangles': 'Triangles',
            'polygons': 'Polygons and Rectangular Solids',
            'circles': 'Circles and Cylinders',
            'coordinate geometry': 'Coordinate Geometry',
            'mixed geometry': 'Mixed Geometry',
            'rates and work': 'Rates and Work',
            'probability': 'Probability, Combinatorics, and Overlapping Sets',
            'advanced quant': 'Advanced Quant',
        }
        
        for key, value in quant_sections.items():
            if key in context_lower:
                return ('Quantitative Section', value)
        
        # Verbal Section categories
        if 'text completion' in context_lower and 'diagnostic' not in context_lower:
            return ('Verbal Section', 'Text Completion')
        if 'sentence equivalence' in context_lower and 'diagnostic' not in context_lower:
            return ('Verbal Section', 'Sentence Equivalence')
        if 'reading comprehension' in context_lower and 'diagnostic' not in context_lower:
            return ('Verbal Section', 'Reading Comprehension')
        if 'paragraph argument' in context_lower or 'passage paragraph' in context_lower:
            return ('Verbal Section', 'Passage Paragraph Argument')
        
        return None
    
    def extract_question_content(self, url):
        """Extract question content from a question page."""
        response = self.fetch_page(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        question_data = {
            'question': '',
            'answer_choices': [],
            'correct_answer': '',
            'explanation': '',
            'question_type': '',
            'source_url': url
        }
        
        # Remove navigation and sidebar elements first
        for nav in soup.find_all(['nav', 'header', 'footer', 'aside']):
            nav.decompose()
        
        # Remove common navigation classes
        for elem in soup.find_all(class_=re.compile('navbar|navigation|sidebar|menu|header|footer', re.I)):
            elem.decompose()
        
        # Find the main content area (usually contains the question)
        # Strategy 1: Find first post in the topic (the question post)
        main_content = None
        
        # Look for topic container
        topic_container = soup.find('div', class_=re.compile('topic|main-content|content-wrap', re.I))
        if topic_container:
            # Find first post within topic
            first_post = topic_container.find('div', class_=re.compile('post', re.I))
            if first_post:
                main_content = first_post.find('div', class_=re.compile('content|postbody|message-body', re.I))
        
        # Strategy 2: Find post by looking for first substantial post content
        if not main_content:
            all_posts = soup.find_all('div', class_=re.compile('post', re.I))
            for post in all_posts:
                # Skip posts that are clearly navigation or headers
                post_text = post.get_text(strip=True)
                if any(nav_word in post_text.lower() for nav_word in ['forum', 'tests', 'gre prep', 'discounts', 'sign in', 'join now']):
                    continue
                
                content_div = post.find('div', class_=re.compile('content|postbody|message-body|post-content', re.I))
                if content_div:
                    text = content_div.get_text(strip=True)
                    # Question posts are usually substantial and don't contain navigation
                    if len(text) > 100 and 'forum' not in text.lower()[:200]:
                        main_content = content_div
                        break
        
        # Strategy 3: Find by itemprop or specific post IDs
        if not main_content:
            main_content = soup.find('div', itemprop='text')
        
        # Strategy 4: Find content area excluding navigation
        if not main_content:
            # Find main content wrapper
            for div in soup.find_all('div', class_=re.compile('content|main|wrapper', re.I)):
                text = div.get_text(strip=True)
                # Skip if it contains navigation text
                if any(nav_word in text.lower()[:500] for nav_word in ['main forum', 'active discussions', 'sign in', 'join now']):
                    continue
                if len(text) > 200:
                    main_content = div
                    break
        
        if main_content:
            # Extract question text (first post, before spoilers/explanations)
            question_text = self._extract_question_text(main_content)
            question_data['question'] = question_text
            
            # Extract answer choices if present
            answer_choices = self._extract_answer_choices(main_content)
            question_data['answer_choices'] = answer_choices
            
            # Extract correct answer from entire page (may be in later posts)
            correct_answer = self._extract_correct_answer(main_content, soup)
            question_data['correct_answer'] = correct_answer
            
            # Extract explanation from entire page (may be in expert reply)
            explanation = self._extract_explanation(main_content, soup)
            question_data['explanation'] = explanation
            
            # Determine question type
            question_data['question_type'] = self._determine_question_type(question_text, answer_choices)
        
        # If question is too short or looks like navigation, return None
        if question_data['question'] and len(question_data['question'].strip()) < 50:
            return None
        
        if question_data['question'] and any(nav_word in question_data['question'].lower()[:200] for nav_word in ['main forum', 'sign in', 'join now', 'gre prep']):
            return None
        
        return question_data
    
    def _extract_question_text(self, element):
        """Extract the question text from an element."""
        # Clone to avoid modifying original
        text_element = BeautifulSoup(str(element), 'html.parser')
        
        # Remove navigation elements
        for tag in text_element.find_all(['nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # Remove spoiler tags and answer sections
        for tag in text_element.find_all(['div', 'span'], class_=re.compile('spoiler|answer|explanation', re.I)):
            tag.decompose()
        
        # Remove signature blocks
        for tag in text_element.find_all(['div', 'span'], class_=re.compile('signature', re.I)):
            tag.decompose()
        
        # Get text, preserving line breaks
        text = text_element.get_text(separator='\n', strip=True)
        
        # Remove common navigation text patterns
        lines = text.split('\n')
        filtered_lines = []
        skip_next_nav = False
        for line in lines:
            line_lower = line.lower().strip()
            # Skip navigation lines
            if any(nav in line_lower for nav in ['main forum', 'active discussions', 'sign in', 'join now', 
                                                  'gre prep', 'discounts', 'reviews', 'deals', 'blog', 'chat',
                                                  'my profile', 'logout', 'settings', 'email', 'password']):
                continue
            # Skip empty lines at start
            if not filtered_lines and not line.strip():
                continue
            filtered_lines.append(line)
        
        text = '\n'.join(filtered_lines)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing navigation-like content
        text = text.strip()
        
        return text
    
    def _extract_answer_choices(self, element):
        """Extract answer choices from an element."""
        choices = []
        
        # Look for list items, options, or labeled choices
        # Common patterns: (A), (B), 1), 2), etc.
        text = element.get_text()
        
        # Try to find choices by pattern
        choice_pattern = r'[\(（]([A-Ea-e])[\)）]\s*(.+?)(?=[\(（][A-Ea-e][\)）]|$)'
        matches = re.findall(choice_pattern, text, re.DOTALL)
        
        if matches:
            for match in matches:
                choices.append(match[1].strip())
        else:
            # Try numbered choices
            choice_pattern = r'(\d+)[\.\)]\s*(.+?)(?=\d+[\.\)]|$)'
            matches = re.findall(choice_pattern, text, re.DOTALL)
            for match in matches:
                choices.append(match[1].strip())
        
        return choices
    
    def _extract_correct_answer(self, element, soup):
        """Extract the correct answer."""
        # Look for OA (Official Answer) tags or spoiler tags
        oa_tag = soup.find(string=re.compile(r'OA[:\s]*[A-E]', re.I))
        if oa_tag:
            match = re.search(r'OA[:\s]*([A-E])', oa_tag, re.I)
            if match:
                return match.group(1)
        
        # Look for spoiler tags that might contain the answer
        spoiler = soup.find(['div', 'span'], class_=re.compile('spoiler', re.I))
        if spoiler:
            answer_text = spoiler.get_text(strip=True)
            # Check if it's a single letter answer
            match = re.search(r'\b([A-E])\b', answer_text)
            if match:
                return match.group(1)
            return answer_text
        
        return ''
    
    def _extract_explanation(self, element, soup):
        """Extract the explanation."""
        # Look for explanation sections
        explanation_sections = soup.find_all(['div', 'p'], class_=re.compile('explanation', re.I))
        
        if explanation_sections:
            explanations = []
            for section in explanation_sections:
                explanations.append(section.get_text(separator='\n', strip=True))
            return '\n\n'.join(explanations)
        
        # Look for expert replies or solution posts
        expert_posts = soup.find_all('div', class_=re.compile('expert|solution', re.I))
        if expert_posts:
            explanations = []
            for post in expert_posts:
                text = post.get_text(separator='\n', strip=True)
                # Remove question text if it's repeated
                if len(text) > 100:  # Likely an explanation
                    explanations.append(text)
            if explanations:
                return '\n\n'.join(explanations)
        
        # Look for posts by experts (usually have "Expert" in author name or class)
        expert_authors = soup.find_all(['div', 'span'], class_=re.compile('author|username', re.I))
        for author_elem in expert_authors:
            author_text = author_elem.get_text(strip=True)
            if 'expert' in author_text.lower():
                # Find the post content following this author
                post = author_elem.find_parent('div', class_=re.compile('post', re.I))
                if post:
                    content = post.find('div', class_=re.compile('content|postbody', re.I))
                    if content:
                        text = content.get_text(separator='\n', strip=True)
                        if len(text) > 100:
                            return text
        
        # Look for second post (often contains explanation)
        all_posts = soup.find_all('div', class_=re.compile('post', re.I))
        if len(all_posts) > 1:
            # Second post might be explanation
            second_post = all_posts[1]
            content = second_post.find('div', class_=re.compile('content|postbody', re.I))
            if content:
                text = content.get_text(separator='\n', strip=True)
                # Check if it looks like an explanation (not just question repeated)
                if len(text) > 150 and 'explanation' not in text.lower()[:50]:
                    return text
        
        return ''
    
    def _determine_question_type(self, question_text, answer_choices):
        """Determine the question type based on content."""
        text_lower = question_text.lower()
        
        if 'quantity a' in text_lower and 'quantity b' in text_lower:
            return 'Quantitative Comparison'
        if len(answer_choices) > 5:
            return 'Multiple Answer Choices'
        if 'select all' in text_lower or 'select one or more' in text_lower:
            return 'Multiple Answer Choices'
        if not answer_choices and ('enter' in text_lower or 'numeric' in text_lower):
            return 'Numeric Entry'
        if 'blank' in text_lower or 'complete' in text_lower:
            return 'Text Completion'
        if 'sentence' in text_lower and 'equivalence' in text_lower:
            return 'Sentence Equivalence'
        if 'passage' in text_lower or 'according to the passage' in text_lower:
            return 'Reading Comprehension'
        
        return 'Problem Solving' if answer_choices else 'Unknown'
    
    def sanitize_filename(self, text, max_length=100):
        """Generate a filename from question text."""
        if not text or not isinstance(text, str):
            return 'question'
        
        # Take first few words (up to 8 words or 60 chars, whichever comes first)
        words = text.split()[:8]
        filename = '_'.join(words)
        
        # Remove special characters but keep alphanumeric, underscores, and hyphens
        filename = re.sub(r'[^\w\s-]', '', filename)
        filename = re.sub(r'[-\s]+', '_', filename)
        
        # Limit length
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        # Remove trailing underscores and make lowercase
        filename = filename.strip('_').lower()
        
        return filename if filename else 'question'
    
    def save_question(self, question_data, category_path, base_filename):
        """Save a question as a JSON file."""
        filename = self.sanitize_filename(base_filename)
        filepath = category_path / f"{filename}.json"
        
        # Handle collisions
        counter = 1
        original_filepath = filepath
        while filepath.exists():
            filepath = category_path / f"{filename}_{counter}.json"
            counter += 1
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(question_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def create_index(self, category_path, questions):
        """Create an index file for a category."""
        index_data = {
            'category': category_path.name,
            'total_questions': len(questions),
            'questions': questions
        }
        
        index_path = category_path / 'index.json'
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)


def main():
    main_url = "https://gre.myprepclub.com/forum/the-5-lb-book-of-gre-practice-problems-34935.html#p119769"
    
    extractor = GREQuestionExtractor(main_url)
    
    # Step 1: Create folder structure
    extractor.create_folder_structure()
    
    # Step 2: Parse main page
    questions_by_category = extractor.parse_main_page(main_url)
    
    # Step 3: Extract and save questions
    total_questions = 0
    for main_cat, subcats in questions_by_category.items():
        for subcat, question_links in subcats.items():
            category_path = extractor.output_dir / main_cat / subcat
            saved_questions = []
            
            print(f"\nProcessing {main_cat} > {subcat} ({len(question_links)} questions)...")
            
            for idx, q_link in enumerate(question_links, 1):
                print(f"  [{idx}/{len(question_links)}] Extracting: {q_link['url']}")
                
                question_data = extractor.extract_question_content(q_link['url'])
                if question_data and question_data['question']:
                    # Add category information
                    question_data['category'] = subcat
                    question_data['main_category'] = main_cat
                    
                    # Use question text for filename, fallback to link text
                    filename_base = question_data['question'] or q_link['text'] or 'question'
                    filepath = extractor.save_question(question_data, category_path, filename_base)
                    saved_questions.append({
                        'filename': filepath.name,
                        'url': q_link['url'],
                        'question_preview': question_data['question'][:100]
                    })
                    total_questions += 1
                    time.sleep(1)  # Rate limiting
                else:
                    print(f"    Failed to extract question content")
            
            # Create index for this category
            if saved_questions:
                extractor.create_index(category_path, saved_questions)
    
    print(f"\n\nExtraction complete! Total questions extracted: {total_questions}")


if __name__ == "__main__":
    main()

