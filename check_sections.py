"""Check which sections are found in the HTML file based on sections.txt."""

from bs4 import BeautifulSoup
import re
from pathlib import Path

# Parse sections.txt to get expected sections
def parse_sections_file():
    """Parse sections.txt to extract expected sections and subsections."""
    sections_file = Path('sections.txt')
    if not sections_file.exists():
        print("ERROR: sections.txt not found!")
        return {}
    
    expected_sections = {
        'Math Diagnostic Test & Verbal Diagnostic Test': {
            'type': 'main',
            'subsections': []
        },
        'Math Diagnostic Test': {
            'type': 'main',
            'subsections': []
        },
        'Verbal Diagnostic Test': {
            'type': 'main',
            'subsections': []
        },
        'The Verbal Section': {
            'type': 'main',
            'subsections': [
                'Text Completion',
                'Sentence Equivalence',
                'Reading Comprehension',
                'Passage Paragraph Argument'
            ]
        },
        'The Quant Section': {
            'type': 'main',
            'subsections': [
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
                'Verbal Practice Sections',
                'Verbal Practice Adaptive Sections',
                'Quant Practice Sections',
                'Quant Practice Adaptive Sections'
            ]
        }
    }
    
    return expected_sections


def format_quant_subsection_name(name: str) -> str:
    """Return a consistently formatted quant subsection name."""
    mapping = {
        'functions, formulas, and sequences': 'Functions, Formulas, and Sequences',
        'inequalities and absolute values': 'Inequalities and Absolute Values',
        'divisibility and primes': 'Divisibility and Primes',
        'fractions and decimals': 'Fractions and Decimals',
        'exponents and roots': 'Exponents and Roots',
        'linear and quadratic equations': 'Linear and Quadratic Equations',
        'two variables word problems': 'Two Variables Word Problems',
        'averages, weighted averages, median, and mode': 'Averages, Weighted Averages, Median, and Mode',
        'standard deviation and normal distribution': 'Standard Deviation and Normal Distribution',
        'polygons and rectangular solids': 'Polygons and Rectangular Solids',
        'circles and cylinders': 'Circles and Cylinders',
        'coordinate geometry': 'Coordinate Geometry',
        'mixed geometry': 'Mixed Geometry',
        'rates and work': 'Rates and Work',
        'probability, combinatorics, and overlapping sets': 'Probability, Combinatorics, and Overlapping Sets',
    }
    return mapping.get(name, name.title())

def check_sections_in_html():
    """Check which expected sections are found in the HTML."""
    html_file = Path('gre_base.html')
    if not html_file.exists():
        print("ERROR: gre_base.html not found!")
        return
    
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    expected_sections = parse_sections_file()
    
    divs = soup.find_all('div', class_='item text')
    print(f"Total item text divs: {len(divs)}\n")
    
    # Track found sections
    found_sections = {}
    found_subsections = {}
    all_quant_subsections_found = set()
    
    # Quant section subsections list for detection
    quant_subsections = [
        'arithmetic', 'exponents and roots', 'linear and quadratic equations',
        'functions, formulas, and sequences', 'inequalities and absolute values',
        'divisibility and primes', 'number properties', 'fractions and decimals',
        'percents', 'ratios', 'word problems', 'two variables word problems',
        'averages, weighted averages, median, and mode',
        'standard deviation and normal distribution',
        'data interpretation', 'triangles', 'polygons and rectangular solids',
        'circles and cylinders', 'coordinate geometry', 'mixed geometry',
        'rates and work', 'probability, combinatorics, and overlapping sets',
        'advanced quant', 'verbal practice sections', 'verbal practice adaptive sections',
        'quant practice sections', 'quant practice adaptive sections'
    ]
    
    for i, div in enumerate(divs):
        div_text = div.get_text()
        div_text_lower = div_text.lower()
        div_text_normalized = re.sub(r'\s+', ' ', div_text_lower).strip()

        # Track all quant subsections present in this div (for global accounting)
        for subsection in quant_subsections:
            if subsection.lower() in div_text_normalized:
                all_quant_subsections_found.add(format_quant_subsection_name(subsection))

        # Find section header
        section_header = None
        section_span = div.find('span', style=re.compile('color.*#ff0000|color.*red', re.I))
        if section_span:
            section_header = section_span.get_text(strip=True)

        # Determine marker presence
        verbal_subsections_list = [
            'Text Completion',
            'Sentence Equivalence',
            'Reading Comprehension',
            'Passage Paragraph Argument'
        ]
        verbal_markers = [marker.lower() for marker in verbal_subsections_list]
        quant_markers = [sub.lower() for sub in quant_subsections]

        verbal_marker_present = any(marker in div_text_normalized for marker in verbal_markers)
        quant_marker_present = any(marker in div_text_normalized for marker in quant_markers)

        # Determine section header via markers if not explicitly provided
        if not section_header:
            if ('math diagnostic test' in div_text_normalized and 'verbal diagnostic test' in div_text_normalized) or \
               ('math diagnostic test & verbal diagnostic test' in div_text_normalized):
                section_header = 'Math Diagnostic Test & Verbal Diagnostic Test'
            elif 'math diagnostic test' in div_text_normalized or 'math diagnostic' in div_text_normalized:
                section_header = 'Math Diagnostic Test'
            elif 'verbal diagnostic test' in div_text_normalized or 'verbal diagnostic' in div_text_normalized:
                section_header = 'Verbal Diagnostic Test'
            elif 'the verbal section' in div_text_normalized:
                section_header = 'The Verbal Section'
            elif 'the quant section' in div_text_normalized:
                section_header = 'The Quant Section'

        if not section_header:
            if verbal_marker_present and not quant_marker_present:
                section_header = 'The Verbal Section'
            elif quant_marker_present:
                section_header = 'The Quant Section'

        section_lower = section_header.lower() if section_header else ''
        is_verbal_context = 'the verbal section' in section_lower
        is_quant_context = 'the quant section' in section_lower or section_lower.startswith('gre ')

        # Detect subsections based on context
        detected_verbal_subsections = []
        detected_quant_subsections = []

        if is_verbal_context or (not section_header and verbal_marker_present and not quant_marker_present):
            for sub in verbal_subsections_list:
                if sub.lower() in div_text_normalized:
                    detected_verbal_subsections.append(sub)

        if is_quant_context or (not section_header and quant_marker_present and not is_verbal_context):
            for subsection in quant_subsections:
                subsection_lower = subsection.lower()
                if subsection_lower in div_text_normalized:
                    subsection_title = format_quant_subsection_name(subsection)
                    detected_quant_subsections.append(subsection_title)

        if not section_header:
            if detected_verbal_subsections and not detected_quant_subsections:
                section_header = 'The Verbal Section'
                section_lower = section_header.lower()
                is_verbal_context = True
            elif detected_quant_subsections:
                section_header = 'The Quant Section'
                section_lower = section_header.lower()
                is_quant_context = True

        detected_subsections = detected_verbal_subsections + detected_quant_subsections
        
        # Check if this matches an expected section
        matched_section = None
        
        # First check section_header if we have one
        if section_header:
            for expected_section in expected_sections.keys():
                if expected_section.lower() in section_header.lower():
                    matched_section = expected_section
                    break
        
        # If no match from header, check div text content
        if not matched_section:
            for expected_section in expected_sections.keys():
                if expected_section.lower() in div_text_normalized:
                    matched_section = expected_section
                    break
        
        # Count links
        links = div.find_all('a', class_='postlink-local', href=True)
        link_count = len(links)
        
        # Record findings - only record subsections that belong to the matched section
        if matched_section:
            if matched_section not in found_sections:
                found_sections[matched_section] = {
                    'divs': [],
                    'total_links': 0,
                    'subsections': set()
                }
            found_sections[matched_section]['divs'].append(i + 1)
            found_sections[matched_section]['total_links'] += link_count
            
            # Only add subsections that belong to this section
            if matched_section == 'The Verbal Section':
                for subsec in detected_verbal_subsections:
                    found_sections[matched_section]['subsections'].add(subsec)
            elif matched_section == 'The Quant Section':
                for subsec in detected_quant_subsections:
                    found_sections[matched_section]['subsections'].add(subsec)
            else:
                for subsec in detected_subsections:
                    found_sections[matched_section]['subsections'].add(subsec)
        
        # Print details for each div
        print(f"=== Div {i+1} ===")
        if section_header:
            print(f"Section header: {section_header}")
        if matched_section:
            print(f"[FOUND] Matched expected section: {matched_section}")
        else:
            print("[MISSING] No matching expected section")
            div_preview = div_text[:200].replace('\n', ' ')
            print(f"  Preview: {div_preview}")
        
        print(f"Sections found: {matched_section or 'None'}")
        print(f"Question links: {link_count}")
        if detected_subsections:
            print(f"Detected subsections: {', '.join(detected_subsections)}")
        print()
    
    # Ensure The Quant Section includes all detected quant subsections
    if all_quant_subsections_found:
        if 'The Quant Section' not in found_sections:
            found_sections['The Quant Section'] = {
                'divs': [],
                'total_links': 0,
                'subsections': set()
            }
        found_sections['The Quant Section']['subsections'].update(all_quant_subsections_found)

    # If combined diagnostic test found, mark individual ones as found too (only if not already found separately)
    if 'Math Diagnostic Test & Verbal Diagnostic Test' in found_sections:
        combined_info = found_sections['Math Diagnostic Test & Verbal Diagnostic Test']
        if 'Math Diagnostic Test' not in found_sections:
            found_sections['Math Diagnostic Test'] = {
                'divs': combined_info['divs'].copy(),
                'total_links': combined_info['total_links'],
                'subsections': combined_info['subsections'].copy()
            }
        if 'Verbal Diagnostic Test' not in found_sections:
            found_sections['Verbal Diagnostic Test'] = {
                'divs': combined_info['divs'].copy(),
                'total_links': combined_info['total_links'],
                'subsections': combined_info['subsections'].copy()
            }
    
    # Print summary
    print("=" * 80)
    print("SUMMARY: Expected Sections Found")
    print("=" * 80)
    
    for section_name, section_info in expected_sections.items():
        if section_name in found_sections:
            found_info = found_sections[section_name]
            print(f"\n[FOUND] {section_name}")
            print(f"  Found in divs: {found_info['divs']}")
            print(f"  Total question links: {found_info['total_links']}")
            
            # Check subsections
            expected_subsections = section_info.get('subsections', [])
            found_subsections_list = list(found_info['subsections'])
            
            if expected_subsections:
                print(f"  Expected subsections: {len(expected_subsections)}")
                print(f"  Found subsections: {len(found_subsections_list)}")
                
                # Check which subsections were found
                for subsec in expected_subsections:
                    if subsec in found_subsections_list:
                        print(f"    [FOUND] {subsec}")
                    else:
                        print(f"    [MISSING] {subsec} (NOT FOUND)")
                
                # Check for unexpected subsections
                unexpected = set(found_subsections_list) - set(expected_subsections)
                if unexpected:
                    print(f"  Unexpected subsections found: {', '.join(unexpected)}")
        else:
            print(f"\n[MISSING] {section_name} (NOT FOUND)")
    
    print("\n" + "=" * 80)
    print("Overall Statistics")
    print("=" * 80)
    total_expected = len(expected_sections)
    total_found = len(found_sections)
    print(f"Expected sections: {total_expected}")
    print(f"Found sections: {total_found}")
    print(f"Missing sections: {total_expected - total_found}")
    
    if total_found < total_expected:
        print("\nMissing sections:")
        for section_name in expected_sections.keys():
            if section_name not in found_sections:
                print(f"  - {section_name}")

if __name__ == "__main__":
    check_sections_in_html()
