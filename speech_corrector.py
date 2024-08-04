import os
import re
from spellchecker import SpellChecker
from concurrent.futures import ProcessPoolExecutor, as_completed

def clean_text(text):
    # Fix common formatting issues
    text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
    text = re.sub(r'\.([A-Z])', r'. \1', text)  # Add space after periods if missing
    text = re.sub(r',([A-Z])', r', \1', text)  # Add space after commas if missing
    text = re.sub(r'!([A-Z])', r'! \1', text)  # Add space after exclamation marks if missing
    text = re.sub(r'\?([A-Z])', r'? \1', text)  # Add space after question marks if missing
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between camelCase words
    text = re.sub(r'(\S)([\"\'”’])', r'\1 \2', text)  # Add space before closing quotation marks
    text = re.sub(r'([\"\'“‘])(\S)', r'\1 \2', text)  # Add space after opening quotation marks
    text = re.sub(r'(\S)([:;])', r'\1 \2', text)  # Add space before colons and semicolons
    text = re.sub(r'([:;])(\S)', r'\1 \2', text)  # Add space after colons and semicolons
    
    # Remove extra spaces around newlines
    text = re.sub(r'\s*\n\s*', '\n', text)
    
    # Ensure single blank line between paragraphs
    text = re.sub(r'\n{2,}', '\n\n', text)
    
    # Handle cases where there are random paragraphs instead of spaces
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    
    text = text.strip()  # Remove leading and trailing whitespace
    return text

def correct_spelling(text):
    spell = SpellChecker()
    words = text.split()
    corrected_words = [spell.correction(word) if spell.correction(word) is not None else word for word in words]
    return ' '.join(corrected_words)

def process_release(release):
    sections = release.split('\n\n')
    cleaned_sections = [clean_text(section) for section in sections]
    corrected_sections = [correct_spelling(section) for section in cleaned_sections]
    return '\n\n'.join(corrected_sections)

def process_file(input_file, output_file, chunk_size=1000):
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    releases = content.split('\n\n==\n\n')
    processed_releases = []
    
    # Create new output file at the start
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write("")
    
    for idx, release in enumerate(releases):
        processed_release = process_release(release)
        processed_releases.append(processed_release)
        
        if (idx + 1) % chunk_size == 0 or (idx + 1) == len(releases):
            with open(output_file, 'a', encoding='utf-8') as file:
                file.write('\n\n==\n\n'.join(processed_releases) + '\n\n==\n\n')
            processed_releases = []
        
        print(f"Processed {idx + 1} out of {len(releases)} releases.")

def process_all_files_in_directory(input_directory):
    files = [
        "aoc.txt",
        "hawley.txt",
        "lee.txt",
        "manchin.txt",
        "markey.txt",
        "mtg.txt",
        "pocan.txt",
        "sanders.txt",
        "stefanik.txt"
    ]
    
    total_files = len(files)

    with ProcessPoolExecutor() as executor:
        futures = []
        for idx, filename in enumerate(files):
            input_file = os.path.join(input_directory, filename)
            output_file = os.path.join(input_directory, f"{filename.split('.')[0]}_formatted.txt")
            print(f"Starting processing of file {idx + 1} of {total_files}: {filename}")
            futures.append(executor.submit(process_file, input_file, output_file))
        
        for future in as_completed(futures):
            print(f"Completed processing of a file.")

if __name__ == "__main__":
    input_directory = 'output'
    process_all_files_in_directory(input_directory)
    print("All files processed successfully.")