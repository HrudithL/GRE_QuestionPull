"""
Script to extract GRE practice questions from GRE Prep Club forum
and organize them into categorized folders as JSON files.
"""

import os
import json
import re
import time
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit
from pathlib import Path


class GREQuestionExtractor:
    def __init__(self, base_url, output_dir="."):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
            'Referer': base_url
        })
        
        # Mapping of section names to folder names
        self.section_mapping = {
            'GRE Arithmetic': 'Arithmetic',
            'GRE Algebra & Word Problems': 'Word Problems',
            'GRE Algebra': 'Linear and Quadratic Equations',
            'GRE Geometry': 'Triangles',
            'GRE Data Analysis': 'Data Interpretation',
        }
        
        # Mapping of special subsection names to folder names
        self.subsection_mapping = {
            'Graphs & Illustrations': 'Data Interpretation',
            'Overlapping Sets': 'Probability, Combinatorics, and Overlapping Sets',
            'Sequence and Series': 'Functions, Formulas, and Sequences',
            'SIMPLE INTEREST AND COMPOUND INTEREST': 'Percents',
            'Rate and Time': 'Rates and Work',
            'Statistic': 'Averages, Weighted Averages, Median, and Mode',
        }
        
        # Folder structure for main sections - matching sections.txt
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
                'Passage Paragraph Argument',
                'Verbal Practice Sections',
                'Verbal Practice Adaptive Sections'
            ]
        }
    
    def _normalize_url(self, url: str) -> str:
        """Remove fragments and normalize whitespace within a URL."""
        if not url:
            return url
        parts = urlsplit(url.strip())
        # Remove fragment portion (#...)
        normalized = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))
        return normalized

    def cleanup_old_questions(self, target_main_category=None, target_subcategory=None):
        """Remove existing JSON files for specified categories while preserving folder structure."""
        print("Cleaning up old question files...")
        deleted_count = 0

        # Question type folders for Quantitative Section subsections
        quant_question_types = [
            'Quantitative Comparison (QCQ)',
            'Problem Solving (PS)',
            'Multiple Answer Choices (MAC)',
            'Numeric Entry (NE)',
            'Data Interpretation (DI)'
        ]

        # Helper to determine if a folder should be cleaned
        def should_clean(main_folder, subfolder=None):
            if target_main_category and main_folder != target_main_category:
                return False
            if target_subcategory and subfolder and subfolder != target_subcategory:
                return False
            return True

        # First, clean up remnant top-level question type folders in Quantitative Section
        if should_clean('Quantitative Section'):
            quant_section_path = self.output_dir / 'Quantitative Section'
            if quant_section_path.exists():
                for qt_folder in quant_question_types:
                    qt_path = quant_section_path / qt_folder
                    if qt_path.exists():
                        print(f"  Removing remnant folder: Quantitative Section/{qt_folder}")
                        for json_file in qt_path.glob('*.json'):
                            try:
                                json_file.unlink()
                                deleted_count += 1
                            except Exception as e:
                                print(f"  Warning: Could not delete {json_file}: {e}")
                        try:
                            if not any(qt_path.iterdir()):
                                qt_path.rmdir()
                        except Exception:
                            pass

        for main_folder, subfolders in self.folder_structure.items():
            if target_main_category and main_folder != target_main_category:
                continue

            main_path = self.output_dir / main_folder
            if not main_path.exists():
                continue

            for subfolder in subfolders:
                if target_subcategory and subfolder != target_subcategory:
                    continue

                sub_path = main_path / subfolder

                if main_folder == 'Quantitative Section':
                    for qt_folder in quant_question_types:
                        qt_path = sub_path / qt_folder
                        if qt_path.exists():
                            for json_file in qt_path.glob('*.json'):
                                try:
                                    json_file.unlink()
                                    deleted_count += 1
                                except Exception as e:
                                    print(f"  Warning: Could not delete {json_file}: {e}")

                if sub_path.exists():
                    for json_file in sub_path.glob('*.json'):
                        try:
                            json_file.unlink()
                            deleted_count += 1
                        except Exception as e:
                            print(f"  Warning: Could not delete {json_file}: {e}")

        print(f"Deleted {deleted_count} old question files.")
    
    def create_folder_structure(self):
        """Create the folder structure for organizing questions."""
        print("Creating folder structure...")
        
        # Question type folders for Quantitative Section subsections
        quant_question_types = [
            'Quantitative Comparison (QCQ)',
            'Problem Solving (PS)',
            'Multiple Answer Choices (MAC)',
            'Numeric Entry (NE)',
            'Data Interpretation (DI)'
        ]
        
        for main_folder, subfolders in self.folder_structure.items():
            main_path = self.output_dir / main_folder
            main_path.mkdir(parents=True, exist_ok=True)
            for subfolder in subfolders:
                sub_path = main_path / subfolder
                sub_path.mkdir(parents=True, exist_ok=True)
                
                # For Quantitative Section subsections, create question type subfolders
                if main_folder == 'Quantitative Section':
                    for qt_folder in quant_question_types:
                        qt_path = sub_path / qt_folder
                        qt_path.mkdir(parents=True, exist_ok=True)
        
        print("Folder structure created.")
    
    def parse_main_page_from_url(self, url):
        """Parse the main forum page from a live URL."""
        print(f"Fetching and parsing URL: {url}")
        response = self.fetch_page(url)
        if not response:
            print("ERROR: Could not fetch the main page!")
            return {}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        questions_by_category = {}
        
        # Find all divs with class "item text" - these contain the question lists
        item_text_divs = soup.find_all('div', class_='item text')
        
        if not item_text_divs:
            print("ERROR: Could not find any 'item text' divs!")
            return {}
        
        print(f"Found {len(item_text_divs)} 'item text' divs")
        
        # Process each item text div
        for div_idx, item_div in enumerate(item_text_divs):
            # Find section header - look for various patterns
            section_header = None
            section_subcategory = None
            
            # Check for red/bold section headers
            section_span = item_div.find('span', style=re.compile('color.*#ff0000|color.*red', re.I))
            if section_span:
                section_text = section_span.get_text(strip=True)
                # Check for combined diagnostic test header
                if 'math diagnostic test' in section_text.lower() and 'verbal diagnostic test' in section_text.lower():
                    # This is a combined header, will handle separately
                    section_header = 'Math Diagnostic Test & Verbal Diagnostic Test'
                else:
                    for key in self.section_mapping.keys():
                        if key in section_text:
                            section_header = key
                            break
            
            # Check text content for section markers
            div_text = item_div.get_text()
            div_text_lower = div_text.lower()
            
            # Check for Quant Section subsections by looking for numbered lists and section names
            quant_subsections = [
                'arithmetic', 'exponents and roots', 'linear and quadratic equations',
                'functions, formulas, and sequences', 'inequalities and absolute values',
                'divisibility and primes', 'number properties', 'fractions and decimals',
                'percents', 'ratios', 'word problems', 'two variables word problems',
                'averages, weighted averages, median, and mode', 'standard deviation and normal distribution',
                'data interpretation', 'triangles', 'polygons and rectangular solids',
                'circles and cylinders', 'coordinate geometry', 'mixed geometry',
                'rates and work', 'probability, combinatorics, and overlapping sets',
                'advanced quant', 'verbal practice sections', 'verbal practice adaptive sections',
                'quant practice sections', 'quant practice adaptive sections'
            ]
            
            # Check if this div contains Quant Section subsection markers
            detected_quant_subsection = None
            div_text_normalized = re.sub(r'\s+', ' ', div_text_lower)
            for subsection in quant_subsections:
                if subsection in div_text_normalized:
                    detected_quant_subsection = self._map_quant_subsection(subsection.title())
                    break
            
            if not section_header:
                # Check for combined diagnostic test header
                if ('math diagnostic test' in div_text_lower and 'verbal diagnostic test' in div_text_lower) or \
                   ('math diagnostic test & verbal diagnostic test' in div_text_lower):
                    section_header = 'Math Diagnostic Test & Verbal Diagnostic Test'
                elif 'math diagnostic test' in div_text_lower or 'math diagnostic' in div_text_lower:
                    section_header = 'Math Diagnostic Test'
                elif 'verbal diagnostic test' in div_text_lower or 'verbal diagnostic' in div_text_lower:
                    section_header = 'Verbal Diagnostic Test'
                # Check for GRE section headers in text content (before other checks)
                elif any(key.lower() in div_text_lower for key in self.section_mapping.keys()):
                    # Find which GRE section this is
                    for key in self.section_mapping.keys():
                        if key.lower() in div_text_lower:
                            section_header = key
                            break
                elif 'the verbal section' in div_text_lower:
                    section_header = 'The Verbal Section'
                elif 'the quant section' in div_text_lower or detected_quant_subsection:
                    section_header = 'The Quant Section'
                    if detected_quant_subsection:
                        # Map to proper folder name
                        section_subcategory = self._map_quant_subsection(detected_quant_subsection)
                # Check for individual verbal subsections
                elif 'text completion' in div_text_lower and 'diagnostic' not in div_text_lower:
                    section_header = 'The Verbal Section'
                    section_subcategory = 'Text Completion'
                elif 'sentence equivalence' in div_text_lower and 'diagnostic' not in div_text_lower:
                    section_header = 'The Verbal Section'
                    section_subcategory = 'Sentence Equivalence'
                elif 'reading comprehension' in div_text_lower and 'diagnostic' not in div_text_lower:
                    section_header = 'The Verbal Section'
                    section_subcategory = 'Reading Comprehension'
                elif 'paragraph argument' in div_text_lower or 'passage paragraph' in div_text_lower:
                    section_header = 'The Verbal Section'
                    section_subcategory = 'Passage Paragraph Argument'
                elif 'verbal practice sections' in div_text_lower:
                    section_header = 'The Verbal Section'
                    section_subcategory = 'Verbal Practice Sections'
                elif 'verbal practice adaptive sections' in div_text_lower:
                    section_header = 'The Verbal Section'
                    section_subcategory = 'Verbal Practice Adaptive Sections'
                elif 'quant practice sections' in div_text_lower:
                    section_header = 'The Quant Section'
                    section_subcategory = 'Quant Practice Sections'
                elif 'quant practice adaptive sections' in div_text_lower:
                    section_header = 'The Quant Section'
                    section_subcategory = 'Quant Practice Adaptive Sections'
                # Check for GRE section headers in span
                elif section_span:
                    section_text = section_span.get_text(strip=True)
                    for key in self.section_mapping.keys():
                        if key in section_text:
                            section_header = key
                            break
            
            # Determine main category and map section to subcategory folder
            if section_header == 'Math Diagnostic Test & Verbal Diagnostic Test':
                # Handle combined header - process both diagnostic tests
                # First pass: Math Diagnostic Test
                main_category = 'Math Diagnostic Test'
                section_subcategory = None
                self._extract_questions_from_div(item_div, main_category, section_subcategory, questions_by_category, is_math_diagnostic=True)
                # Second pass: Verbal Diagnostic Test
                main_category = 'Verbal Diagnostic Test'
                section_subcategory = None
                self._extract_questions_from_div(item_div, main_category, section_subcategory, questions_by_category, is_verbal_diagnostic=True)
                continue
            elif section_header and 'Diagnostic Test' in section_header:
                main_category = section_header
                section_subcategory = None
            elif section_header == 'The Verbal Section':
                main_category = 'Verbal Section'
                # section_subcategory already set above if detected
            elif section_header == 'The Quant Section':
                main_category = 'Quantitative Section'
                # section_subcategory may be set above for practice sections
            elif section_header and section_header.startswith('GRE '):
                main_category = 'Quantitative Section'
                # Map section header to subcategory folder
                section_name = section_header.replace('GRE ', '')
                if section_name == 'Arithmetic':
                    section_subcategory = 'Arithmetic'
                elif 'Algebra' in section_name or 'Word Problems' in section_name:
                    section_subcategory = 'Word Problems'
                elif section_name == 'Geometry':
                    section_subcategory = 'Triangles'
                elif section_name == 'Data Analysis':
                    section_subcategory = 'Data Interpretation'
                else:
                    section_subcategory = None
            else:
                # Skip if no recognizable section
                if len(item_div.find_all('a', class_='postlink-local', href=True)) > 0:
                    print(f"  Warning: Div {div_idx+1} has {len(item_div.find_all('a', class_='postlink-local', href=True))} links but no recognizable section header")
                continue
            
            # Extract questions from this div
            if main_category:
                print(f"  Processing section: {section_header} -> {main_category} > {section_subcategory}")
                self._extract_questions_from_div(item_div, main_category, section_subcategory, questions_by_category)
        
        # Print summary
        total = sum(len(subcat_links) for subcats in questions_by_category.values() for subcat_links in subcats.values())
        print(f"\nExtracted {total} question links across {len(questions_by_category)} main categories")
        
        # Print breakdown by category
        for main_cat, subcats in questions_by_category.items():
            print(f"\n{main_cat}:")
            for subcat, links in subcats.items():
                print(f"  {subcat}: {len(links)} questions")
        
        return questions_by_category
    
    def _extract_questions_from_div(self, item_div, main_category, section_subcategory, questions_by_category, 
                                    is_math_diagnostic=False, is_verbal_diagnostic=False):
        """Extract questions from a div, handling diagnostic test filtering."""
        current_question_type = None
        current_topic_subsection = None
        all_elements = list(item_div.descendants)
        
        for i, element in enumerate(all_elements):
            # Check for subsection markers
            if hasattr(element, 'get_text'):
                text = element.get_text(strip=True).strip()
                
                # Check for question type markers (QCQ, PS, MAC, NE, DI, TC, SE, RC)
                question_type = self._detect_question_type_marker(text)
                if question_type:
                    current_question_type = question_type
                    current_topic_subsection = None
                
                # Check for special topic subsections
                topic_subsection = self._detect_topic_subsection(text)
                if topic_subsection:
                    current_topic_subsection = topic_subsection
                    if topic_subsection in self.subsection_mapping:
                        current_topic_subsection = self.subsection_mapping[topic_subsection]
            
            # Check for <ol> elements (ordered lists of questions)
            if hasattr(element, 'name') and element.name == 'ol':
                final_subcategory = self._determine_final_subcategory(
                    current_topic_subsection, current_question_type, section_subcategory,
                    main_category, is_math_diagnostic, is_verbal_diagnostic
                )
                
                if final_subcategory:
                    if main_category not in questions_by_category:
                        questions_by_category[main_category] = {}
                    if final_subcategory not in questions_by_category[main_category]:
                        questions_by_category[main_category][final_subcategory] = []
                    
                    # Extract links from this <ol>
                    links = element.find_all('a', class_='postlink-local', href=True)
                    for link in links:
                        href = link.get('href', '')
                        link_text = link.get_text(strip=True)

                        if href:
                            if not href.startswith('http'):
                                href = urljoin(self.base_url, href)
                            href = self._normalize_url(href)

                            if any(skip_term in href.lower() for skip_term in [
                                'gre-prep-whatsapp', 'gre-premium-quant-question-banks',
                                'how-to-achieve', 'gre-hard-and-tricky-verbal',
                                'gre-skill-builder-project', 'the-best-gre-books',
                                'gre-prep-club', 'forum/search', 'forum/viewforum'
                            ]):
                                continue

                            if not any(q['url'] == href for q in questions_by_category[main_category][final_subcategory]):
                                questions_by_category[main_category][final_subcategory].append({
                                    'url': href,
                                    'text': link_text or href,
                                    'question_type': current_question_type or '',
                                    'section': section_subcategory or ''
                                })
                    
                    if links:
                        print(f"    Extracted {len(links)} links from <ol> -> {main_category} > {final_subcategory}")
        
        # Also handle direct links (not in <ol>) after subsection markers
        current_question_type = None
        current_topic_subsection = None
        
        for i, element in enumerate(all_elements):
            # Update context from text elements
            if hasattr(element, 'get_text'):
                text = element.get_text(strip=True).strip()
                if text:
                    question_type = self._detect_question_type_marker(text)
                    if question_type:
                        current_question_type = question_type
                        current_topic_subsection = None
                    
                    topic_subsection = self._detect_topic_subsection(text)
                    if topic_subsection:
                        current_topic_subsection = topic_subsection
                        if topic_subsection in self.subsection_mapping:
                            current_topic_subsection = self.subsection_mapping[topic_subsection]
            
            # Handle direct links (not inside <ol>)
            if hasattr(element, 'name') and element.name == 'a':
                if 'postlink-local' in element.get('class', []):
                    href = element.get('href', '')
                    if href:
                        if not href.startswith('http'):
                            href = urljoin(self.base_url, href)
                        href = self._normalize_url(href)

                        if any(skip_term in href.lower() for skip_term in [
                            'gre-prep-whatsapp', 'gre-premium-quant-question-banks',
                            'how-to-achieve', 'gre-hard-and-tricky-verbal',
                            'gre-skill-builder-project', 'the-best-gre-books',
                            'gre-prep-club', 'forum/search', 'forum/viewforum'
                        ]):
                            continue

                        final_subcategory = self._determine_final_subcategory(
                            current_topic_subsection, current_question_type, section_subcategory,
                            main_category, is_math_diagnostic, is_verbal_diagnostic
                        )

                        if final_subcategory:
                            if main_category not in questions_by_category:
                                questions_by_category[main_category] = {}
                            if final_subcategory not in questions_by_category[main_category]:
                                questions_by_category[main_category][final_subcategory] = []

                            if not any(q['url'] == href for q in questions_by_category[main_category][final_subcategory]):
                                questions_by_category[main_category][final_subcategory].append({
                                    'url': href,
                                    'text': element.get_text(strip=True) or href,
                                    'question_type': current_question_type or '',
                                    'section': section_subcategory or ''
                                })
    
    def _determine_final_subcategory(self, current_topic_subsection, current_question_type, section_subcategory,
                                     main_category, is_math_diagnostic=False, is_verbal_diagnostic=False, 
                                     detected_question_type_from_content=None):
        """Determine the final subcategory to use for a question.
        
        For Quantitative Section subsections, creates question type subfolders.
        For Diagnostic Tests, uses question type directly.
        """
        # Filter by diagnostic test type if applicable
        if is_math_diagnostic:
            # Only include math question types
            if current_question_type and 'Verbal' in current_question_type:
                return None
        elif is_verbal_diagnostic:
            # Only include verbal question types
            if current_question_type and 'Verbal' not in current_question_type and 'Text Completion' not in current_question_type and \
               'Sentence Equivalence' not in current_question_type and 'Reading Comprehension' not in current_question_type:
                return None
        
        # For Diagnostic Tests, use question type as folder directly
        if 'Diagnostic Test' in main_category:
            # Use detected type from content if available, otherwise use marker type
            question_type = detected_question_type_from_content or current_question_type
            if question_type:
                return question_type
            return current_question_type if current_question_type else None
        
        # For Quantitative Section: use subsection directly (question type subfolders created during save)
        if main_category == 'Quantitative Section':
            # Priority: topic_subsection > section_subcategory
            final_subsection = current_topic_subsection or section_subcategory
            if final_subsection:
                return final_subsection
            # No subsection, use question type if available (fallback)
            question_type = detected_question_type_from_content or current_question_type
            return question_type if question_type else None
        
        # For Verbal Section: use subsection directly (question types are already the subsections)
        if main_category == 'Verbal Section':
            if current_topic_subsection:
                return current_topic_subsection
            elif section_subcategory:
                return section_subcategory
            elif current_question_type:
                return current_question_type
        
        # Default: Priority: topic_subsection > question_type > section_subcategory
        if current_topic_subsection:
            return current_topic_subsection
        elif current_question_type:
            return current_question_type
        elif section_subcategory:
            return section_subcategory
        
        return None
    
    def _detect_question_type_marker(self, text):
        """Detect question type markers like 'QCQ -', 'PS -', etc."""
        text_lower = text.lower().strip()
        
        # Diagnostic Test subsections
        if text_lower.startswith('qcq') or text_lower == 'qcq -':
            return 'Quantitative Comparison (QCQ)'
        if text_lower.startswith('ps') and ('-' in text_lower or len(text_lower) <= 5):
            return 'Problem Solving (PS)'
        if text_lower.startswith('mac') or text_lower == 'mac -':
            return 'Multiple Answer Choices (MAC)'
        if text_lower.startswith('ne') and ('-' in text_lower or len(text_lower)  <= 5):
            return 'Numeric Entry (NE)'
        if text_lower.startswith('di') and ('-' in text_lower or len(text_lower) <= 5):
            return 'Data Interpretation (DI)'
        
        # Verbal Diagnostic Test subsections
        if text_lower.startswith('tc') and ('-' in text_lower or len(text_lower) <= 5):
            return 'Text Completion (TC)'
        if text_lower.startswith('se') and ('-' in text_lower or len(text_lower) <= 5):
            return 'Sentence Equivalence (SE)'
        if text_lower.startswith('rc') and ('-' in text_lower or len(text_lower) <= 5):
            return 'Reading Comprehension (RC)'
        
        return None
    
    def _map_quant_subsection(self, subsection_name):
        """Map Quant Section subsection name to folder name."""
        mapping = {
            'Arithmetic': 'Arithmetic',
            'Exponents And Roots': 'Exponents and Roots',
            'Linear And Quadratic Equations': 'Linear and Quadratic Equations',
            'Functions, Formulas, And Sequences': 'Functions, Formulas, and Sequences',
            'Inequalities And Absolute Values': 'Inequalities and Absolute Values',
            'Divisibility And Primes': 'Divisibility and Primes',
            'Number Properties': 'Number Properties',
            'Fractions And Decimals': 'Fractions and Decimals',
            'Percents': 'Percents',
            'Ratios': 'Ratios',
            'Word Problems': 'Word Problems',
            'Two Variables Word Problems': 'Two Variables Word Problems',
            'Averages, Weighted Averages, Median, And Mode': 'Averages, Weighted Averages, Median, and Mode',
            'Standard Deviation And Normal Distribution': 'Standard Deviation and Normal Distribution',
            'Data Interpretation': 'Data Interpretation',
            'Triangles': 'Triangles',
            'Polygons And Rectangular Solids': 'Polygons and Rectangular Solids',
            'Circles And Cylinders': 'Circles and Cylinders',
            'Coordinate Geometry': 'Coordinate Geometry',
            'Mixed Geometry': 'Mixed Geometry',
            'Rates And Work': 'Rates and Work',
            'Probability, Combinatorics, And Overlapping Sets': 'Probability, Combinatorics, and Overlapping Sets',
            'Advanced Quant': 'Advanced Quant',
            'Verbal Practice Sections': 'Verbal Practice Sections',
            'Verbal Practice Adaptive Sections': 'Verbal Practice Adaptive Sections',
            'Quant Practice Sections': 'Quant Practice Sections',
            'Quant Practice Adaptive Sections': 'Quant Practice Adaptive Sections'
        }
        return mapping.get(subsection_name, subsection_name)
    
    def _detect_topic_subsection(self, text):
        """Detect special topic subsections like 'Graphs & Illustrations', 'Overlapping Sets', etc."""
        text_lower = text.lower().strip()
        
        # Check for special subsections (case-insensitive)
        for key in self.subsection_mapping.keys():
            if key.lower() in text_lower and len(text_lower) < 100:
                return key
        
        return None
    
    def fetch_page(self, url, retries=3):
        """Fetch a webpage with retry logic."""
        for attempt in range(retries):
            try:
                headers = self.session.headers.copy()
                headers.setdefault('Referer', self.base_url)
                response = self.session.get(url, timeout=30, allow_redirects=True, headers=headers)
                if response.status_code == 400 and attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"Error fetching {url}: {e}")
                return None
        return None
    
    def extract_question_content(self, url):
        """Extract question content from a question page."""
        normalized_url = self._normalize_url(url)
        response = self.fetch_page(normalized_url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        question_data = {
            'question': '',
            'answer_choices': [],
            'correct_answer': '',
            'explanation': '',
            'question_type': '',
            'source_url': normalized_url
        }
        
        # Find the first post (question post)
        first_post = None
        
        # Strategy 1: Find div with class 'item text' inside a post
        post_wrappers = soup.find_all('div', class_=re.compile('post-wrapper|post', re.I))
        for post_wrapper in post_wrappers:
            item_text = post_wrapper.find('div', class_='item text')
            if item_text:
                first_post = item_text
                break
        
        # Strategy 2: Find div with class containing 'content' or 'postbody' in first post
        if not first_post:
            for post_wrapper in post_wrappers[:1]:
                content_div = post_wrapper.find('div', class_=re.compile('content|postbody|item.*text', re.I))
                if content_div:
                    first_post = content_div
                    break
        
        # Strategy 3: Find by itemprop
        if not first_post:
            first_post = soup.find('div', itemprop='text')
        
        # Strategy 4: Find first post div with substantial content
        if not first_post:
            for post_wrapper in post_wrappers[:1]:
                content_divs = post_wrapper.find_all('div')
                for div in content_divs:
                    text = div.get_text(strip=True)
                    if len(text) > 200 and 'forum' not in text.lower()[:100] and 'navigation' not in text.lower()[:100]:
                        first_post = div
                        break
                if first_post:
                    break
        
        if first_post:
            # Extract question text
            question_text = self._extract_question_text(first_post)
            question_data['question'] = question_text
            
            # Extract answer choices if present
            answer_choices = self._extract_answer_choices(first_post)
            question_data['answer_choices'] = answer_choices
            
            # Extract correct answer from entire page
            correct_answer = self._extract_correct_answer(first_post, soup)
            question_data['correct_answer'] = correct_answer
            
            # Extract explanation from entire page
            explanation = self._extract_explanation(first_post, soup)
            question_data['explanation'] = explanation
            
            # Determine question type from content
            detected_type = self._determine_question_type(question_text, answer_choices)
            question_data['question_type'] = detected_type
        else:
            # Fallback: extract from body but filter out navigation
            body_text = soup.find('body')
            if body_text:
                main_content = body_text.find('div', id=re.compile('content|main|post', re.I))
                if main_content:
                    question_data['question'] = main_content.get_text(separator='\n', strip=True)[:2000]
                else:
                    question_data['question'] = body_text.get_text(separator='\n', strip=True)[:2000]
        
        return question_data
    
    def _extract_question_text(self, element):
        """Extract the question text from an element."""
        text_element = BeautifulSoup(str(element), 'html.parser')
        
        # Remove spoiler tags and answer sections
        for tag in text_element.find_all(['div', 'span'], class_=re.compile('spoiler|answer|explanation', re.I)):
            tag.decompose()
        
        text = text_element.get_text(separator='\n', strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _extract_answer_choices(self, element):
        """Extract answer choices from an element."""
        choices = []
        text = element.get_text()
        
        # Try to find choices by pattern (A), (B), etc.
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
        # Look for OA (Official Answer) tags
        oa_tag = soup.find(string=re.compile(r'OA[:\s]*[A-E]', re.I))
        if oa_tag:
            match = re.search(r'OA[:\s]*([A-E])', oa_tag, re.I)
            if match:
                return match.group(1)
        
        # Look for spoiler tags
        spoiler = soup.find(['div', 'span'], class_=re.compile('spoiler', re.I))
        if spoiler:
            answer_text = spoiler.get_text(strip=True)
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
        
        # Look for expert replies
        expert_posts = soup.find_all('div', class_=re.compile('expert|solution', re.I))
        if expert_posts:
            explanations = []
            for post in expert_posts:
                text = post.get_text(separator='\n', strip=True)
                if len(text) > 100:
                    explanations.append(text)
            if explanations:
                return '\n\n'.join(explanations)
        
        # Look for posts by experts
        expert_authors = soup.find_all(['div', 'span'], class_=re.compile('author|username', re.I))
        for author_elem in expert_authors:
            author_text = author_elem.get_text(strip=True)
            if 'expert' in author_text.lower():
                post = author_elem.find_parent('div', class_=re.compile('post', re.I))
                if post:
                    content = post.find('div', class_=re.compile('content|postbody', re.I))
                    if content:
                        text = content.get_text(separator='\n', strip=True)
                        if len(text) > 100:
                            return text
        
        # Look for second post
        all_posts = soup.find_all('div', class_=re.compile('post', re.I))
        if len(all_posts) > 1:
            second_post = all_posts[1]
            content = second_post.find('div', class_=re.compile('content|postbody', re.I))
            if content:
                text = content.get_text(separator='\n', strip=True)
                if len(text) > 150 and 'explanation' not in text.lower()[:50]:
                    return text
        
        return ''
    
    def _determine_question_type(self, question_text, answer_choices):
        """Determine the question type based on content. Returns standardized question type names."""
        text_lower = question_text.lower()
        
        # Quantitative Comparison - has Quantity A and Quantity B
        if 'quantity a' in text_lower and 'quantity b' in text_lower:
            return 'Quantitative Comparison (QCQ)'
        
        # Multiple Answer Choices - select all or select one or more, or more than 5 choices
        if 'select all' in text_lower or 'select one or more' in text_lower or 'mark all' in text_lower:
            return 'Multiple Answer Choices (MAC)'
        if len(answer_choices) > 5:
            return 'Multiple Answer Choices (MAC)'
        
        # Numeric Entry - no answer choices and asks for numeric input
        if not answer_choices and ('enter' in text_lower or 'numeric' in text_lower or 'your answer' in text_lower):
            return 'Numeric Entry (NE)'
        
        # Problem Solving - standard multiple choice with one answer (typically 5 choices)
        if answer_choices and len(answer_choices) <= 5:
            # Check if it's not explicitly a multi-select question
            if 'select all' not in text_lower and 'select one or more' not in text_lower:
                return 'Problem Solving (PS)'
        
        # Verbal question types
        if 'blank' in text_lower or 'complete' in text_lower:
            return 'Text Completion'
        if 'sentence' in text_lower and 'equivalence' in text_lower:
            return 'Sentence Equivalence'
        if 'passage' in text_lower or 'according to the passage' in text_lower:
            return 'Reading Comprehension'
        
        # Default fallback
        if answer_choices:
            return 'Problem Solving (PS)'
        
        return 'Unknown'
    
    def sanitize_filename(self, text, max_length=100):
        """Generate a filename from question text."""
        if not text or not isinstance(text, str):
            return 'question'
        
        words = text.split()[:8]
        filename = '_'.join(words)
        
        filename = re.sub(r'[^\w\s-]', '', filename)
        filename = re.sub(r'[-\s]+', '_', filename)
        
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        filename = filename.strip('_').lower()
        
        return filename if filename else 'question'
    
    def save_question(self, question_data, category_path, base_filename):
        """Save a question as a JSON file."""
        # Ensure directory exists
        category_path.mkdir(parents=True, exist_ok=True)
        
        filename = self.sanitize_filename(base_filename)
        filepath = category_path / f"{filename}.json"
        
        # Handle collisions
        counter = 1
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
    parser = argparse.ArgumentParser(description="Extract GRE questions from GRE Prep Club forum")
    parser.add_argument('--main-category', dest='main_category', help='Main category to extract (e.g. "Quantitative Section")')
    parser.add_argument('--subcategory', dest='subcategory', help='Subcategory to extract (e.g. "Percents")')
    parser.add_argument('--url', dest='url', default="https://gre.myprepclub.com/forum/the-5-lb-book-of-gre-practice-problems-34935.html#p119768",
                        help='Source forum URL to parse')
    parser.add_argument('--output-dir', dest='output_dir', default='.', help='Output directory for saved questions')
    args = parser.parse_args()

    if args.subcategory and not args.main_category:
        parser.error('--subcategory requires --main-category to be specified')

    main_url = args.url

    extractor = GREQuestionExtractor(main_url, output_dir=args.output_dir)

    if args.main_category:
        print(f"Targeting extraction for {args.main_category} > {args.subcategory or 'ALL subsections'}")

    # Step 1: Clean up question files for the target selection
    extractor.cleanup_old_questions(target_main_category=args.main_category, target_subcategory=args.subcategory)

    # Step 2: Ensure folder structure exists
    extractor.create_folder_structure()

    # Step 3: Parse main page from URL
    questions_by_category = extractor.parse_main_page_from_url(main_url)

    if not questions_by_category:
        print("ERROR: No questions found! Exiting.")
        return

    total_questions = 0
    processed_any = False

    for main_cat, subcats in questions_by_category.items():
        if args.main_category and main_cat != args.main_category:
            continue

        for subcat, question_links in subcats.items():
            if args.subcategory and subcat != args.subcategory:
                continue

            processed_any = True
            saved_questions = []

            print(f"\nProcessing {main_cat} > {subcat} ({len(question_links)} questions)...")

            for idx, q_link in enumerate(question_links, 1):
                print(f"  [{idx}/{len(question_links)}] Extracting: {q_link['url']}")

                question_data = extractor.extract_question_content(q_link['url'])
                if question_data and question_data['question']:
                    detected_question_type = question_data.get('question_type', '')

                    if main_cat == 'Quantitative Section':
                        subsection = subcat
                        question_type = detected_question_type or 'Problem Solving (PS)'

                        if 'Quantitative Comparison' in question_type or question_type == 'QCQ':
                            question_type_folder = 'Quantitative Comparison (QCQ)'
                        elif 'Multiple Answer Choices' in question_type or question_type == 'MAC':
                            question_type_folder = 'Multiple Answer Choices (MAC)'
                        elif 'Numeric Entry' in question_type or question_type == 'NE':
                            question_type_folder = 'Numeric Entry (NE)'
                        elif 'Data Interpretation' in question_type or question_type == 'DI':
                            question_type_folder = 'Data Interpretation (DI)'
                        else:
                            question_type_folder = 'Problem Solving (PS)'

                        category_path = extractor.output_dir / main_cat / subsection / question_type_folder
                        final_category = f"{subsection} > {question_type_folder}"
                    else:
                        category_path = extractor.output_dir / main_cat / subcat
                        final_category = subcat

                    question_data['main_category'] = main_cat

                    if main_cat == 'Quantitative Section':
                        question_data['subsection'] = subsection
                        question_data['question_type'] = question_type_folder
                        question_data['category'] = final_category
                        question_data['detected_type'] = detected_question_type
                    else:
                        question_data['category'] = final_category
                        question_data['question_type'] = detected_question_type

                    filename_base = question_data['question'] or q_link['text'] or 'question'
                    filepath = extractor.save_question(question_data, category_path, filename_base)
                    saved_questions.append({
                        'filename': filepath.name,
                        'url': q_link['url'],
                        'question_preview': question_data['question'][:100],
                        'question_type': detected_question_type
                    })
                    total_questions += 1
                    time.sleep(1)
                else:
                    print("    Failed to extract question content")

            if main_cat == 'Quantitative Section':
                questions_by_type = {}
                for q in saved_questions:
                    qt = q.get('question_type', 'Problem Solving (PS)')
                    questions_by_type.setdefault(qt, []).append(q)

                for qt, qt_questions in questions_by_type.items():
                    if 'Quantitative Comparison' in qt or qt == 'QCQ':
                        qt_folder = 'Quantitative Comparison (QCQ)'
                    elif 'Multiple Answer Choices' in qt or qt == 'MAC':
                        qt_folder = 'Multiple Answer Choices (MAC)'
                    elif 'Numeric Entry' in qt or qt == 'NE':
                        qt_folder = 'Numeric Entry (NE)'
                    elif 'Data Interpretation' in qt or qt == 'DI':
                        qt_folder = 'Data Interpretation (DI)'
                    else:
                        qt_folder = 'Problem Solving (PS)'

                    qt_category_path = extractor.output_dir / main_cat / subcat / qt_folder
                    if qt_questions:
                        extractor.create_index(qt_category_path, qt_questions)
            else:
                if saved_questions:
                    category_path = extractor.output_dir / main_cat / subcat
                    extractor.create_index(category_path, saved_questions)

    if not processed_any:
        print("WARNING: No categories matched the provided selection. Nothing was extracted.")
    else:
        print(f"\n\nExtraction complete! Total questions extracted: {total_questions}")


if __name__ == "__main__":
    main()
