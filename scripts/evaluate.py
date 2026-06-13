"""
JARVIS Evaluation Framework (US-016) and Radar Chart (US-017).

Evaluates JARVIS rule-engine output against a pre-recorded ChatGPT baseline
across 5 standardized test scenarios and 5 quality dimensions.

Usage:
    python scripts/evaluate.py
"""

import re
import sys
from pathlib import Path

import yaml

# Add src to path so we can import jarvis modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jarvis.engine.intent import recognize, IntentResult
from jarvis.engine.rule_engine import generate_prep_fallback
from jarvis.knowledge.loader import load_all
from jarvis.models.prep_package import PrepPackage

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EVAL_DIR = DATA_DIR / "eval"
DOCS_DIR = PROJECT_ROOT / "docs"

# ---------------------------------------------------------------------------
# Standardized test scenarios
# ---------------------------------------------------------------------------
TEST_SCENARIOS = [
    {
        "id": "manufacturing_ransomware",
        "industry": "manufacturing",
        "scenario": "ransomware",
        "input": "明天去见制造业客户，产线被勒索了",
    },
    {
        "id": "finance_compliance",
        "industry": "finance",
        "scenario": "compliance",
        "input": "金融行业合规审计准备，讨论数据泄露风险",
    },
    {
        "id": "healthcare_data_leak",
        "industry": "healthcare",
        "scenario": "data_leak",
        "input": "医疗客户担心患者数据泄露",
    },
    {
        "id": "technology_apt",
        "industry": "technology",
        "scenario": "apt",
        "input": "科技公司面临APT高级持续性威胁",
    },
    {
        "id": "education_phishing",
        "industry": "education",
        "scenario": "phishing",
        "input": "教育机构遭受钓鱼邮件攻击",
    },
]

# Dimension labels (Chinese) for reporting and charts
DIMENSIONS = {
    "structure": "结构性",
    "professionalism": "专业性",
    "practicality": "实用性",
    "depth": "深度",
    "completeness": "完整性",
}

# ---------------------------------------------------------------------------
# Industry / scenario keyword dictionaries for professionalism scoring
# ---------------------------------------------------------------------------
INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "manufacturing": [
        "ot", "ics", "scada", "plc", "production", "factory", "manufacturing",
        "industrial", "segmentation", "firmware", "hmi", "ops",
    ],
    "finance": [
        "compliance", "audit", "regulatory", "sox", "pci", "grc", "dlp",
        "siem", "financial", "banking", "risk", "control",
    ],
    "healthcare": [
        "hipaa", "phi", "ehr", "emr", "patient", "clinical", "medical",
        "healthcare", "breach", "encryption", "access",
    ],
    "technology": [
        "apt", "threat", "intelligence", "ioc", "ttp", "lateral", "c2",
        "exfiltration", "persistent", "sophisticated", "zero-day",
    ],
    "education": [
        "phishing", "email", "credential", "social engineering", "awareness",
        "training", "simulation", "spam", "spear", "education",
    ],
}

GENERAL_CYBER_KEYWORDS = [
    "security", "threat", "vulnerability", "incident", "breach", "attack",
    "defense", "protection", "response", "recovery", "risk", "endpoint",
    "network", "detection", "monitoring", "firewall", "edr", "siem",
    "ransomware", "malware", "encryption", "backup", "segment",
]


# ===========================================================================
# Scoring functions
# ===========================================================================

def _module_text_length(pkg: PrepPackage) -> dict[str, int]:
    """Return character length of each module's content."""
    return {
        "scenario_assessment": len(pkg.scenario_assessment),
        "sensitivity_alerts": sum(len(a) for a in pkg.sensitivity_alerts),
        "matched_cases": sum(len(c) for c in pkg.matched_cases),
        "follow_up_questions": sum(len(q) for q in pkg.follow_up_questions),
        "solution_direction": len(pkg.solution_direction),
        "talking_points": len(pkg.talking_points),
    }


def score_structure(pkg: PrepPackage) -> float:
    """Score structural completeness of the 6 modules (0-10).

    Checks if all 6 modules are non-empty and substantive.
    """
    lengths = _module_text_length(pkg)

    # Each module contributes up to ~1.5 points based on presence + substance
    module_score = 0.0
    thresholds = {
        "scenario_assessment": 30,
        "sensitivity_alerts": 20,
        "matched_cases": 5,
        "follow_up_questions": 20,
        "solution_direction": 20,
        "talking_points": 20,
    }

    for module_name, min_len in thresholds.items():
        length = lengths.get(module_name, 0)
        if length == 0:
            continue
        # Partial credit: present but thin
        if length < min_len:
            module_score += 0.75
        else:
            module_score += 1.5

    # Bonus for threat_intel (optional 7th module)
    if pkg.threat_intel:
        module_score += 1.0

    return min(10.0, round(module_score, 1))


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count keyword hits using word-boundary matching to avoid false positives.

    For example, 'ot' should match 'OT security' but not 'protection'.
    """
    hits = 0
    for kw in keywords:
        # Use word-boundary regex for accurate matching
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            hits += 1
    return hits


def score_professionalism(pkg: PrepPackage, industry: str) -> float:
    """Score cybersecurity domain specificity (0-10).

    Checks for industry-specific and general cybersecurity keywords.
    """
    # Gather all text from the package
    all_text = " ".join([
        pkg.scenario_assessment,
        " ".join(pkg.sensitivity_alerts),
        " ".join(pkg.follow_up_questions),
        pkg.solution_direction,
        pkg.talking_points,
    ]).lower()

    # Count industry-specific keyword hits using word-boundary matching
    industry_kws = INDUSTRY_KEYWORDS.get(industry, [])
    industry_hits = _count_keyword_hits(all_text, industry_kws)
    industry_max = max(len(industry_kws), 1)
    # Require at least 50% keyword coverage for full marks on this component
    industry_ratio = min(industry_hits / (industry_max * 0.5), 1.0)

    # Count general cybersecurity keyword hits
    general_hits = _count_keyword_hits(all_text, GENERAL_CYBER_KEYWORDS)
    # Require 50% of general keywords for full marks
    general_ratio = min(general_hits / (len(GENERAL_CYBER_KEYWORDS) * 0.5), 1.0)

    # Weighted combination: 60% industry-specific, 40% general
    raw = industry_ratio * 0.6 + general_ratio * 0.4
    score = raw * 10.0
    return min(10.0, round(score, 1))


def score_practicality(pkg: PrepPackage) -> float:
    """Score actionability for a salesperson (0-10).

    Evaluates follow-up questions, talking points structure, and solution clarity.
    """
    score = 0.0

    # Follow-up questions: more is better (up to 3.5 points)
    q_count = len(pkg.follow_up_questions)
    if q_count >= 11:
        score += 3.5
    elif q_count >= 9:
        score += 3.0
    elif q_count >= 7:
        score += 2.5
    elif q_count >= 5:
        score += 2.0
    elif q_count >= 3:
        score += 1.5
    elif q_count >= 1:
        score += 0.5

    # Check if questions cover multiple dimensions (up to 2 points)
    dimensions_covered = set()
    for q in pkg.follow_up_questions:
        for dim in ["environment", "time", "asset", "budget"]:
            if dim in q.lower():
                dimensions_covered.add(dim)
    score += len(dimensions_covered) * 0.5  # up to 2.0

    # Talking points structure: check for opening/empathy/anchoring (up to 3 points)
    tp_lower = pkg.talking_points.lower()
    for keyword in ["opening", "empathy", "anchoring"]:
        if keyword in tp_lower:
            score += 1.0

    # Solution direction has actionable content (up to 1.5 points)
    sol_len = len(pkg.solution_direction)
    if sol_len > 200:
        score += 1.5
    elif sol_len > 100:
        score += 1.0
    elif sol_len > 50:
        score += 0.5

    return min(10.0, round(score, 1))


def score_depth(pkg: PrepPackage) -> float:
    """Score detail level and insight depth (0-10).

    Based on content volume and richness across all modules.
    """
    lengths = _module_text_length(pkg)
    total_chars = sum(lengths.values())

    # Base score from total content volume - raised thresholds for discrimination
    # 0-300 chars = 1-2, 300-800 = 3-4, 800-1500 = 5-6, 1500-3000 = 7-8, 3000+ = 9-10
    if total_chars >= 3000:
        volume_score = 8.5 + min((total_chars - 3000) / 3000, 1.5)
    elif total_chars >= 1500:
        volume_score = 6.5 + (total_chars - 1500) / 750
    elif total_chars >= 800:
        volume_score = 4.5 + (total_chars - 800) / 350
    elif total_chars >= 300:
        volume_score = 2.5 + (total_chars - 300) / 250
    else:
        volume_score = 1.0 + total_chars / 200

    # Bonus for non-empty matched cases (real case data adds depth)
    if pkg.matched_cases and len(pkg.matched_cases) > 0:
        case_ids_with_data = [c for c in pkg.matched_cases if c and c != ""]
        if case_ids_with_data:
            volume_score += 0.5

    # Bonus for rich follow-up questions (long, detailed questions)
    avg_q_len = (
        sum(len(q) for q in pkg.follow_up_questions) / max(len(pkg.follow_up_questions), 1)
    )
    if avg_q_len > 100:
        volume_score += 1.0
    elif avg_q_len > 70:
        volume_score += 0.5

    return min(10.0, round(volume_score, 1))


def score_completeness(pkg: PrepPackage) -> float:
    """Score coverage of all required aspects (0-10).

    Checks population of matched_cases, threat_intel, sensitivity, and
    multi-dimensional follow-up questions.
    """
    score = 0.0

    # matched_cases populated (up to 2 points)
    real_cases = [c for c in pkg.matched_cases if c and "No " not in c]
    if len(real_cases) >= 2:
        score += 2.0
    elif len(real_cases) >= 1:
        score += 1.5
    else:
        score += 0.5  # at least the field exists

    # sensitivity_alerts has meaningful content (up to 2 points)
    real_alerts = [a for a in pkg.sensitivity_alerts if a and "No specific" not in a]
    if len(real_alerts) >= 4:
        score += 2.0
    elif len(real_alerts) >= 2:
        score += 1.5
    elif len(real_alerts) >= 1:
        score += 1.0

    # follow_up_questions cover multiple dimensions (up to 2 points)
    dimensions_covered = set()
    for q in pkg.follow_up_questions:
        for dim in ["environment", "time", "asset", "budget"]:
            if dim in q.lower():
                dimensions_covered.add(dim)
    score += len(dimensions_covered) * 0.5

    # scenario_assessment is substantive (up to 2 points)
    if len(pkg.scenario_assessment) > 100:
        score += 2.0
    elif len(pkg.scenario_assessment) > 50:
        score += 1.5
    elif len(pkg.scenario_assessment) > 20:
        score += 1.0

    # threat_intel populated (up to 2 points)
    if len(pkg.threat_intel) >= 3:
        score += 2.0
    elif len(pkg.threat_intel) >= 1:
        score += 1.0
    else:
        score += 0.0  # empty in fallback mode

    return min(10.0, round(score, 1))


# ===========================================================================
# Evaluation pipeline
# ===========================================================================

def load_chatgpt_baseline() -> dict:
    """Load ChatGPT baseline scores from YAML."""
    baseline_path = EVAL_DIR / "chatgpt_baseline.yaml"
    with open(baseline_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def evaluate_scenario(scenario: dict, kb) -> dict:
    """Run JARVIS on a single scenario and score the output."""
    # Step 1: Recognize intent
    intent: IntentResult = recognize(scenario["input"])

    # Step 2: Generate Prep package via rule engine
    pkg: PrepPackage = generate_prep_fallback(intent, kb)

    # Step 3: Score across 5 dimensions
    scores = {
        "structure": score_structure(pkg),
        "professionalism": score_professionalism(pkg, scenario["industry"]),
        "practicality": score_practicality(pkg),
        "depth": score_depth(pkg),
        "completeness": score_completeness(pkg),
    }

    return {
        "scenario_id": scenario["id"],
        "input": scenario["input"],
        "intent_industry": intent.industry,
        "intent_scenario": intent.scenario,
        "scores": scores,
        "package": pkg,
    }


def generate_markdown_report(
    jarvis_results: list[dict],
    chatgpt_baseline: dict,
) -> str:
    """Generate a Markdown evaluation report comparing JARVIS vs ChatGPT."""
    lines = [
        "# JARVIS vs ChatGPT Evaluation Report",
        "",
        "## Overview",
        "",
        f"- **Test scenarios**: {len(jarvis_results)}",
        f"- **Evaluation dimensions**: {len(DIMENSIONS)} ({', '.join(DIMENSIONS.values())})",
        "- **JARVIS engine**: Rule-based fallback (no LLM API)",
        "- **ChatGPT baseline**: Pre-recorded GPT-4 scores",
        "",
        "## Scenario Details",
        "",
    ]

    # Scenario descriptions
    for s in TEST_SCENARIOS:
        lines.append(f"- **{s['id']}**: {s['input']}")
    lines.append("")

    # Per-scenario comparison tables
    lines.append("## Per-Scenario Scores")
    lines.append("")

    for result in jarvis_results:
        sid = result["scenario_id"]
        cgpt_data = chatgpt_baseline["scenarios"].get(sid, {})
        cgpt_scores = cgpt_data.get("scores", {})

        lines.append(f"### {sid}")
        lines.append(f"**Input**: {result['input']}")
        lines.append(f"**Intent detected**: industry={result['intent_industry']}, scenario={result['intent_scenario']}")
        lines.append("")
        lines.append("| Dimension | JARVIS | ChatGPT | Delta |")
        lines.append("|-----------|--------|---------|-------|")

        for dim_key, dim_label in DIMENSIONS.items():
            j_score = result["scores"][dim_key]
            c_score = cgpt_scores.get(dim_key, 0)
            delta = j_score - c_score
            delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
            lines.append(f"| {dim_label} | {j_score:.1f} | {c_score:.1f} | {delta_str} |")

        lines.append("")

    # Summary table: averages
    lines.append("## Summary: Average Scores Across All Scenarios")
    lines.append("")
    lines.append("| Dimension | JARVIS (avg) | ChatGPT (avg) | Delta | Winner |")
    lines.append("|-----------|-------------|---------------|-------|--------|")

    jarvis_avgs = {}
    chatgpt_avgs = {}

    for dim_key in DIMENSIONS:
        j_vals = [r["scores"][dim_key] for r in jarvis_results]
        c_vals = [
            chatgpt_baseline["scenarios"][r["scenario_id"]]["scores"][dim_key]
            for r in jarvis_results
        ]
        j_avg = sum(j_vals) / len(j_vals)
        c_avg = sum(c_vals) / len(c_vals)
        jarvis_avgs[dim_key] = j_avg
        chatgpt_avgs[dim_key] = c_avg

        delta = j_avg - c_avg
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        winner = "JARVIS" if delta > 0 else ("ChatGPT" if delta < 0 else "Tie")
        lines.append(
            f"| {DIMENSIONS[dim_key]} | {j_avg:.1f} | {c_avg:.1f} | {delta_str} | {winner} |"
        )

    # Overall averages
    j_overall = sum(jarvis_avgs.values()) / len(jarvis_avgs)
    c_overall = sum(chatgpt_avgs.values()) / len(chatgpt_avgs)
    lines.append(f"| **Overall** | **{j_overall:.1f}** | **{c_overall:.1f}** | "
                 f"**{'+' if j_overall >= c_overall else ''}{j_overall - c_overall:.1f}** | "
                 f"**{'JARVIS' if j_overall >= c_overall else 'ChatGPT'}** |")
    lines.append("")

    # Key findings
    lines.append("## Key Findings")
    lines.append("")

    jarvis_wins = sum(1 for d in DIMENSIONS if jarvis_avgs[d] > chatgpt_avgs[d])
    chatgpt_wins = sum(1 for d in DIMENSIONS if chatgpt_avgs[d] > jarvis_avgs[d])

    lines.append(f"- JARVIS wins on **{jarvis_wins}** dimensions, ChatGPT wins on **{chatgpt_wins}**")
    lines.append(f"- JARVIS overall average: **{j_overall:.1f}** / ChatGPT overall average: **{c_overall:.1f}**")

    # Find JARVIS strongest advantage
    best_dim = max(DIMENSIONS, key=lambda d: jarvis_avgs[d] - chatgpt_avgs[d])
    lines.append(
        f"- JARVIS strongest advantage: **{DIMENSIONS[best_dim]}** "
        f"(+{jarvis_avgs[best_dim] - chatgpt_avgs[best_dim]:.1f})"
    )

    # Find ChatGPT strongest advantage
    worst_dim = min(DIMENSIONS, key=lambda d: jarvis_avgs[d] - chatgpt_avgs[d])
    gap = jarvis_avgs[worst_dim] - chatgpt_avgs[worst_dim]
    if gap < 0:
        lines.append(
            f"- ChatGPT strongest advantage: **{DIMENSIONS[worst_dim]}** "
            f"({gap:+.1f})"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Report generated by JARVIS Evaluation Framework (US-016)*")

    return "\n".join(lines)


# ===========================================================================
# Radar chart (US-017)
# ===========================================================================

def generate_radar_chart(
    jarvis_results: list[dict],
    chatgpt_baseline: dict,
) -> Path:
    """Generate a radar/spider chart comparing JARVIS vs ChatGPT.

    Uses matplotlib (not plotly) for reliable PNG export.
    Returns the path to the saved PNG.
    """
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np

    # Configure CJK font for Chinese labels
    cjk_font = None
    for font_name in ["Microsoft YaHei", "SimHei", "Noto Sans SC", "STSong"]:
        try:
            matplotlib.font_manager.findfont(font_name, fallback_to_default=False)
            cjk_font = font_name
            break
        except Exception:
            continue
    if cjk_font:
        plt.rcParams["font.sans-serif"] = [cjk_font, "DejaVu Sans"]
    else:
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    # Compute average scores per dimension
    dim_keys = list(DIMENSIONS.keys())
    dim_labels = [DIMENSIONS[k] for k in dim_keys]

    jarvis_avgs = []
    chatgpt_avgs = []
    for dk in dim_keys:
        j_vals = [r["scores"][dk] for r in jarvis_results]
        c_vals = [
            chatgpt_baseline["scenarios"][r["scenario_id"]]["scores"][dk]
            for r in jarvis_results
        ]
        jarvis_avgs.append(sum(j_vals) / len(j_vals))
        chatgpt_avgs.append(sum(c_vals) / len(c_vals))

    # Number of dimensions
    n = len(dim_keys)

    # Compute angles for each axis (evenly spaced around the circle)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()

    # Close the polygon by appending the first value/angle again
    jarvis_vals_closed = jarvis_avgs + [jarvis_avgs[0]]
    chatgpt_vals_closed = chatgpt_avgs + [chatgpt_avgs[0]]
    angles_closed = angles + [angles[0]]

    # Create the figure
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # Plot JARVIS (blue)
    ax.plot(angles_closed, jarvis_vals_closed, "o-", linewidth=2, color="#2563EB",
            label="JARVIS", markersize=8)
    ax.fill(angles_closed, jarvis_vals_closed, alpha=0.15, color="#2563EB")

    # Plot ChatGPT (orange/red)
    ax.plot(angles_closed, chatgpt_vals_closed, "s--", linewidth=2, color="#EA580C",
            label="ChatGPT", markersize=8)
    ax.fill(angles_closed, chatgpt_vals_closed, alpha=0.10, color="#EA580C")

    # Set axis labels (Chinese dimension names)
    ax.set_xticks(angles)
    ax.set_xticklabels(dim_labels, fontsize=13, fontweight="bold")

    # Set y-axis limits and ticks
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=9, color="gray")

    # Add score annotations for JARVIS
    for angle, val, label in zip(angles, jarvis_avgs, dim_labels):
        ax.annotate(
            f"{val:.1f}",
            xy=(angle, val),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            color="#2563EB",
            fontweight="bold",
        )

    # Add score annotations for ChatGPT
    for angle, val, label in zip(angles, chatgpt_avgs, dim_labels):
        ax.annotate(
            f"{val:.1f}",
            xy=(angle, val),
            xytext=(0, -16),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            color="#EA580C",
            fontweight="bold",
        )

    # Title and legend
    ax.set_title("JARVIS vs ChatGPT 评估对比", fontsize=18, fontweight="bold", pad=30)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=13)

    # Grid styling
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOCS_DIR / "evaluation_radar.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path


# ===========================================================================
# Main
# ===========================================================================

def main() -> int:
    """Run the full evaluation pipeline."""
    print("=" * 60)
    print("JARVIS Evaluation Framework (US-016 + US-017)")
    print("=" * 60)

    # Ensure eval directory exists
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    # Load knowledge base
    print("\n[1/5] Loading knowledge base...")
    kb = load_all()
    print(f"  Loaded: {len(kb.cases)} cases, {len(kb.methodologies)} methodologies, "
          f"{len(kb.sensitivities)} sensitivities, {len(kb.products)} products")

    # Load ChatGPT baseline
    print("\n[2/5] Loading ChatGPT baseline...")
    chatgpt_baseline = load_chatgpt_baseline()
    print(f"  Loaded scores for {len(chatgpt_baseline['scenarios'])} scenarios")

    # Run evaluation on each scenario
    print("\n[3/5] Evaluating JARVIS on 5 test scenarios...")
    jarvis_results = []
    for scenario in TEST_SCENARIOS:
        result = evaluate_scenario(scenario, kb)
        jarvis_results.append(result)
        scores_str = ", ".join(f"{k}={v:.1f}" for k, v in result["scores"].items())
        print(f"  [{result['scenario_id']}] Intent: {result['intent_industry']}/{result['intent_scenario']}")
        print(f"    Scores: {scores_str}")

    # Generate Markdown report
    print("\n[4/5] Generating evaluation report...")
    report = generate_markdown_report(jarvis_results, chatgpt_baseline)
    report_path = EVAL_DIR / "evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report saved to: {report_path}")

    # Generate radar chart
    print("\n[5/5] Generating radar chart...")
    try:
        chart_path = generate_radar_chart(jarvis_results, chatgpt_baseline)
        print(f"  Chart saved to: {chart_path}")
    except ImportError as e:
        print(f"  WARNING: Could not generate radar chart: {e}")
        print("  Install matplotlib: pip install matplotlib")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    dim_keys = list(DIMENSIONS.keys())
    print(f"\n{'Dimension':<20} {'JARVIS':>8} {'ChatGPT':>8} {'Delta':>8}")
    print("-" * 48)

    for dk in dim_keys:
        j_vals = [r["scores"][dk] for r in jarvis_results]
        c_vals = [
            chatgpt_baseline["scenarios"][r["scenario_id"]]["scores"][dk]
            for r in jarvis_results
        ]
        j_avg = sum(j_vals) / len(j_vals)
        c_avg = sum(c_vals) / len(c_vals)
        delta = j_avg - c_avg
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        print(f"{DIMENSIONS[dk]:<20} {j_avg:>8.1f} {c_avg:>8.1f} {delta_str:>8}")

    j_overall = sum(
        sum(r["scores"][dk] for r in jarvis_results) / len(jarvis_results)
        for dk in dim_keys
    ) / len(dim_keys)
    c_overall = sum(
        sum(chatgpt_baseline["scenarios"][r["scenario_id"]]["scores"][dk] for r in jarvis_results)
        / len(jarvis_results)
        for dk in dim_keys
    ) / len(dim_keys)

    overall_delta = j_overall - c_overall
    overall_str = f"+{overall_delta:.1f}" if overall_delta >= 0 else f"{overall_delta:.1f}"
    print("-" * 48)
    print(f"{'Overall':<20} {j_overall:>8.1f} {c_overall:>8.1f} {overall_str:>8}")
    print(f"\nWinner: {'JARVIS' if j_overall >= c_overall else 'ChatGPT'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
