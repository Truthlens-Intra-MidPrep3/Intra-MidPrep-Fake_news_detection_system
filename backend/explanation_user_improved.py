"""
EXPLANATION MODULE

Key improvements:
- Color-coded signals (🟢 🟡 🔴)
- Traffic light system
- Clear "Why it matters" statements
- CSV-safe formatting (preserves newlines with \n)
"""

import pandas as pd
import numpy as np
import os

# ============================================================
# HELPER: INTERPRET FEATURE VALUES
# ============================================================

def interpret_sentiment(sentiment_score):
    """
    Interpret TextBlob polarity (-1 .. +1).
    0 is neutral. Factual news normally sits between about -0.15 and +0.15.
    (Old code treated this value as 0..1, so a neutral +0.15 was "Very Negative".)
    Returns: (label, signal, reason)
    """
    s = float(sentiment_score)
    if s <= -0.5:
        return ("Very Negative", "🔴 RED FLAG", "Highly polarized language suggests potential bias")
    elif s <= -0.2:
        return ("Negative", "🟡 CAUTION", "Some negative language detected")
    elif s < 0.2:
        return ("Neutral", "🟢 CREDIBLE", "Balanced, factual tone")
    elif s < 0.5:
        return ("Positive", "🟡 CAUTION", "Some positive bias detected")
    else:
        return ("Very Positive", "🔴 RED FLAG", "Highly promotional language suggests bias")


def interpret_subjectivity(subjectivity_score):
    """
    Interpret subjectivity score (0-1)
    Returns: (label, signal, reason, icon)
    """
    opinion_pct = int(subjectivity_score * 100)
    fact_pct = 100 - opinion_pct
    
    if subjectivity_score < 0.2:
        return (f"Mostly FACTS ({fact_pct}%)", "🟢 CREDIBLE", "Real news is fact-based, not opinion-based", "✓")
    elif subjectivity_score < 0.4:
        return (f"Mostly FACTS with some opinion ({opinion_pct}%)", "🟢 CREDIBLE", "Good balance of facts and analysis", "✓")
    elif subjectivity_score < 0.6:
        return (f"BALANCED ({fact_pct}% facts, {opinion_pct}% opinion)", "🟡 CAUTION", "Mix of facts and opinion requires verification", "⚠")
    elif subjectivity_score < 0.8:
        return (f"Mostly OPINION ({opinion_pct}%)", "🔴 RED FLAG", "Opinion-heavy content may contain bias", "✗")
    else:
        return (f"Almost entirely OPINION ({opinion_pct}%)", "🔴 RED FLAG", "Pure opinion without factual basis", "✗")


def compute_grade_level(text):
    """Flesch-Kincaid grade level computed from the text itself."""
    try:
        import textstat
        return max(0.0, float(textstat.flesch_kincaid_grade(text)))
    except Exception:
        return None


def interpret_readability(grade):
    """
    Interpret Flesch-Kincaid GRADE LEVEL (e.g. 8.2).
    (The stored feature is Flesch reading EASE / 100, which is NOT a grade -
    the old code showed it as "Grade 0.6".)
    Returns: (label, complexity, signal, reason)
    """
    if grade is None:
        return ("Not measured", "Unknown", "🟢 CREDIBLE", "Not enough text to measure")
    if grade < 8:
        return (f"Simple (Grade {grade:.1f})", "Easy to understand", "🟢 CREDIBLE", "Professional journalists write clearly")
    elif grade < 12:
        return (f"Standard (Grade {grade:.1f})", "High-school level reading", "🟢 CREDIBLE", "Expected complexity for news")
    elif grade < 16:
        return (f"Complex (Grade {grade:.1f})", "Advanced vocabulary", "🟡 CAUTION", "May be intentionally obscuring simple ideas")
    else:
        return (f"Very Complex (Grade {grade:.1f})", "Highly technical", "🔴 RED FLAG", "Excessive complexity can hide weak arguments")


def interpret_exclamation(exclamation_ratio):
    """
    Interpret exclamation mark ratio (0-1)
    Returns: (count_desc, signal, icon)
    """
    pct = int(exclamation_ratio * 100)
    
    if exclamation_ratio == 0:
        return ("No exclamation marks (measured tone)", "🟢 CREDIBLE", "Professional journalism uses calm, measured language")
    elif exclamation_ratio < 0.02:
        return (f"Minimal ({pct}%)", "🟢 CREDIBLE", "Occasional emphasis is normal")
    elif exclamation_ratio < 0.05:
        return (f"Moderate ({pct}%)", "🟡 CAUTION", "More emphasis than typical news")
    else:
        return (f"Heavy ({pct}%)", "🔴 RED FLAG", "Excessive exclamation marks suggest sensationalism")


# Acronyms that are normal in news and must NOT count as "shouting"
_COMMON_ACRONYMS = {
    "ODI", "T20", "T20I", "IPL", "BCCI", "ICC", "WHO", "UN", "UK", "US", "USA", "UAE", "EU", "NATO",
    "NASA", "ISRO", "FBI", "CIA", "GDP", "CEO", "CFO", "AI", "IT", "TV", "PM", "MP", "MLA", "RBI",
    "SEBI", "NSE", "BSE", "GST", "PDF", "COVID", "HIV", "AIDS", "DNA", "FIFA", "NBA", "NFL", "NHL",
    "MLB", "WTO", "IMF", "OPEC", "ATM", "SUV", "CBI", "ED", "AAP", "BJP", "INC", "DMK", "ADMK", "AIADMK",
    "IST", "EST", "PST", "GMT", "UTC", "OK", "II", "III", "IV", "TN", "AP", "UP", "MP", "HC", "SC",
}
# Short all-caps words that ARE used to shout
_SHOUT_SHORT = {"NO", "NOT", "ALL", "YOU", "NOW", "WOW", "LIE", "LIES", "WAKE", "UP", "STOP", "WHY", "HOW", "YES"}


def shouted_words(text):
    """Return (shouted_word_list, total_word_count) - ALL-CAPS emphasis words in the text."""
    import re
    words = re.findall(r"[A-Za-z][A-Za-z0-9']*", text or "")
    shouted = []
    for w in words:
        if len(w) < 2 or not w.isupper():
            continue
        if w in _COMMON_ACRONYMS:
            continue
        if len(w) >= 4 or w in _SHOUT_SHORT:
            shouted.append(w)
    return shouted, max(len(words), 1)


def interpret_capitalization(text):
    """
    Judge capitalization from ALL-CAPS *words* (e.g. "SHOCKING", "BREAKING").
    The stored uppercase_ratio feature counts every capital LETTER, so ordinary
    sentence starts and names (~3-5%) used to be flagged as "excessive caps".
    Returns: (label, signal, reason)
    """
    shouted, total = shouted_words(text)
    n = len(shouted)
    pct = n / total * 100
    if n == 0 or (n == 1 and pct < 5):
        return ("Normal", "🟢 CREDIBLE", "Professional writing follows standard grammar rules")
    elif pct < 5 or n < 3:
        return (f"Slightly elevated ({n} ALL-CAPS word{'s' if n != 1 else ''})", "🟡 CAUTION", "More caps than typical professional writing")
    else:
        return (f"High ({n} ALL-CAPS words, {pct:.0f}% of text)", "🔴 RED FLAG", "Excessive caps suggest aggressive tone")


# ============================================================
# MAIN EXPLANATION GENERATOR
# ============================================================

def generate_user_friendly_explanation(text, prediction_label, confidence, 
                                       sentiment, subjectivity, readability,
                                       exclamation_ratio, uppercase_ratio):
    """
    Generate a user-friendly explanation for a single prediction
    
    Args:
        text: Original article text
        prediction_label: "REAL" or "FAKE"
        confidence: Confidence score (0-1)
        sentiment: Sentiment score (0-1)
        subjectivity: Subjectivity score (0-1)
        readability: Readability score (grade level)
        exclamation_ratio: Exclamation mark ratio (0-1)
        uppercase_ratio: Uppercase word ratio (0-1)
    
    Returns:
        str: Multi-line explanation (CSV-safe with \n for newlines)
    """
    
    # Get interpretations
    sent_label, sent_signal, sent_reason = interpret_sentiment(sentiment)
    subj_label, subj_signal, subj_reason, _ = interpret_subjectivity(subjectivity)
    read_label, read_complex, read_signal, read_reason = interpret_readability(compute_grade_level(text))
    excl_label, excl_signal, excl_reason = interpret_exclamation(exclamation_ratio)
    caps_label, caps_signal, caps_reason = interpret_capitalization(text)
    
    # Count red flags
    red_flags = 0
    green_signals = 0
    
    if "RED FLAG" in sent_signal:
        red_flags += 1
    else:
        green_signals += 1
    
    if "RED FLAG" in subj_signal:
        red_flags += 1
    else:
        green_signals += 1
    
    if "RED FLAG" in excl_signal:
        red_flags += 1
    else:
        green_signals += 1
    
    if "RED FLAG" in caps_signal:
        red_flags += 1
    else:
        green_signals += 1
    
    # Build SHORT SUMMARY explanation - TEXT ONLY (no numbers)
    red_flag_list = []
    
    if "RED FLAG" in sent_signal:
        red_flag_list.append("emotional bias")
    if "RED FLAG" in subj_signal:
        red_flag_list.append("opinion-heavy")
    if "RED FLAG" in excl_signal:
        red_flag_list.append("sensationalism")
    if "RED FLAG" in caps_signal:
        red_flag_list.append("excessive caps")
    
    # Create concise text-only summary
    if red_flags == 0:
        summary = f"✓ CREDIBLE - Professional tone, fact-based, no red flags."
    elif red_flags == 1:
        summary = f"⚠ CAUTION - Minor concern: {', '.join(red_flag_list)}."
    elif red_flags == 2:
        summary = f"⚠ MIXED - Multiple concerns: {', '.join(red_flag_list)}."
    else:
        summary = f"✗ SUSPICIOUS - Multiple red flags: {', '.join(red_flag_list)}."
    
    # Add feature summary (text descriptions, no scores)
    explanation = (
        f"{summary} "
        f"Tone: {sent_label}. "
        f"Content: {subj_label}. "
        f"Readability: {read_label}. "
        f"Exclamation marks: {excl_label}. "
        f"Capitalization: {caps_label}. "
        f"[Analyzes STYLE only, not FACTS]"
    )
    
    return explanation


# ============================================================
# CSV BATCH PROCESSING
# ============================================================

def explain_predictions_improved_from_csv(predictions_csv, features_csv, output_csv):
    """
    Read predictions and features from CSV, generate explanations, save to CSV
    
    Args:
        predictions_csv: Path to predictions CSV (from model_prediction.py)
        features_csv: Path to features CSV (from feature_extraction.py)
        output_csv: Path to save explanations CSV
    """
    
    print("\n📋 GENERATING USER-FRIENDLY EXPLANATIONS...")
    
    # Load CSVs
    pred_df = pd.read_csv(predictions_csv)
    feat_df = pd.read_csv(features_csv)
    
    explanations = []
    
    # Generate explanation for each article
    for idx, row in pred_df.iterrows():
        
        if (idx + 1) % 50 == 0:
            print(f"   Progress: {idx + 1}/{len(pred_df)}")
        
        try:
            explanation = generate_user_friendly_explanation(
                text=row['text'],
                prediction_label=row['prediction_label'],
                confidence=row['confidence'],
                sentiment=feat_df.iloc[idx]['feature_768'],
                subjectivity=feat_df.iloc[idx]['feature_769'],
                readability=feat_df.iloc[idx]['feature_770'],
                exclamation_ratio=feat_df.iloc[idx]['feature_771'],
                uppercase_ratio=feat_df.iloc[idx]['feature_772']
            )
        except Exception as e:
            print(f"   Warning: Could not generate explanation for article {idx + 1}: {str(e)}")
            explanation = f"Error generating explanation: {str(e)}"
        
        explanations.append(explanation)
    
    # Create output DataFrame
    output_df = pred_df.copy()
    output_df['explanation'] = explanations
    
    # Save with proper CSV formatting to preserve newlines
    import csv
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    
    output_df.to_csv(
        output_csv,
        index=False,
        quoting=csv.QUOTE_ALL,
        quotechar='"',
        escapechar='\\',
        encoding='utf-8-sig'
    )
    
    abs_path = os.path.abspath(output_csv)
    print(f"\n✓ Explanations saved to: {abs_path}")
    print(f"  Rows: {len(output_df)}")
    
    return abs_path


# ============================================================
# DISPLAY FUNCTIONS (For console output)
# ============================================================

def display_explanation(explanation_text):
    """
    Display explanation in formatted console output
    
    Args:
        explanation_text: Explanation string (may contain \n)
    """
    # Replace \n with actual newlines for display
    formatted = explanation_text.replace('\\n', '\n')
    print(formatted)


# Export functions
__all__ = [
    'generate_user_friendly_explanation',
    'explain_predictions_improved_from_csv',
    'display_explanation'
]
