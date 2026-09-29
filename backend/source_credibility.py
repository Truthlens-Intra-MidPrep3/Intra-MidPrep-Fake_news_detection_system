"""
SOURCE CREDIBILITY MODULE
Loads source credibility scores and integrates them with predictions

"""

import os
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PART 1: LOAD SOURCE CREDIBILITY DATABASE
# ============================================================

def load_source_credibility(credibility_csv_path='source_credibility_lookup.csv'):
    """
    Load source credibility lookup table
    
    Args:
        credibility_csv_path (str): Path to source credibility CSV
    
    Returns:
        dict: {source_name: credibility_score}
    """
    print(f"Loading source credibility from: {credibility_csv_path}")
    
    df = pd.read_csv(credibility_csv_path)
    
    # Create dictionary mapping
    source_credibility = dict(zip(df['source'], df['credibility_score']))
    
    print(f"✓ Loaded credibility scores for {len(source_credibility)} sources")
    
    return source_credibility

# ============================================================
# PART 2: GET SOURCE CREDIBILITY FOR SINGLE SOURCE
# ============================================================

def get_source_credibility_score(source, source_credibility_dict):
    """
    Get credibility score for a source
    
    Args:
        source (str): Source/author name
        source_credibility_dict (dict): Source credibility lookup
    
    Returns:
        float or None: Credibility score (0-1) or None if unknown
    """
    # Normalize source name (lowercase for matching)
    source_normalized = str(source).lower().strip()
    
    # Try exact match first
    if source_normalized in source_credibility_dict:
        return source_credibility_dict[source_normalized]
    
    # Try case-insensitive match in dictionary
    for key, value in source_credibility_dict.items():
        if key.lower() == source_normalized:
            return value
    
    # Unknown source
    return None

def interpret_credibility(credibility_score):
    """
    Convert credibility score to human-readable interpretation
    
    Args:
        credibility_score (float or None): Credibility score (0-1)
    
    Returns:
        str: Human-readable interpretation
    """
    if credibility_score is None:
        return "Unknown source - no historical data available"
    
    if credibility_score >= 0.8:
        return f"Very credible source ({credibility_score:.2f}) - high historical accuracy"
    elif credibility_score >= 0.6:
        return f"Credible source ({credibility_score:.2f}) - generally reliable"
    elif credibility_score >= 0.4:
        return f"Neutral source ({credibility_score:.2f}) - mixed track record"
    elif credibility_score >= 0.2:
        return f"Low credibility ({credibility_score:.2f}) - frequently inaccurate"
    else:
        return f"Very low credibility ({credibility_score:.2f}) - mostly unreliable"

# ============================================================
# PART 3: ADJUST PREDICTION BASED ON SOURCE CREDIBILITY
# ============================================================

def adjust_confidence_with_source(model_confidence, source_credibility, 
                                  model_weight=0.8, source_weight=0.2):
    """
    Adjust model confidence using source credibility
    
    Formula:
        adjusted_confidence = model_weight * model_confidence + source_weight * source_credibility
    
    Args:
        model_confidence (float): Model's confidence (0-1)
        source_credibility (float or None): Source credibility (0-1)
        model_weight (float): Weight of model confidence (default 0.8)
        source_weight (float): Weight of source credibility (default 0.2)
    
    Returns:
        float: Adjusted confidence (0-1)
    """
    if source_credibility is None:
        # No source data, use model confidence only
        return model_confidence
    
    # Adjust confidence using source credibility
    adjusted = (model_weight * model_confidence) + (source_weight * source_credibility)
    
    return min(max(adjusted, 0.0), 1.0)  # Clamp to [0, 1]

def get_credibility_note(model_confidence, source_credibility, adjusted_confidence):
    """
    Create note about how source credibility affected prediction
    
    Args:
        model_confidence (float): Original model confidence
        source_credibility (float or None): Source credibility
        adjusted_confidence (float): Adjusted confidence
    
    Returns:
        str: Note about credibility adjustment
    """
    if source_credibility is None:
        return "No source credibility data - prediction based on article text only"
    
    if adjusted_confidence > model_confidence:
        boost = adjusted_confidence - model_confidence
        return f"Source credibility boosts confidence by +{boost:.4f} (from {model_confidence:.4f} to {adjusted_confidence:.4f})"
    elif adjusted_confidence < model_confidence:
        drop = model_confidence - adjusted_confidence
        return f"Source credibility reduces confidence by -{drop:.4f} (from {model_confidence:.4f} to {adjusted_confidence:.4f})"
    else:
        return "Source credibility does not change model confidence"

# ============================================================
# PART 4: BATCH ADD SOURCE CREDIBILITY FROM CSV
# ============================================================

def add_source_credibility_from_csv(explanations_csv_path, 
                                    credibility_csv_path='source_credibility_lookup.csv',
                                    output_csv_path='final_output.csv',
                                    model_weight=0.8,
                                    source_weight=0.2):
    """
    Add source credibility scores to explanations CSV
    
    Input CSV (from explanation module):
        text, source, prediction, confidence, top_feature_1, ..., reasoning
    
    Output CSV:
        text, source, prediction, confidence,
        source_credibility_score, source_credibility_interpretation,
        adjusted_confidence, credibility_note,
        top_feature_1, ..., reasoning
    
    Args:
        explanations_csv_path (str): Path to explanations CSV
        credibility_csv_path (str): Path to source credibility lookup CSV
        output_csv_path (str): Path to save final output CSV
        model_weight (float): Weight of model confidence in adjustment
        source_weight (float): Weight of source credibility in adjustment
    
    Returns:
        str: Path to output CSV
    """
    
    print("="*70)
    print("SOURCE CREDIBILITY INTEGRATION")
    print("="*70)
    
    # 1. Load source credibility database
    print(f"\n1. Loading source credibility database...")
    source_credibility_dict = load_source_credibility(credibility_csv_path)
    
    # 2. Load explanations
    print(f"\n2. Loading explanations from: {explanations_csv_path}")
    explanations_df = pd.read_csv(explanations_csv_path)
    print(f"   Loaded: {len(explanations_df)} explanations")
    
    # 3. Add source credibility scores
    print(f"\n3. Adding source credibility scores...")
    
    source_credibility_scores = []
    source_interpretations = []
    adjusted_confidences = []
    credibility_notes = []
    
    for idx, row in explanations_df.iterrows():
        if (idx + 1) % 100 == 0:
            print(f"   Progress: {idx + 1}/{len(explanations_df)}")
        
        source = row['source']
        model_confidence = row['confidence']
        
        # Get source credibility
        cred_score = get_source_credibility_score(source, source_credibility_dict)
        cred_interpretation = interpret_credibility(cred_score)
        
        # Adjust confidence
        adjusted_conf = adjust_confidence_with_source(
            model_confidence, cred_score, model_weight, source_weight
        )
        
        # Get note
        note = get_credibility_note(model_confidence, cred_score, adjusted_conf)
        
        source_credibility_scores.append(cred_score)
        source_interpretations.append(cred_interpretation)
        adjusted_confidences.append(adjusted_conf)
        credibility_notes.append(note)
    
    print(f"   ✓ Credibility scores added")
    
    # 4. Create output DataFrame
    print(f"\n4. Creating output DataFrame...")
    
    output_df = explanations_df.copy()
    
    output_df.insert(
        output_df.columns.get_loc('confidence') + 1,
        'source_credibility_score',
        source_credibility_scores
    )
    
    output_df.insert(
        output_df.columns.get_loc('source_credibility_score') + 1,
        'source_credibility_interpretation',
        source_interpretations
    )
    
    output_df.insert(
        output_df.columns.get_loc('source_credibility_interpretation') + 1,
        'adjusted_confidence',
        adjusted_confidences
    )
    
    output_df.insert(
        output_df.columns.get_loc('adjusted_confidence') + 1,
        'credibility_note',
        credibility_notes
    )
    
    print(f"   ✓ DataFrame created: {output_df.shape}")
    
    # 5. Summary statistics
    print(f"\n5. Source Credibility Summary:")
    
    known_sources = sum(1 for score in source_credibility_scores if score is not None)
    unknown_sources = len(source_credibility_scores) - known_sources
    
    print(f"   Sources with credibility data: {known_sources}")
    print(f"   Unknown sources: {unknown_sources}")
    
    if known_sources > 0:
        known_scores = [s for s in source_credibility_scores if s is not None]
        avg_credibility = np.mean(known_scores)
        print(f"   Average credibility score: {avg_credibility:.4f}")
    
    # Count confidence adjustments
    same_count = sum(1 for i in range(len(adjusted_confidences)) 
                     if adjusted_confidences[i] == explanations_df.iloc[i]['confidence'])
    boost_count = sum(1 for i in range(len(adjusted_confidences)) 
                      if adjusted_confidences[i] > explanations_df.iloc[i]['confidence'])
    reduce_count = sum(1 for i in range(len(adjusted_confidences)) 
                       if adjusted_confidences[i] < explanations_df.iloc[i]['confidence'])
    
    print(f"\n   Confidence adjustments:")
    print(f"   - No change: {same_count} predictions")
    print(f"   - Confidence boosted: {boost_count} predictions")
    print(f"   - Confidence reduced: {reduce_count} predictions")
    
    # 6. Save to CSV
    abs_output_path = os.path.abspath(output_csv_path)
    print(f"\n6. Saving to: {abs_output_path}")
    output_df.to_csv(abs_output_path, index=False)
    
    print(f"   ✓ Final output saved")
    print(f"   📁 File location: {abs_output_path}")
    
    print("\n" + "="*70)
    print("SOURCE CREDIBILITY INTEGRATION COMPLETE")
    print("="*70)
    
    return output_csv_path

# ============================================================
# PART 5: SOURCE STATISTICS
# ============================================================

def get_source_statistics(final_output_csv_path):
    """
    Get statistics about source credibility in final output
    
    Args:
        final_output_csv_path (str): Path to final output CSV
    
    Returns:
        dict: Statistics about sources
    """
    df = pd.read_csv(final_output_csv_path)
    
    stats = {
        'total_predictions': len(df),
        'unique_sources': df['source'].nunique(),
        'sources_with_data': sum(df['source_credibility_score'].notna()),
        'sources_unknown': sum(df['source_credibility_score'].isna()),
        'avg_source_credibility': df['source_credibility_score'].mean(),
        'avg_original_confidence': df['confidence'].mean(),
        'avg_adjusted_confidence': df['adjusted_confidence'].mean()
    }
    
    return stats

def print_source_statistics(final_output_csv_path):
    """
    Print source statistics for review
    
    Args:
        final_output_csv_path (str): Path to final output CSV
    """
    stats = get_source_statistics(final_output_csv_path)
    
    print("\n" + "="*70)
    print("SOURCE CREDIBILITY STATISTICS")
    print("="*70)
    print(f"\nTotal predictions: {stats['total_predictions']}")
    print(f"Unique sources: {stats['unique_sources']}")
    print(f"Sources with credibility data: {stats['sources_with_data']}")
    print(f"Unknown sources: {stats['sources_unknown']}")
    print(f"\nAverage source credibility: {stats['avg_source_credibility']:.4f}")
    print(f"Average original model confidence: {stats['avg_original_confidence']:.4f}")
    print(f"Average adjusted confidence: {stats['avg_adjusted_confidence']:.4f}")
    print("="*70)

