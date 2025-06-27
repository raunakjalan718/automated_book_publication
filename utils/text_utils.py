import re
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing line breaks.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text
    """
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove spaces at beginning of lines
    text = re.sub(r'^ +', '', text, flags=re.MULTILINE)
    
    return text.strip()

def extract_paragraphs(text: str) -> List[str]:
    """
    Extract paragraphs from a text.
    
    Args:
        text: Input text
        
    Returns:
        List of paragraphs
    """
    # Split on double newlines or more
    paragraphs = re.split(r'\n{2,}', text)
    
    # Filter out empty paragraphs
    return [p.strip() for p in paragraphs if p.strip()]

def compare_texts(text1: str, text2: str) -> Dict[str, Any]:
    """
    Compare two texts and provide similarity metrics.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Dictionary with comparison metrics
    """
    # Simple length comparison
    len1 = len(text1)
    len2 = len(text2)
    length_diff = abs(len1 - len2)
    length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0
    
    # Word count comparison
    words1 = len(re.findall(r'\w+', text1))
    words2 = len(re.findall(r'\w+', text2))
    word_diff = abs(words1 - words2)
    word_ratio = min(words1, words2) / max(words1, words2) if max(words1, words2) > 0 else 0
    
    # Paragraph count comparison
    paras1 = len(extract_paragraphs(text1))
    paras2 = len(extract_paragraphs(text2))
    para_diff = abs(paras1 - paras2)
    para_ratio = min(paras1, paras2) / max(paras1, paras2) if max(paras1, paras2) > 0 else 0
    
    return {
        "char_length": {"orig": len1, "new": len2, "diff": length_diff, "ratio": length_ratio},
        "word_count": {"orig": words1, "new": words2, "diff": word_diff, "ratio": word_ratio},
        "paragraph_count": {"orig": paras1, "new": paras2, "diff": para_diff, "ratio": para_ratio}
    }
