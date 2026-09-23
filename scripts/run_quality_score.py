"""Command-line runner for the DataQualityScorer.

Usage:
    python scripts/run_quality_score.py [optional_path_to_dataset]
    python scripts/run_quality_score.py --compare data/raw/netflix_titles.csv data/sample/netflix_cleaned.csv
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.scorer import DataQualityScorer, ScoreWeights


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Evaluate dataset quality score using DataQualityScorer.")
    parser.add_argument(
        "filepath",
        nargs="?",
        default="data/raw/netflix_titles.csv",
        help="Path to dataset to evaluate",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("RAW_FILE", "CLEANED_FILE"),
        help="Compare quality scores between raw and cleaned versions",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/sample/netflix_quality_score.json",
        help="Output path for the score report JSON",
    )
    args = parser.parse_args()

    scorer = DataQualityScorer()

    if args.compare:
        raw_path, clean_path = Path(args.compare[0]), Path(args.compare[1])
        print(f"\n[DataQualityScorer] Comparing '{raw_path}' vs '{clean_path}'...")
        raw_df = pd.read_csv(raw_path)
        clean_df = pd.read_csv(clean_path)

        comparison = scorer.compare(
            raw_df,
            clean_df,
            id_columns=["show_id"] if "show_id" in raw_df.columns else None,
        )

        b = comparison.before
        a = comparison.after

        print("\n" + "=" * 65)
        print(" DATA QUALITY SCORE COMPARISON (BEFORE vs AFTER)")
        print("=" * 65)
        print(f"  Overall Score:    {b.overall_score:.1f}% (Grade {b.grade}) -> {a.overall_score:.1f}% (Grade {a.grade})")
        print(f"  Quality Delta:    {'+' if comparison.score_delta >= 0 else ''}{comparison.score_delta:.2f}%")
        print(f"  Grade Improved:   {'YES' if comparison.grade_improved else 'MAINTAINED'}")

        print("\n  Dimensional Scores Breakdown:")
        print(f"    {'Dimension':<15} | {'Before':<10} | {'After':<10} | {'Delta':<10}")
        print("    " + "-" * 50)
        for dim, b_dim in b.dimensions.items():
            a_dim = a.dimensions[dim]
            delta = a_dim.score - b_dim.score
            sign = "+" if delta >= 0 else ""
            print(f"    {b_dim.name:<15} | {b_dim.score:>6.1f}%    | {a_dim.score:>6.1f}%    | {sign}{delta:>6.1f}%")

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(comparison.to_json(indent=2))

        print(f"\n[DataQualityScorer] Comparison report exported to: {output_path}")
        print("=" * 65 + "\n")
        return

    # Single dataset scoring
    input_path = Path(args.filepath)
    if not input_path.exists():
        print(f"Error: File '{input_path}' not found.")
        sys.exit(1)

    print(f"\n[DataQualityScorer] Evaluating '{input_path}'...")
    df = pd.read_csv(input_path) if input_path.suffix.lower() == ".csv" else pd.read_excel(input_path)

    result = scorer.score(df, id_columns=["show_id"] if "show_id" in df.columns else None)

    print("\n" + "=" * 65)
    print(" DATA QUALITY SCORECARD")
    print("=" * 65)
    print(f"  Overall Quality Score:    {result.overall_score:.1f}%")
    print(f"  Letter Grade:             Grade {result.grade} ({result.grade_label})")
    print(f"  Analytics Trustworthy:    {'YES - Certified Safe' if result.is_trustworthy else 'NO - Requires Cleaning'}")

    print("\n  Dimensional Breakdown:")
    for dim_key, dim in result.dimensions.items():
        print(f"    - {dim.name:<14} : {dim.score:>5.1f}% (Weight: {dim.weight * 100:.0f}%, Contrib: {dim.weighted_score:>4.1f} pts)")
        print(f"      Details: {dim.details}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.to_json(indent=2))

    print(f"\n[DataQualityScorer] Scorecard exported to: {output_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
