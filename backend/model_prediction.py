"""
MODEL PREDICTION MODULE
Loads trained XGBoost model and makes predictions on feature vectors

"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PART 1: MODEL LOADING
# ============================================================

_model_cache = {}

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xgboost_model.json")

def load_model(model_path=DEFAULT_MODEL_PATH):
    """
    Load XGBoost model (cached)
    
    Args:
        model_path (str): Path to saved XGBoost model
    
    Returns:
        xgb.XGBClassifier: Loaded model
    """
    if model_path not in _model_cache:
        print(f"Loading XGBoost model from: {model_path}")
        model = xgb.XGBClassifier()
        model.load_model(model_path)
        _model_cache[model_path] = model
        print("✓ Model loaded")
    
    return _model_cache[model_path]

# ============================================================
# PART 2: SINGLE PREDICTION
# ============================================================

def predict_single(features, model):
    """
    Make prediction for a single sample
    
    Args:
        features (np.ndarray or list): Feature vector (389 dims)
        model (xgb.XGBClassifier): Loaded model
    
    Returns:
        dict: {
            'prediction': 0 or 1 (FAKE or REAL),
            'confidence': float (0-1),
            'fake_prob': float (0-1),
            'real_prob': float (0-1)
        }
    """
    # Reshape for model
    features_2d = np.array(features).reshape(1, -1)
    
    # Predict
    prediction = model.predict(features_2d)[0]
    probabilities = model.predict_proba(features_2d)[0]
    
    fake_prob = probabilities[0]
    real_prob = probabilities[1]
    
    # Determine confidence (max of the two probabilities)
    confidence = max(fake_prob, real_prob)
    
    return {
        'prediction': int(prediction),
        'confidence': float(confidence),
        'fake_prob': float(fake_prob),
        'real_prob': float(real_prob)
    }

# ============================================================
# PART 3: BATCH PREDICTIONS FROM CSV
# ============================================================

def predict_from_csv(features_csv_path, model_path=DEFAULT_MODEL_PATH, 
                     output_csv_path='predictions_output.csv'):
    """
    Load features CSV and make predictions for all samples
    
    Input CSV format (from feature_extraction):
        text,source,feature_0,feature_1,...,feature_388
        "article1","reuters",0.234,-0.456,...,0.789
        "article2","unknown",0.123,0.456,...,0.234
    
    Output CSV format:
        text,source,prediction,confidence,fake_prob,real_prob
        "article1","reuters",1,0.87,0.13,0.87
        "article2","unknown",0,0.76,0.76,0.24
    
    where:
        prediction: 0=FAKE, 1=REAL
        confidence: max(fake_prob, real_prob)
        fake_prob: probability of being FAKE
        real_prob: probability of being REAL
    
    Args:
        features_csv_path (str): Path to features CSV
        model_path (str): Path to XGBoost model
        output_csv_path (str): Path to save predictions CSV
    
    Returns:
        str: Path to output CSV
    """
    
    print("="*70)
    print("MODEL PREDICTION")
    print("="*70)
    
    # 1. Load model
    print(f"\n1. Loading model from: {model_path}")
    model = load_model(model_path)
    
    # 2. Load features
    print(f"\n2. Loading features from: {features_csv_path}")
    df = pd.read_csv(features_csv_path)
    
    # Extract text and source (first 2 columns)
    text_col = df['text'].values
    source_col = df['source'].values
    
    # Extract feature columns (rest of the columns)
    feature_cols = [col for col in df.columns if col.startswith('feature_')]
    features = df[feature_cols].values
    
    print(f"   Loaded: {len(df)} samples")
    print(f"   Features: {features.shape[1]} dimensions")
    
    # 3. Make predictions
    print(f"\n3. Making predictions...")
    
    predictions_list = []
    
    for idx, feature_vector in enumerate(features):
        if (idx + 1) % 100 == 0:
            print(f"   Progress: {idx + 1}/{len(features)}")
        
        pred_dict = predict_single(feature_vector, model)
        predictions_list.append(pred_dict)
    
    print(f"   ✓ Predictions complete")
    
    # 4. Create output DataFrame
    print(f"\n4. Creating output DataFrame...")
    
    predictions_df = pd.DataFrame(predictions_list)
    
    # Add text and source columns
    predictions_df.insert(0, 'source', source_col)
    predictions_df.insert(0, 'text', text_col)
    
    # Convert prediction to label
    predictions_df['prediction_label'] = predictions_df['prediction'].apply(
        lambda x: 'REAL' if x == 1 else 'FAKE'
    )
    
    # Reorder columns
    predictions_df = predictions_df[[
        'text', 'source', 'prediction', 'prediction_label',
        'confidence', 'fake_prob', 'real_prob'
    ]]
    
    print(f"   ✓ DataFrame created: {predictions_df.shape}")
    
    # 5. Save to CSV
    abs_output_path = os.path.abspath(output_csv_path)
    print(f"\n5. Saving to: {abs_output_path}")
    predictions_df.to_csv(abs_output_path, index=False)
    
    print(f"   ✓ Predictions saved")
    print(f"   📁 File location: {abs_output_path}")
    
    # 6. Summary statistics
    print(f"\n6. Prediction Summary:")
    real_count = (predictions_df['prediction'] == 1).sum()
    fake_count = (predictions_df['prediction'] == 0).sum()
    avg_confidence = predictions_df['confidence'].mean()
    
    print(f"   REAL predictions: {real_count} ({real_count/len(predictions_df)*100:.1f}%)")
    print(f"   FAKE predictions: {fake_count} ({fake_count/len(predictions_df)*100:.1f}%)")
    print(f"   Average confidence: {avg_confidence:.4f}")
    
    print("\n" + "="*70)
    print("PREDICTION COMPLETE")
    print("="*70)
    
    return output_csv_path

# ============================================================
# PART 4: UNCERTAINTY HANDLING
# ============================================================

def classify_with_uncertainty(confidence, threshold=0.65):
    """
    Classify prediction as confident or uncertain
    
    If max probability < threshold → UNCERTAIN
    Else → use prediction label
    
    Args:
        confidence (float): Max probability (0-1)
        threshold (float): Uncertainty threshold (default 0.65)
    
    Returns:
        str: 'UNCERTAIN', 'REAL', or 'FAKE'
    """
    if confidence < threshold:
        return 'UNCERTAIN'
    # Prediction label should be passed separately, this is just classification logic
    return None

# ============================================================
# PART 5: BATCH UNCERTAINTY CLASSIFICATION
# ============================================================

def add_uncertainty_classification(predictions_csv_path, threshold=0.65, 
                                   output_csv_path='predictions_with_uncertainty.csv'):
    """
    Add uncertainty classification to predictions CSV
    
    Args:
        predictions_csv_path (str): Path to predictions CSV (from predict_from_csv)
        threshold (float): Confidence threshold for uncertainty (default 0.65)
        output_csv_path (str): Path to save updated CSV
    
    Returns:
        str: Path to output CSV
    """
    print(f"\nAdding uncertainty classification (threshold={threshold})...")
    
    df = pd.read_csv(predictions_csv_path)
    
    # Classify as certain or uncertain
    df['classification'] = df.apply(
        lambda row: 'UNCERTAIN' if row['confidence'] < threshold 
                    else row['prediction_label'],
        axis=1
    )
    
    # Count classifications
    uncertain = (df['classification'] == 'UNCERTAIN').sum()
    confident = len(df) - uncertain
    
    print(f"   Confident predictions: {confident}")
    print(f"   Uncertain predictions: {uncertain}")
    
    # Save
    abs_output_path = os.path.abspath(output_csv_path)
    df.to_csv(abs_output_path, index=False)
    print(f"   ✓ Saved to: {abs_output_path}")
    print(f"   📁 File location: {abs_output_path}")
    
    return abs_output_path

# ============================================================
# PART 6: MODEL INFORMATION
# ============================================================

def get_model_info(model_path=DEFAULT_MODEL_PATH):
    """
    Get information about the model
    
    Returns:
        dict: Model metadata
    """
    model = load_model(model_path)
    
    return {
        'model_type': 'XGBoost',
        'n_estimators': model.n_estimators,
        'max_depth': model.max_depth,
        'learning_rate': model.learning_rate,
        'n_classes': 2,  # FAKE and REAL
        'input_features': 389
    }

