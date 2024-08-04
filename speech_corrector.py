import os
import re
from spellchecker import SpellChecker

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
    corrected_words = [spell.correction(word) if word.lower() not in spell else word for word in words]
    return ' '.join(corrected_words)

def process_file(input_file, output_file, chunk_size=1000):
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()

    cleaned_content = clean_text(content)
    corrected_content = correct_spelling(cleaned_content)

    words = corrected_content.split()
    processed_content = ''
    for i in range(0, len(words), chunk_size):
        processed_content += ' '.join(words[i:i + chunk_size]) + ' '
        # Save periodically
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(processed_content.strip() + '\n')
        print(f"Processed {min(i + chunk_size, len(words))} out of {len(words)} words.")

def process_all_files_in_directory(input_directory, output_directory):
    for filename in os.listdir(input_directory):
        if filename.endswith('.txt'):
            input_file = os.path.join(input_directory, filename)
            output_file = os.path.join(output_directory, f"corrected_{filename}")
            process_file(input_file, output_file)
            print(f"Processed {filename} and saved as corrected_{filename}")

if __name__ == "__main__":
    input_directory = 'output'
    output_directory = 'output'
    process_all_files_in_directory(input_directory, output_directory)
    print("Processing complete.")