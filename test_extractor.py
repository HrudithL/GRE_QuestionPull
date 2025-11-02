"""
Test script to verify the GRE question extractor works correctly.
Tests each step of the extraction process.
"""

import os
import json
from pathlib import Path
from extract_gre_questions import GREQuestionExtractor


def test_load_initial_page():
    """Test 1: Load the initial HTML page."""
    print("=" * 80)
    print("TEST 1: Loading initial HTML page")
    print("=" * 80)
    
    html_file = "gre_base.html"
    if not os.path.exists(html_file):
        print(f"[FAILED]: HTML file {html_file} not found!")
        return False
    
    print(f"[PASSED] HTML file {html_file} found")
    return True


def test_find_question_lists():
    """Test 2: Find the content that contains lists of questions."""
    print("\n" + "=" * 80)
    print("TEST 2: Finding question lists in HTML")
    print("=" * 80)
    
    from bs4 import BeautifulSoup
    
    html_file = "gre_base.html"
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    item_text_divs = soup.find_all('div', class_='item text')
    
    if not item_text_divs:
        print("[FAILED]: Could not find any 'item text' divs!")
        return False
    
    print(f"[PASSED]: Found {len(item_text_divs)} 'item text' divs")
    
    # Check if they contain question links
    total_links = 0
    for div in item_text_divs:
        links = div.find_all('a', class_='postlink-local', href=True)
        total_links += len(links)
    
    print(f"[PASSED]: Found {total_links} question links total")
    return True


def test_parse_sections():
    """Test 3: Parse sections and extract question links."""
    print("\n" + "=" * 80)
    print("TEST 3: Parsing sections and extracting question links")
    print("=" * 80)
    
    extractor = GREQuestionExtractor("https://gre.myprepclub.com")
    questions_by_category = extractor.parse_main_page_from_file("gre_base.html")
    
    if not questions_by_category:
        print("[FAILED]: No questions extracted!")
        return False
    
    total = sum(len(subcat_links) for subcats in questions_by_category.values() for subcat_links in subcats.values())
    print(f"[PASSED]: Extracted {total} question links")
    
    # Print category breakdown
    for main_cat, subcats in questions_by_category.items():
        print(f"\n  {main_cat}:")
        for subcat, links in subcats.items():
            print(f"    {subcat}: {len(links)} questions")
    
    return True, questions_by_category


def test_extract_single_question():
    """Test 4: Extract a single question from a link."""
    print("\n" + "=" * 80)
    print("TEST 4: Extracting a single question")
    print("=" * 80)
    
    # Use a sample question URL
    test_url = "https://gre.myprepclub.com/forum/no-of-factors-of-80-greater-than-35998.html#p124363"
    
    extractor = GREQuestionExtractor("https://gre.myprepclub.com")
    question_data = extractor.extract_question_content(test_url)
    
    if not question_data:
        print(f"[FAILED]: Could not extract question from {test_url}")
        return False
    
    if not question_data.get('question'):
        print(f"[FAILED]: Question text is empty")
        return False
    
    print(f"[PASSED]: Extracted question content")
    print(f"  Question preview: {question_data['question'][:100]}...")
    print(f"  Answer choices: {len(question_data['answer_choices'])}")
    print(f"  Correct answer: {question_data['correct_answer']}")
    print(f"  Explanation length: {len(question_data['explanation'])} chars")
    print(f"  Question type: {question_data['question_type']}")
    
    return True, question_data


def test_save_question():
    """Test 5: Save question to JSON file."""
    print("\n" + "=" * 80)
    print("TEST 5: Saving question to JSON file")
    print("=" * 80)
    
    extractor = GREQuestionExtractor("https://gre.myprepclub.com", output_dir="test_output")
    
    # Create test category folder
    test_category_path = Path("test_output") / "Quantitative Section" / "Arithmetic"
    test_category_path.mkdir(parents=True, exist_ok=True)
    
    # Create sample question data
    test_question = {
        'question': 'What is 2 + 2?',
        'answer_choices': ['3', '4', '5', '6'],
        'correct_answer': 'B',
        'explanation': '2 + 2 = 4',
        'question_type': 'Problem Solving',
        'category': 'Arithmetic',
        'main_category': 'Quantitative Section',
        'source_url': 'https://test.com'
    }
    
    filename_base = test_question['question']
    filepath = extractor.save_question(test_question, test_category_path, filename_base)
    
    if not filepath.exists():
        print(f"[FAILED]: File was not created at {filepath}")
        return False
    
    # Verify JSON content
    with open(filepath, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    
    if saved_data['question'] != test_question['question']:
        print(f"[FAILED]: Question text mismatch")
        return False
    
    print(f"[PASSED]: Question saved to {filepath}")
    print(f"  File size: {filepath.stat().st_size} bytes")
    
    return True


def test_full_extraction():
    """Test 6: Full extraction of a small subset."""
    print("\n" + "=" * 80)
    print("TEST 6: Full extraction (limited to 3 questions)")
    print("=" * 80)
    
    extractor = GREQuestionExtractor("https://gre.myprepclub.com", output_dir="test_output")
    extractor.create_folder_structure()
    
    # Parse HTML
    questions_by_category = extractor.parse_main_page_from_file("gre_base.html")
    
    if not questions_by_category:
        print("[FAILED]: Could not parse questions")
        return False
    
    # Extract first 3 questions from first category
    extracted_count = 0
    max_questions = 3
    
    for main_cat, subcats in questions_by_category.items():
        for subcat, question_links in subcats.items():
            if extracted_count >= max_questions:
                break
            
            category_path = Path("test_output") / main_cat / subcat
            saved_questions = []
            
            print(f"\nProcessing {main_cat} > {subcat}...")
            
            for q_link in question_links[:max_questions - extracted_count]:
                print(f"  Extracting: {q_link['url']}")
                
                question_data = extractor.extract_question_content(q_link['url'])
                if question_data and question_data['question']:
                    question_data['category'] = subcat
                    question_data['main_category'] = main_cat
                    
                    filename_base = question_data['question'] or q_link['text'] or 'question'
                    filepath = extractor.save_question(question_data, category_path, filename_base)
                    saved_questions.append({
                        'filename': filepath.name,
                        'url': q_link['url'],
                        'question_preview': question_data['question'][:100]
                    })
                    extracted_count += 1
                    
                    if extracted_count >= max_questions:
                        break
            
            if saved_questions:
                extractor.create_index(category_path, saved_questions)
            
            if extracted_count >= max_questions:
                break
        
        if extracted_count >= max_questions:
            break
    
    if extracted_count == 0:
        print("[FAILED]: No questions were extracted")
        return False
    
    print(f"\n[PASSED]: Successfully extracted and saved {extracted_count} questions")
    
    # Verify files exist
    test_dir = Path("test_output")
    json_files = list(test_dir.rglob("*.json"))
    print(f"[PASSED]: Found {len(json_files)} JSON files in test_output directory")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GRE QUESTION EXTRACTOR TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Test 1: Load HTML
    results.append(("Load HTML", test_load_initial_page()))
    
    # Test 2: Find question lists
    results.append(("Find question lists", test_find_question_lists()))
    
    # Test 3: Parse sections
    result = test_parse_sections()
    if isinstance(result, tuple):
        results.append(("Parse sections", result[0]))
        questions_by_category = result[1]
    else:
        results.append(("Parse sections", result))
        questions_by_category = None
    
    # Test 4: Extract single question
    result = test_extract_single_question()
    if isinstance(result, tuple):
        results.append(("Extract question", result[0]))
    else:
        results.append(("Extract question", result))
    
    # Test 5: Save question
    results.append(("Save question", test_save_question()))
    
    # Test 6: Full extraction
    results.append(("Full extraction", test_full_extraction()))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! The extractor is working correctly.")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review the output above.")


if __name__ == "__main__":
    main()

