"""

Features:
1. Single article input
2. CSV file upload
3. Exit

Output: CSV file with all analysis results
"""

import sys
import os
import shutil
import pandas as pd
from pathlib import Path

# Import all backend modules
from preprocessing import preprocess_user_input, preprocess_batch_input, save_preprocessed_output
from feature_extraction import extract_features_from_csv
from model_prediction import predict_from_csv, add_uncertainty_classification
from explanation_user_improved import explain_predictions_improved_from_csv
from source_credibility import add_source_credibility_from_csv, print_source_statistics
from feature_text_extraction import extract_all_feature_examples

# ============================================================
# CONFIGURATION
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    'model_path': os.path.join(HERE, 'xgboost_model.json'),
    'credibility_lookup_path': os.path.join(HERE, 'source_credibility_lookup.csv'),
    'temp_dir': HERE,
    'output_dir': HERE,
    'uncertainty_threshold': 0.65,
    'model_weight': 0.8,
    'source_weight': 0.2
}

# Create directory if it doesn't exist
os.makedirs(HERE, exist_ok=True)

print("\n" + "="*70)
print("📁 ALL FILES WILL BE SAVED TO:")
print("="*70)
print(f"   {HERE}")
print("="*70 + "\n")

# ============================================================
# HELPER: CREATE FINAL OUTPUT CSV WITH ALL COLUMNS
# ============================================================

def create_final_output_csv(predictions_csv, features_csv, explanations_csv, 
                            source_credibility_csv=None, output_path=None):
    """
    Create final output CSV with all required columns:
    - text
    - source
    - prediction
    - confidence
    - source_credibility (if available)
    - sentiment, subjectivity, readability, exclamation_ratio, uppercase_ratio
    - subjectivity_examples, sent   iment_examples, sensationalism_examples, 
      readability_examples, capitalization_examples
    - explanation (full explanation text)
    
    Args:
        predictions_csv: Path to predictions CSV
        features_csv: Path to features CSV
        explanations_csv: Path to explanations CSV
        source_credibility_csv: Path to source credibility CSV (optional)
        output_path: Path to save final CSV
    
    Returns:
        str: Path to final output CSV
    """
    
    print("\n" + "="*70)
    print("CREATING FINAL OUTPUT CSV")
    print("="*70)
    
    # Load all CSVs
    print("\n1. Loading data from all sources...")
    pred_df = pd.read_csv(predictions_csv)
    feat_df = pd.read_csv(features_csv)
    expl_df = pd.read_csv(explanations_csv)
    
    if source_credibility_csv and os.path.exists(source_credibility_csv):
        cred_df = pd.read_csv(source_credibility_csv)
        has_credibility = True
    else:
        has_credibility = False
    
    print(f"   ✓ Loaded {len(pred_df)} predictions")
    
    # Build final DataFrame
    print("\n2. Building final output DataFrame...")
    
    final_df = pd.DataFrame({
        'text': pred_df['text'],
        'source': pred_df['source'],
        'prediction': pred_df['prediction_label'],
        'confidence': pred_df['confidence'],
    })
    
    # Add source credibility if available
    if has_credibility:
        final_df['source_credibility_score'] = cred_df['source_credibility_score']
        final_df['adjusted_confidence'] = cred_df['adjusted_confidence']
    
    # Add linguistic features
    final_df['sentiment'] = feat_df['feature_768']
    final_df['subjectivity'] = feat_df['feature_769']
    final_df['readability'] = feat_df['feature_770']
    final_df['exclamation_ratio'] = feat_df['feature_771']
    final_df['uppercase_ratio'] = feat_df['feature_772']
    
    # Extract feature examples for each article
    print("\n3. Extracting feature examples from text...")
    
    subjectivity_examples = []
    sentiment_examples = []
    sensationalism_examples = []
    readability_examples = []
    capitalization_examples = []
    
    for idx, text in enumerate(pred_df['text']):
        if (idx + 1) % 50 == 0:
            print(f"   Progress: {idx + 1}/{len(pred_df)}")
        
        try:
            # Extract examples
            feature_data = extract_all_feature_examples(text)
            
            # Format examples as strings for CSV
            subj_text = " | ".join([ex['text'] for ex in feature_data['subjectivity']['examples'][:2]])
            sent_text = " | ".join([ex['text'] for ex in feature_data['sentiment']['examples'][:2]])
            sens_text = " | ".join([ex['text'] for ex in feature_data['sensationalism']['examples'][:2]])
            read_text = " | ".join([ex['text'] for ex in feature_data['readability']['examples'][:2]])
            cap_text = " | ".join([ex['text'] for ex in feature_data['capitalization']['examples'][:2]])
            
            subjectivity_examples.append(subj_text if subj_text else "No examples found")
            sentiment_examples.append(sent_text if sent_text else "No examples found")
            sensationalism_examples.append(sens_text if sens_text else "No examples found")
            readability_examples.append(read_text if read_text else "No examples found")
            capitalization_examples.append(cap_text if cap_text else "No examples found")
        
        except Exception as e:
            print(f"   Warning: Could not extract examples for article {idx + 1}")
            subjectivity_examples.append("Error extracting examples")
            sentiment_examples.append("Error extracting examples")
            sensationalism_examples.append("Error extracting examples")
            readability_examples.append("Error extracting examples")
            capitalization_examples.append("Error extracting examples")
    
    # Add examples columns
    final_df['subjectivity_examples'] = subjectivity_examples
    final_df['sentiment_examples'] = sentiment_examples
    final_df['sensationalism_examples'] = sensationalism_examples
    final_df['readability_examples'] = readability_examples
    final_df['capitalization_examples'] = capitalization_examples
    
    # Add full explanation
    final_df['explanation'] = expl_df['explanation']
    
    print(f"   ✓ DataFrame created: {final_df.shape}")
    
    # Save to CSV
    print("\n4. Saving final output...")
    abs_output_path = os.path.abspath(output_path)
    final_df.to_csv(abs_output_path, index=False, encoding='utf-8-sig')
    
    print(f"   ✓ Final output saved")
    print(f"   📁 File location: {abs_output_path}")
    print(f"   Columns: {len(final_df.columns)}")
    print(f"   Rows: {len(final_df)}")
    
    print("\n" + "="*70)
    print("✓ FINAL OUTPUT COMPLETE")
    print("="*70)
    
    return abs_output_path

# ============================================================
# PART 1: SINGLE ARTICLE INPUT
# ============================================================

def predict_single_article():
    """
    Option 1: Single article input
    """
    
    print("\n" + "="*70)
    print("OPTION 1: SINGLE ARTICLE ANALYSIS")
    print("="*70)
    
    print("\nEnter the article text (or type 'CANCEL' to go back):")
    text = input("\n> ").strip()
    
    if text.upper() == 'CANCEL':
        return
    
    if not text or len(text) < 10:
        print("❌ Error: Text must be at least 10 characters")
        return
    
    print("\nEnter source/author name (press Enter to skip):")
    source = input("> ").strip()
    source = source if source else 'unknown'
    
    try:
        # 1. Preprocess
        print("\n[1/5] Preprocessing...")
        preprocessed_df = preprocess_user_input(text, source)
        preprocessed_path = os.path.join(CONFIG['temp_dir'], 'preprocessed_single.csv')
        save_preprocessed_output(preprocessed_df, preprocessed_path)
        
        # 2. Feature extraction
        print("[2/5] Extracting features...")
        features_path = os.path.join(CONFIG['temp_dir'], 'features_single.csv')
        extract_features_from_csv(preprocessed_path, features_path)
        
        # 3. Prediction
        print("[3/5] Making prediction...")
        predictions_path = os.path.join(CONFIG['temp_dir'], 'predictions_single.csv')
        predict_from_csv(features_path, CONFIG['model_path'], predictions_path)
        
        # 4. Explanation
        print("[4/5] Generating explanation...")
        explanations_path = os.path.join(CONFIG['temp_dir'], 'explanations_single.csv')
        explain_predictions_improved_from_csv(predictions_path, features_path, explanations_path)
        
        # 5. Source credibility
        print("[5/5] Adding source credibility...")
        cred_path = os.path.join(CONFIG['temp_dir'], 'credibility_single.csv')
        
        # Check if credibility file exists
        if os.path.exists(CONFIG['credibility_lookup_path']):
            add_source_credibility_from_csv(explanations_path, 
                                           CONFIG['credibility_lookup_path'],
                                           cred_path,
                                           CONFIG['model_weight'],
                                           CONFIG['source_weight'])
            has_credibility = True
        else:
            shutil.copy(explanations_path, cred_path)
            has_credibility = False
        
        # 6. Create final output
        print("\n[6/6] Creating final output CSV...")
        final_output_path = os.path.join(CONFIG['output_dir'], 'single_article_analysis.csv')
        
        create_final_output_csv(
            predictions_path, 
            features_path, 
            explanations_path,
            cred_path if has_credibility else None,
            final_output_path
        )
        
        print("\n✓ ANALYSIS COMPLETE")
        print(f"Output saved to: {final_output_path}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

# ============================================================
# PART 2: BATCH CSV INPUT
# ============================================================

def predict_batch_csv():
    """
    Option 2: Batch CSV input
    """
    
    print("\n" + "="*70)
    print("OPTION 2: BATCH ANALYSIS (CSV FILE)")
    print("="*70)
    
    print("\nEnter CSV file path (or type 'CANCEL' to go back):")
    print("(CSV must have 'text' column, optional 'source' column)")
    csv_path = input("\n> ").strip()
    
    if csv_path.upper() == 'CANCEL':
        return
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: File not found: {csv_path}")
        return
    
    try:
        # 1. Preprocess
        print("\n[1/5] Preprocessing batch...")
        preprocessed_df = preprocess_batch_input(csv_path)
        preprocessed_path = os.path.join(CONFIG['temp_dir'], 'preprocessed_batch.csv')
        save_preprocessed_output(preprocessed_df, preprocessed_path)
        
        # 2. Feature extraction
        print("[2/5] Extracting features...")
        features_path = os.path.join(CONFIG['temp_dir'], 'features_batch.csv')
        extract_features_from_csv(preprocessed_path, features_path)
        
        # 3. Prediction
        print("[3/5] Making predictions...")
        predictions_path = os.path.join(CONFIG['temp_dir'], 'predictions_batch.csv')
        predict_from_csv(features_path, CONFIG['model_path'], predictions_path)
        
        # 4. Explanation
        print("[4/5] Generating explanations...")
        explanations_path = os.path.join(CONFIG['temp_dir'], 'explanations_batch.csv')
        explain_predictions_improved_from_csv(predictions_path, features_path, explanations_path)
        
        # 5. Source credibility
        print("[5/5] Adding source credibility...")
        cred_path = os.path.join(CONFIG['temp_dir'], 'credibility_batch.csv')
        
        # Check if credibility file exists
        if os.path.exists(CONFIG['credibility_lookup_path']):
            add_source_credibility_from_csv(explanations_path, 
                                           CONFIG['credibility_lookup_path'],
                                           cred_path,
                                           CONFIG['model_weight'],
                                           CONFIG['source_weight'])
            has_credibility = True
        else:
            shutil.copy(explanations_path, cred_path)
            has_credibility = False
        
        # 6. Create final output
        print("\n[6/6] Creating final output CSV...")
        final_output_path = os.path.join(CONFIG['output_dir'], 'batch_analysis_results.csv')
        
        create_final_output_csv(
            predictions_path, 
            features_path, 
            explanations_path,
            cred_path if has_credibility else None,
            final_output_path
        )
        
        print("\n✓ BATCH ANALYSIS COMPLETE")
        print(f"Output saved to: {final_output_path}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

# ============================================================
# PART 3: MAIN MENU
# ============================================================

def main_menu():
    """
    Main interactive menu with 3 options
    """
    
    while True:
        print("\n" + "="*70)
        print("MISINFORMATION DETECTION SYSTEM")
        print("="*70)
        print("\nSelect an option:\n")
        print("1. Analyze single article")
        print("2. Batch analysis (CSV file)")
        print("3. Exit")
        print("\n" + "="*70)
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            predict_single_article()
        
        elif choice == '2':
            predict_batch_csv()
        
        elif choice == '3':
            print("\n✓ Thank you for using the system. Goodbye!")
            break
        
        else:
            print("\n❌ Invalid choice. Please enter 1, 2, or 3.")

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == '__main__':
    main_menu()
