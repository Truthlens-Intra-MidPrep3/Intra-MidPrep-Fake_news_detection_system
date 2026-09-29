"""
PREPROCESSING MODULE - Data Cleaning & Normalization
Converted from preprocessing.ipynb
"""

import os
import pandas as pd
import re
import unicodedata
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PART 1: DATA LOADING (for training data)
# ============================================================

def load_data(path):
    """Load dataset with text and label columns"""
    return pd.read_csv(
        path,
        usecols=["text", "label"],
        low_memory=False
    )

# ============================================================
# PART 2: LABEL CLEANING
# ============================================================

def clean_labels(df):
    """Remove invalid labels, keep only 0 and 1"""
    df = df.copy()
    
    # Convert labels to string and strip whitespace
    labels = df["label"].astype("string").str.strip()
    
    # Create mask for valid labels
    valid_mask = labels.isin(["0", "1"])
    
    # Keep only valid labels
    df = df.loc[valid_mask].copy()
    df["label"] = labels.loc[valid_mask].astype("int64")
    
    return df.reset_index(drop=True)

# ============================================================
# PART 3: TEXT VALIDATION
# ============================================================

def remove_invalid_text(df):
    """Remove rows with null or empty text"""
    df = df.copy()
    
    # Convert to string
    df["text"] = df["text"].astype("string")
    
    # Keep only non-null, non-empty text
    mask = (
        df["text"].notna() &
        df["text"].str.strip().ne("")
    )
    
    return df.loc[mask].reset_index(drop=True)

# ============================================================
# PART 4: TEXT NORMALIZATION (Core preprocessing)
# ============================================================

def normalize_text(text):
    """
    Normalize text for consistent processing
    - Unicode normalization
    - Remove HTML tags
    - Normalize whitespace
    """
    text = str(text)
    
    # 1. Unicode normalization (NFKC: decompose then recompose)
    text = unicodedata.normalize("NFKC", text)
    
    # 2. Remove HTML tags if present
    if re.search(r"<[^>]+>", text):
        text = re.sub(r"<[^>]+>", " ", text)
    
    # 3. Normalize whitespace (multiple spaces → single space)
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

# ============================================================
# PART 5: CONFLICT DETECTION (for training data QA)
# ============================================================

def find_conflicting_labels(df):
    """Find texts with same content but different labels"""
    label_counts = (
        df.groupby("text_normalized")["label"]
        .nunique()
    )
    
    conflicting_texts = label_counts[
        label_counts > 1
    ].index
    
    return df[
        df["text_normalized"].isin(conflicting_texts)
    ].sort_values("text_normalized")

# ============================================================
# PART 6: DEDUPLICATION
# ============================================================

def deduplicate_split(df):
    """Keep only first occurrence of each normalized text"""
    df = df.copy()
    
    # Drop duplicates, keeping first occurrence
    df = df.drop_duplicates(
        subset=["text_normalized"],
        keep="first"
    )
    
    return df.reset_index(drop=True)

# ============================================================
# PART 7: OVERLAP REMOVAL (ensure train/val/test separation)
# ============================================================

def overlap_count(df1, df2):
    """Count overlapping texts between two dataframes"""
    return len(
        set(df1["text_normalized"]) &
        set(df2["text_normalized"])
    )

def remove_train_test_overlap(train_df, valid_df, test_df):
    """Remove overlapping texts between datasets"""
    # Remove test texts from validation
    test_texts = set(test_df["text_normalized"])
    valid_df = valid_df[
        ~valid_df["text_normalized"].isin(test_texts)
    ].reset_index(drop=True)
    
    # Remove test+valid texts from train
    protected_texts = (
        set(test_df["text_normalized"]) |
        set(valid_df["text_normalized"])
    )
    train_df = train_df[
        ~train_df["text_normalized"].isin(protected_texts)
    ].reset_index(drop=True)
    
    return train_df, valid_df, test_df

# ============================================================
# PART 8: FULL PREPROCESSING PIPELINE (for training data)
# ============================================================

def preprocess_training_data(train_path, valid_path, test_path):
    """
    Complete preprocessing pipeline for training datasets
    
    Returns:
        train_df, valid_df, test_df - cleaned and deduplicated
    """
    print("="*70)
    print("PREPROCESSING TRAINING DATA")
    print("="*70)
    
    # 1. Load data
    print("\n1. Loading data...")
    train = load_data(train_path)
    valid = load_data(valid_path)
    test = load_data(test_path)
    print(f"   Train: {train.shape}, Valid: {valid.shape}, Test: {test.shape}")
    
    # 2. Clean labels
    print("\n2. Cleaning labels...")
    train = clean_labels(train)
    valid = clean_labels(valid)
    test = clean_labels(test)
    print(f"   Train: {train.shape}, Valid: {valid.shape}, Test: {test.shape}")
    
    # 3. Remove invalid text
    print("\n3. Removing invalid text...")
    train = remove_invalid_text(train)
    valid = remove_invalid_text(valid)
    test = remove_invalid_text(test)
    print(f"   Train: {train.shape}, Valid: {valid.shape}, Test: {test.shape}")
    
    # 4. Normalize text
    print("\n4. Normalizing text...")
    for df in [train, valid, test]:
        df["text_normalized"] = df["text"].apply(normalize_text)
    print("   ✓ Normalization complete")
    
    # 5. Find conflicts
    print("\n5. Finding conflicting labels...")
    train_conflicts = find_conflicting_labels(train)
    valid_conflicts = find_conflicting_labels(valid)
    test_conflicts = find_conflicting_labels(test)
    print(f"   Train conflicts: {len(train_conflicts)}")
    print(f"   Valid conflicts: {len(valid_conflicts)}")
    print(f"   Test conflicts: {len(test_conflicts)}")
    
    # 6. Deduplicate
    print("\n6. Deduplicating...")
    train = deduplicate_split(train)
    valid = deduplicate_split(valid)
    test = deduplicate_split(test)
    print(f"   Train: {train.shape}, Valid: {valid.shape}, Test: {test.shape}")
    
    # 7. Remove overlaps
    print("\n7. Removing overlaps...")
    train, valid, test = remove_train_test_overlap(train, valid, test)
    print(f"   Train: {train.shape}, Valid: {valid.shape}, Test: {test.shape}")
    
    # 8. Verify no overlaps
    print("\n8. Verifying separation...")
    train_valid_overlap = overlap_count(train, valid)
    train_test_overlap = overlap_count(train, test)
    valid_test_overlap = overlap_count(valid, test)
    print(f"   Train-Valid overlap: {train_valid_overlap}")
    print(f"   Train-Test overlap: {train_test_overlap}")
    print(f"   Valid-Test overlap: {valid_test_overlap}")
    
    # 9. Keep only text and label columns
    train_final = train[["text", "label"]].copy()
    valid_final = valid[["text", "label"]].copy()
    test_final = test[["text", "label"]].copy()
    
    print("\n" + "="*70)
    print("PREPROCESSING COMPLETE")
    print("="*70)
    print(f"Final datasets:")
    print(f"  Train: {train_final.shape}")
    print(f"  Valid: {valid_final.shape}")
    print(f"  Test: {test_final.shape}")
    
    return train_final, valid_final, test_final

# ============================================================
# PART 9: USER INPUT PREPROCESSING (for inference)
# ============================================================

def preprocess_user_input(text, source=None, title=None, author=None):
    """
    Preprocess single user input for inference
    Output as CSV (single row)
    
    Args:
        text (str): Raw user input text
        source (str, optional): Source/author of the article
        title (str, optional): Title of the article
        author (str, optional): Author of the article
    
    Returns:
        pd.DataFrame: Single row with 'text' and 'text_cleaned' columns
    """
    if text is None or (isinstance(text, str) and text.strip() == ""):
        raise ValueError("Input text cannot be empty")
    
    if len(text.strip()) < 10:
        raise ValueError("Input text too short (minimum 10 characters)")
    
    # Normalize
    cleaned_text = normalize_text(text)
    
    # Create DataFrame
    df = pd.DataFrame({
        'text': [text],
        'text_cleaned': [cleaned_text],
        'source': [source if source else 'unknown'],
        'title': [title if title else ''],
        'author': [author if author else '']
    })
    
    return df

def preprocess_batch_input(csv_path):
    """
    Preprocess batch CSV input for inference
    Output as DataFrame (ready for CSV save)
    
    Args:
        csv_path (str): Path to CSV with 'text' column
                       Optional: 'source' column
    
    Returns:
        pd.DataFrame: DataFrame with 'text', 'text_cleaned', 'source' columns
    """
    df = pd.read_csv(csv_path)
    
    if 'text' not in df.columns:
        raise ValueError("CSV must have 'text' column")
    
    # Remove empty rows
    df = df.dropna(subset=['text'])
    df = df[df['text'].astype(str).str.strip() != ''].reset_index(drop=True)
    
    # Normalize all texts
    df['text_cleaned'] = df['text'].apply(normalize_text)
    
    # Add source column if missing
    if 'source' not in df.columns:
        df['source'] = 'unknown'
    else:
        df['source'] = df['source'].fillna('unknown')
    
    return df[['text', 'text_cleaned', 'source']]

def save_preprocessed_output(df, output_path='preprocessed_input.csv'):
    """
    Save preprocessed data to CSV
    
    Args:
        df (pd.DataFrame): Preprocessed data with text, text_cleaned, source
        output_path (str): Path to save CSV
    
    Returns:
        str: Path to saved file
    """
    abs_output_path = os.path.abspath(output_path)
    df.to_csv(abs_output_path, index=False)
    print(f"✓ Preprocessed data saved to: {abs_output_path}")
    print(f"  📁 File location: {abs_output_path}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    return abs_output_path


    
