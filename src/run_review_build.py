"""Rebuild, validate, and prepare the basketball review layer."""

from export_analysis_outputs import export_analysis_outputs
from validate_review_outputs import validate_review_outputs


def run_review_build() -> None:
    """Run the full presentation-output build."""

    print("Rebuilding pregame analysis outputs.")
    export_analysis_outputs()

    print("\nValidating pregame review outputs.")
    validate_review_outputs()

    print("\nReview layer is ready.")
    print("Launch it with: streamlit run review_dashboard.py")


if __name__ == "__main__":
    run_review_build()
