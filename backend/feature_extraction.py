"""
FEATURE EXTRACTION MODULE
Converts preprocessed text to 773-dimensional feature vectors
(768 DistilBERT embedding + 5 linguistic features)

"""

import os
import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from textblob import TextBlob
import textstat
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# LOAD AND CACHE MODEL (global)
# ============================================================

_tokenizer = None
_model = None
_device = None

def get_model_and_tokenizer():
    """Load DistilBERT model and tokenizer (cached)"""
    global _tokenizer, _model, _device
    
    if _model is None:
        print("Loading DistilBERT model...")
        _tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
        _model = AutoModel.from_pretrained('distilbert-base-uncased')
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        _model = _model.to(_device)
        _model.eval()
        print(f"✓ DistilBERT loaded (using {_device})")
    
    return _tokenizer, _model, _device

# ============================================================
# PART 1: TEXT EMBEDDING (768 dims from DistilBERT)
# ============================================================

def get_embedding(text, max_length=512):
    """
    Convert text to 768-dimensional DistilBERT embedding
    
    Args:
        text (str): Cleaned text
        max_length (int): Maximum token length
    
    Returns:
        np.ndarray: 768-dim embedding
    """
    
    tokenizer, model, device = get_model_and_tokenizer()

    # Tokenize
    inputs = tokenizer(text, return_tensors='pt', truncation=True,
                       max_length=max_length, padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Forward pass
    with torch.no_grad():
        outputs = model(**inputs)

    # Mean pooling (average across tokens)
    embeddings = outputs.last_hidden_state
    mask = inputs['attention_mask'].unsqueeze(-1).expand(embeddings.size()).float()
    sum_embeddings = torch.sum(embeddings * mask, 1)
    sum_mask = torch.clamp(mask.sum(1), min=1e-9)
    embedding = sum_embeddings / sum_mask

    return embedding.cpu().numpy()[0]

# ============================================================
# PART 2: LINGUISTIC FEATURES (5 dims)
# ============================================================

def get_linguistic_features(text):
    """
    Extract 5 hand-crafted linguistic features
    
    Features:
    1. Sentiment polarity (-1 to 1)
    2. Subjectivity (0 to 1)
    3. Readability (0 to 1, normalized Flesch reading ease)
    4. Exclamation ratio (exclamation marks per sentence)
    5. Uppercase ratio (percentage of uppercase letters)
    
    Args:
        text (str): Cleaned text
    
    Returns:
        np.ndarray: 5-dim feature vector
    """
    try:
        # 1. Sentiment & Subjectivity (TextBlob)
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # 2. Readability (Flesch reading ease)
        readability = textstat.flesch_reading_ease(text) / 100  # Normalize to 0-1
        
        # 3. Exclamation ratio
        exclamation_count = text.count('!')
        total_sentences = max(len(text.split('.')), 1)
        exclamation_ratio = exclamation_count / total_sentences
        
        # 4. Uppercase ratio
        if len(text) > 0:
            uppercase_ratio = sum(1 for c in text if c.isupper()) / len(text)
        else:
            uppercase_ratio = 0
        
        return np.array([
            sentiment,
            subjectivity,
            readability,
            exclamation_ratio,
            uppercase_ratio
        ])
    
    except Exception as e:
        print(f"Error extracting linguistic features: {e}")
        return np.zeros(5)

# ============================================================
# PART 3: COMBINED FEATURE EXTRACTION
# ============================================================

def extract_features_single(text):
    """
    Extract all features (773 dims) for a single text
    
    Args:
        text (str): Cleaned text
    
    Returns:
        np.ndarray: 768 (DistilBERT) + 5 (linguistic) = 773 dims
    """
    embedding = get_embedding(text)
    linguistic = get_linguistic_features(text)
    
    return np.concatenate([embedding, linguistic])

# ============================================================
# PART 4: BATCH FEATURE EXTRACTION FROM CSV
# ============================================================

def extract_features_from_csv(preprocessed_csv_path, output_csv_path='features_output.csv'):
    """
    Extract features from preprocessed CSV
    
    Input CSV format:
        text,text_cleaned,source
        "article1","article1 cleaned","reuters"
        "article2","article2 cleaned","unknown"
    
    Output CSV format:
        text,source,feature_0,feature_1,...,feature_388
        "article1","reuters",0.234,-0.456,...,0.789
        "article2","unknown",0.123,0.456,...,0.234
    
    Args:
        preprocessed_csv_path (str): Path to preprocessed CSV
        output_csv_path (str): Path to save features CSV
    
    Returns:
        str: Path to output CSV
    """
    
    print("="*70)
    print("FEATURE EXTRACTION")
    print("="*70)
    
    # 1. Load preprocessed data
    print(f"\n1. Loading preprocessed data from: {preprocessed_csv_path}")
    df = pd.read_csv(preprocessed_csv_path)
    
    if 'text_cleaned' not in df.columns:
        raise ValueError("CSV must have 'text_cleaned' column")
    
    print(f"   Loaded: {len(df)} rows")
    
    # 2. Extract features
    print(f"\n2. Extracting features ({len(df)} samples)...")
    print("   (This may take several minutes - DistilBERT is slower but more accurate)")
    
    features_list = []
    
    for idx, text in enumerate(df['text_cleaned']):
        if (idx + 1) % 50 == 0:
            print(f"   Progress: {idx + 1}/{len(df)}")
        
        features = extract_features_single(text)
        features_list.append(features)
    
    # Convert to numpy array
    features_array = np.array(features_list)
    
    print(f"\n   ✓ Features extracted: {features_array.shape}")
    print(f"     Samples: {features_array.shape[0]}")
    print(f"     Dimensions: {features_array.shape[1]} (768 DistilBERT + 5 linguistic)")
    
    # 3. Create output DataFrame
    print(f"\n3. Creating output DataFrame...")
    
    output_df = pd.DataFrame(features_array)
    output_df.columns = [f'feature_{i}' for i in range(features_array.shape[1])]
    
    # Add original text and source columns
    output_df.insert(0, 'source', df['source'].values)
    output_df.insert(0, 'text', df['text'].values)
    
    print(f"   ✓ DataFrame created: {output_df.shape}")
    print(f"     Columns: {list(output_df.columns[:5])}... (+ {output_df.shape[1]-5} feature columns)")
    
    # 4. Save to CSV
    abs_output_path = os.path.abspath(output_csv_path)
    print(f"\n4. Saving to: {abs_output_path}")
    output_df.to_csv(abs_output_path, index=False)
    
    print(f"   ✓ Features saved")
    print(f"   📁 File location: {abs_output_path}")
    
    print("\n" + "="*70)
    print("FEATURE EXTRACTION COMPLETE")
    print("="*70)
    
    return abs_output_path

# ============================================================
# PART 5: FEATURE INFORMATION
# ============================================================

def get_feature_names():
    """Get list of feature names"""
    embedding_features = [f'distilbert_{i}' for i in range(768)]
    linguistic_features = [
        'sentiment',
        'subjectivity',
        'readability',
        'exclamation_ratio',
        'uppercase_ratio'
    ]
    return embedding_features + linguistic_features

def get_feature_descriptions():
    """Get descriptions of features"""
    return {
        'distilbert_0-767': 'DistilBERT semantic embeddings (768 dims)',
        'sentiment': 'Sentiment polarity (-1 to 1)',
        'subjectivity': 'Subjectivity score (0 to 1)',
        'readability': 'Flesch reading ease (normalized 0 to 1)',
        'exclamation_ratio': 'Exclamation marks per sentence',
        'uppercase_ratio': 'Percentage of uppercase letters'
    }

