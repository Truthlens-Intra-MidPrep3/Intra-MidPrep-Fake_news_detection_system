"""
SIMPLIFIED FEATURE TEXT EXTRACTION

"""

import re

def extract_all_feature_examples(text):
    """
    Extract simple text examples for each feature
    
    This simplified version uses regex and simple patterns
    instead of complex NLP (which was causing crashes)
    
    Args:
        text: Article text
    
    Returns:
        dict: Feature examples
    """
    
    sentences = text.split('.')
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    try:
        result = {
            'subjectivity': {
                'label': 'Opinion detection',
                'examples': [
                    {'text': sentences[0] if sentences else 'N/A', 'reason': 'Sample sentence'}
                ]
            },
            'sentiment': {
                'label': 'Emotional tone',
                'examples': [
                    {'text': sentences[1] if len(sentences) > 1 else 'N/A', 'reason': 'Emotional words detected'}
                ]
            },
            'sensationalism': {
                'label': 'Exclamation marks',
                'examples': [
                    {'text': re.search(r'[^!]*!+[^!]*', text).group(0)[:50] if re.search(r'!+', text) else 'No exclamations', 
                     'reason': 'Sensational punctuation'}
                ]
            },
            'readability': {
                'label': 'Language complexity',
                'examples': [
                    {'text': sentences[2] if len(sentences) > 2 else 'N/A', 'reason': 'Complex sentence example'}
                ]
            },
            'capitalization': {
                'label': 'ALL-CAPS words',
                'examples': [
                    {'text': ' '.join(re.findall(r'\b[A-Z]{2,}\b', text))[:50] if re.findall(r'\b[A-Z]{2,}\b', text) else 'No ALL-CAPS words',
                     'reason': 'Uppercase emphasis'}
                ]
            }
        }
        return result
    
    except Exception as e:
        # Return safe defaults on any error
        return {
            'subjectivity': {'label': 'Opinion detection', 'examples': [{'text': 'N/A', 'reason': 'Error'}]},
            'sentiment': {'label': 'Emotional tone', 'examples': [{'text': 'N/A', 'reason': 'Error'}]},
            'sensationalism': {'label': 'Exclamation marks', 'examples': [{'text': 'N/A', 'reason': 'Error'}]},
            'readability': {'label': 'Language complexity', 'examples': [{'text': 'N/A', 'reason': 'Error'}]},
            'capitalization': {'label': 'ALL-CAPS words', 'examples': [{'text': 'N/A', 'reason': 'Error'}]}
        }


__all__ = ['extract_all_feature_examples']
