"""
OUTPUT FORMATTER 
Handles conversion between formats and ensures explanation text is preserved fully
"""

import pandas as pd
import os

def load_and_merge_outputs(predictions_csv, features_csv, explanations_csv, 
                           source_credibility_csv=None):
    """
    Load and merge all outputs into a single DataFrame
    
    Args:
        predictions_csv: Path to predictions CSV
        features_csv: Path to features CSV  
        explanations_csv: Path to explanations CSV
        source_credibility_csv: Path to source credibility CSV (optional)
    
    Returns:
        pd.DataFrame: Merged output with all columns
    """
    
    # Load CSVs
    pred_df = pd.read_csv(predictions_csv)
    feat_df = pd.read_csv(features_csv)
    
    # Load explanations with proper handling for multi-line text
    expl_df = pd.read_csv(explanations_csv, quotechar='"', escapechar='\\')
    
    # Build merged DataFrame
    merged_df = pd.DataFrame({
        'title': pred_df.get('title', [''] * len(pred_df)) if 'title' in pred_df.columns else [''] * len(pred_df),
        'author': pred_df.get('author', [''] * len(pred_df)) if 'author' in pred_df.columns else [''] * len(pred_df),
        'text': pred_df['text'],
        'source': pred_df['source'],
        'prediction': pred_df['prediction_label'],
        'confidence': pred_df['confidence'],
    })
    
    # Add linguistic features
    merged_df['sentiment'] = feat_df['feature_768']
    merged_df['subjectivity'] = feat_df['feature_769']
    merged_df['readability'] = feat_df['feature_770']
    merged_df['exclamation_ratio'] = feat_df['feature_771']
    merged_df['uppercase_ratio'] = feat_df['feature_772']
    
    # CRITICAL: Preserve full explanation text from explanations_csv
    # The explanation column contains the full formatted explanation
    merged_df['explanation'] = expl_df['explanation'].astype(str)
    
    # Add source credibility if available
    if source_credibility_csv and os.path.exists(source_credibility_csv):
        cred_df = pd.read_csv(source_credibility_csv)
        merged_df['source_credibility_score'] = cred_df['source_credibility_score']
        merged_df['adjusted_confidence'] = cred_df['adjusted_confidence']
    
    return merged_df


def save_to_csv(df, output_path, include_examples=False):
    """
    Save merged DataFrame to CSV
    
    CRITICAL: Use quoting=csv.QUOTE_NONNUMERIC to preserve multi-line explanation text
    
    Args:
        df: DataFrame to save
        output_path: Path to save CSV
        include_examples: Whether to include example columns
    
    Returns:
        str: Path to saved file
    """
    
    import csv
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save with proper quoting to preserve newlines and multi-line text
    df.to_csv(
        output_path,
        index=False,
        quoting=csv.QUOTE_ALL,  # Quote all fields
        quotechar='"',
        escapechar='\\',
        encoding='utf-8'
    )
    
    abs_path = os.path.abspath(output_path)
    print(f"\n✓ Output saved to: {abs_path}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {len(df.columns)}")
    
    return abs_path


def save_to_json(df, output_path):
    """
    Save merged DataFrame to JSON (better for preserving complex text)
    
    Args:
        df: DataFrame to save
        output_path: Path to save JSON
    
    Returns:
        str: Path to saved file
    """
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Convert to JSON with full explanation preservation
    df.to_json(
        output_path,
        orient='records',
        indent=2,
        force_ascii=False
    )
    
    abs_path = os.path.abspath(output_path)
    print(f"\n✓ Output saved to: {abs_path}")
    print(f"  Rows: {len(df)}")
    print(f"  Format: JSON (preserves full text including newlines)")
    
    return abs_path


def format_explanation_for_display(explanation_text):
    """
    Format explanation text for console display
    
    Args:
        explanation_text: Raw explanation text from CSV
    
    Returns:
        str: Formatted text with proper line breaks
    """
    
    # Replace escaped newlines with actual newlines
    formatted = explanation_text.replace('\\n', '\n')
    return formatted


def display_single_result(row):
    """
    Display a single analysis result in formatted console output
    
    Args:
        row: DataFrame row
    """
    
    print("\n" + "="*70)
    print("ANALYSIS RESULT")
    print("="*70)
    
    print(f"\n📄 Text: {row['text'][:100]}...")
    print(f"📌 Source: {row['source']}")
    print(f"\n🎯 Prediction: {row['prediction']}")
    print(f"📊 Confidence: {row['confidence']:.2%}")
    
    if 'source_credibility_score' in row:
        print(f"✓ Source Credibility: {row['source_credibility_score']:.2%}")
        print(f"📈 Adjusted Confidence: {row['adjusted_confidence']:.2%}")
    
    print(f"\n📈 LINGUISTIC FEATURES")
    print(f"  • Sentiment: {row['sentiment']:.4f}")
    print(f"  • Subjectivity: {row['subjectivity']:.4f}")
    print(f"  • Readability: {row['readability']:.4f}")
    print(f"  • Exclamation Ratio: {row['exclamation_ratio']:.4f}")
    print(f"  • Uppercase Ratio: {row['uppercase_ratio']:.4f}")
    
    # Display full explanation with proper formatting
    print(f"\n📋 EXPLANATION:")
    print("-" * 70)
    formatted_explanation = format_explanation_for_display(row['explanation'])
    print(formatted_explanation)
    print("-" * 70)


def display_batch_summary(df):
    """
    Display summary statistics for batch analysis
    
    Args:
        df: Results DataFrame
    """
    
    print("\n" + "="*70)
    print("BATCH ANALYSIS SUMMARY")
    print("="*70)
    
    print(f"\nTotal items analyzed: {len(df)}")
    
    # Prediction distribution
    pred_counts = df['prediction'].value_counts()
    print(f"\nPrediction Distribution:")
    for pred, count in pred_counts.items():
        pct = (count / len(df)) * 100
        print(f"  • {pred}: {count} ({pct:.1f}%)")
    
    # Confidence statistics
    print(f"\nConfidence Statistics:")
    print(f"  • Mean: {df['confidence'].mean():.2%}")
    print(f"  • Min: {df['confidence'].min():.2%}")
    print(f"  • Max: {df['confidence'].max():.2%}")
    
    # Source statistics
    if df['source'].nunique() > 0:
        print(f"\nSources analyzed: {df['source'].nunique()}")
        top_sources = df['source'].value_counts().head(5)
        for source, count in top_sources.items():
            print(f"  • {source}: {count}")
    
    print("\n" + "="*70)


# Export functions
__all__ = [
    'load_and_merge_outputs',
    'save_to_csv',
    'save_to_json',
    'format_explanation_for_display',
    'display_single_result',
    'display_batch_summary'
]
