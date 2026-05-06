#!/usr/bin/env python3
"""
Wave Modulation Qualitative Analysis Agent

Wraps GPT-4o to provide qualitative interpretation of Wave Modulation Machine results.

Purpose:
    - Convert quantitative flow metrics to qualitative insights
    - Identify patterns, anomalies, and structural features
    - Provide musical/performative context
    - Flag areas for investigation or improvement

Model: GPT-4o (gpt-4o) - "5.1" designation
Philosophy: Quantitative structure → Qualitative understanding
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

import openai


# ========================================
# Agent Configuration
# ========================================

WAVE_MODULATION_AGENT_SYSTEM_PROMPT = """You are a qualitative analysis agent for the Wave Modulation Machine.

Your role:
- Interpret quantitative flow metrics (coherence, lock strength, tempo stability)
- Provide musical and performative context
- Identify patterns, anomalies, and structural features
- Offer insights without aesthetic judgment
- Flag areas for investigation or improvement

Key principles:
- Structure > aesthetics: Analyze flow, not quality
- Honesty > performance: First playthrough is baseline, not failure
- Quantitative → Qualitative: Translate metrics to insights
- No judgment: "Low coupling" = exploration, not error

Input format:
You will receive Wave Modulation Machine output as JSON with:
- Guitar stream metrics (tempo, beat count)
- Vocal stream metrics (onset count, inferred tempo)
- Alignment metrics (coherence, lock strength, tempo stability)
- Challenge sections (timestamps, coherence scores)

Output format:
Provide qualitative analysis in markdown with sections:
1. Overall Flow Assessment
2. Rhythmic Foundation Analysis
3. Structural Patterns Identified
4. Anomalies & Investigations
5. Musical Context
6. Performative Insights
7. Next Steps (if applicable)

Tone: Technical, grounded, honest. No flowery language or aesthetic praise/criticism.
Focus: What the numbers reveal about structural coupling and flow dynamics.
"""


# ========================================
# Core Functions
# ========================================

def call_wave_modulation_agent(metrics: Dict[str, Any], context: str = "") -> str:
    """
    Call GPT-4o to provide qualitative analysis of wave modulation results.
    
    Args:
        metrics: Flow metrics from Wave Modulation Machine
        context: Optional additional context (e.g., "first playthrough", "learning bridge")
        
    Returns:
        Qualitative analysis as markdown string
    """
    # Prepare user message
    user_message = f"""Analyze these Wave Modulation Machine results:

```json
{json.dumps(metrics, indent=2)}
```

Additional context: {context if context else "None provided"}

Provide qualitative analysis following the specified output format.
"""
    
    # Call GPT-4o
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": WAVE_MODULATION_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,  # Fairly deterministic for technical analysis
        max_tokens=2000
    )
    
    return response.choices[0].message.content


def format_metrics_for_agent(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format Wave Modulation Machine report for agent consumption.
    
    Args:
        report: Complete flow report from generate_flow_report()
        
    Returns:
        Formatted metrics dict suitable for JSON serialization
    """
    # Extract and format key metrics
    metrics = {
        "guitar": {
            "tempo_bpm": float(report['guitar_tempo']),
            "beat_count": int(report['guitar_beats']),
            "duration_seconds": float(report['duration'])
        },
        "vocals": {
            "onset_count": int(report['vocal_onsets']),
            "inferred_tempo_bpm": float(report['vocal_tempo']),
        },
        "alignment": {
            "overall_coherence": float(report['overall_coherence']),
            "quality_classification": report['quality_classification'],
            "tempo_stability": float(report['tempo_stability']),
            "tempo_delta_bpm": abs(float(report['guitar_tempo']) - float(report['vocal_tempo']))
        },
        "structural_coupling": {
            "lock_strength": float(report['structural_lock']['lock_strength']),
            "tight_locks_count": int(report['structural_lock']['tight_locks']),
            "loose_locks_count": int(report['structural_lock']['loose_locks']),
            "avg_lock_distance_seconds": float(report['structural_lock']['avg_lock_distance']),
            "tight_coupling_percentage": round(
                (int(report['structural_lock']['tight_locks']) / int(report['vocal_onsets'])) * 100, 1
            )
        },
        "challenge_sections": [
            {
                "start_time": float(section['start']),
                "end_time": float(section['end']),
                "coherence": float(section['coherence']),
                "description": section['description']
            }
            for section in report['challenge_sections'][:5]  # Limit to top 5
        ]
    }
    
    return metrics


def save_qualitative_analysis(analysis: str, output_path: Path):
    """Save qualitative analysis to markdown file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(analysis, encoding='utf-8')
    print(f"\n✅ Qualitative analysis saved to: {output_path}")


# ========================================
# Main Execution
# ========================================

def main():
    """
    Run qualitative analysis on Wave Modulation Machine results.
    
    Usage:
        python3 wave_modulation_agent.py <report_json_file> [context]
        
    Example:
        python3 wave_modulation_agent.py results.json "first playthrough, learning bridge"
    """
    if len(sys.argv) < 2:
        print("Usage: python3 wave_modulation_agent.py <report_json_file> [context]")
        print()
        print("Example:")
        print('  python3 wave_modulation_agent.py results.json "first playthrough"')
        sys.exit(1)
    
    report_path = Path(sys.argv[1])
    context = sys.argv[2] if len(sys.argv) > 2 else ""
    
    if not report_path.exists():
        print(f"❌ Error: Report file not found: {report_path}")
        sys.exit(1)
    
    try:
        # Load report
        print(f"📊 Loading report: {report_path.name}")
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        # Format metrics
        print("🔄 Formatting metrics for agent...")
        metrics = format_metrics_for_agent(report)
        
        # Call agent
        print("🤖 Calling Wave Modulation Agent (GPT-4o)...")
        analysis = call_wave_modulation_agent(metrics, context)
        
        # Display analysis
        print("\n" + "="*60)
        print("QUALITATIVE ANALYSIS")
        print("="*60)
        print()
        print(analysis)
        print()
        print("="*60)
        
        # Save analysis
        output_path = report_path.parent / f"{report_path.stem}_QUALITATIVE_ANALYSIS.md"
        save_qualitative_analysis(analysis, output_path)
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in report file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

