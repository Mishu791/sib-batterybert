#!/usr/bin/env python3
"""
SIB-BatteryBERT — Annotation Comparison & Visualization
=========================================================
Compares rule-based (preannotated_1000.json) vs LLM (sib_annotated_llm.json)
and saves 4 charts to annotation/plots/.

Usage (run from project root):
    python annotation/scripts/compare_annotations.py

    # Custom paths:
    python annotation/scripts/compare_annotations.py \
        --rule  annotation/preannotated_1000.json \
        --llm   annotation/sib_annotated_llm.json \
        --out   annotation/plots
"""

import json
import argparse
from pathlib import Path
from collections import Counter

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Colour scheme ─────────────────────────────────────────────────────────────
RULE_COLOR = "#5DCAA5"   # teal   — rule-based
LLM_COLOR  = "#378ADD"   # blue   — LLM
BOTH_COLOR = "#1D9E75"   # dark teal — overlap
ONLY_COLOR = "#EF9F27"   # amber  — rule-only

LABEL_COLORS = {
    "MAT":    "#378ADD",
    "PROP":   "#5DCAA5",
    "STRUCT": "#7F77DD",
    "CHAR":   "#D85A30",
    "SYNTH":  "#D4537E",
    "APP":    "#888780",
}

LABEL_ORDER = ["MAT", "PROP", "STRUCT", "CHAR", "SYNTH", "APP"]

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.25,
    "grid.linestyle":   "--",
    "figure.dpi":       150,
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def load(path: str) -> list:
    return json.loads(Path(path).read_text())


def get_spans(task: dict) -> list:
    preds = task.get("predictions", [])
    if not preds:
        return []
    return preds[0].get("result", [])


def label_counts(tasks: list) -> Counter:
    c = Counter()
    for t in tasks:
        for s in get_spans(t):
            label = s.get("value", {}).get("labels", ["?"])[0]
            c[label] += 1
    return c


def coverage_stats(tasks: list):
    covered = sum(1 for t in tasks if get_spans(t))
    total   = len(tasks)
    spans   = sum(len(get_spans(t)) for t in tasks)
    return covered, total, spans


def overlap_stats(rule_tasks, llm_tasks):
    both     = sum(1 for r, l in zip(rule_tasks, llm_tasks) if get_spans(r) and get_spans(l))
    llm_only = sum(1 for r, l in zip(rule_tasks, llm_tasks) if not get_spans(r) and get_spans(l))
    rule_only= sum(1 for r, l in zip(rule_tasks, llm_tasks) if get_spans(r) and not get_spans(l))
    neither  = sum(1 for r, l in zip(rule_tasks, llm_tasks) if not get_spans(r) and not get_spans(l))
    return both, llm_only, rule_only, neither


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_label_distribution(rule_counts, llm_counts, out_dir: Path):
    labels = LABEL_ORDER
    x      = np.arange(len(labels))
    w      = 0.35

    rule_vals = [rule_counts.get(l, 0) for l in labels]
    llm_vals  = [llm_counts.get(l, 0)  for l in labels]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars_r = ax.bar(x - w/2, rule_vals, w, label="Rule-based", color=RULE_COLOR, zorder=3)
    bars_l = ax.bar(x + w/2, llm_vals,  w, label="LLM (Claude)", color=LLM_COLOR, zorder=3)

    for bar in bars_r:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9, color="#444")
    for bar in bars_l:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9, color="#444")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Span count", fontsize=11)
    ax.set_title("Label distribution — rule-based vs LLM", fontsize=13, pad=12)
    ax.legend(framealpha=0.4)
    plt.tight_layout()
    path = out_dir / "01_label_distribution.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved → {path}")


def plot_coverage_overview(rule_tasks, llm_tasks, out_dir: Path):
    r_cov, total, r_spans = coverage_stats(rule_tasks)
    l_cov, _,     l_spans = coverage_stats(llm_tasks)

    categories = ["sentences\nwith spans", "total\nspans", "avg spans\nper sentence"]
    rule_vals  = [r_cov,  r_spans, round(r_spans / total, 2)]
    llm_vals   = [l_cov,  l_spans, round(l_spans / total, 2)]

    x = np.arange(len(categories))
    w = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w/2, rule_vals, w, label="Rule-based", color=RULE_COLOR, zorder=3)
    ax.bar(x + w/2, llm_vals,  w, label="LLM (Claude)", color=LLM_COLOR, zorder=3)

    for i, (rv, lv) in enumerate(zip(rule_vals, llm_vals)):
        ax.text(i - w/2, rv + max(llm_vals)*0.01, str(rv), ha="center", va="bottom", fontsize=10)
        ax.text(i + w/2, lv + max(llm_vals)*0.01, str(lv), ha="center", va="bottom", fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_title("Coverage overview — rule-based vs LLM", fontsize=13, pad=12)
    ax.legend(framealpha=0.4)
    plt.tight_layout()
    path = out_dir / "02_coverage_overview.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved → {path}")


def plot_sentence_overlap(rule_tasks, llm_tasks, out_dir: Path):
    both, llm_only, rule_only, neither = overlap_stats(rule_tasks, llm_tasks)

    categories = ["LLM only\n(rules missed)", "both found\nspans", "rules only\n(LLM missed)", "neither\nfound spans"]
    values     = [llm_only, both, rule_only, neither]
    colors     = [LLM_COLOR, BOTH_COLOR, ONLY_COLOR, "#B4B2A9"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(categories, values, color=colors, zorder=3, width=0.5)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                str(val), ha="center", va="bottom", fontsize=11, fontweight="bold")

    total = sum(values)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
                f"{val/total*100:.1f}%", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")

    ax.set_ylabel("Sentences", fontsize=11)
    ax.set_title("Sentence-level annotation overlap", fontsize=13, pad=12)
    plt.tight_layout()
    path = out_dir / "03_sentence_overlap.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved → {path}")


def plot_label_pie_comparison(rule_counts, llm_counts, out_dir: Path):
    labels = [l for l in LABEL_ORDER if rule_counts.get(l, 0) + llm_counts.get(l, 0) > 0]
    colors = [LABEL_COLORS[l] for l in labels]

    rule_vals = [rule_counts.get(l, 0) for l in labels]
    llm_vals  = [llm_counts.get(l, 0)  for l in labels]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

    def make_pie(ax, vals, title):
        non_zero = [(v, l, c) for v, l, c in zip(vals, labels, colors) if v > 0]
        if not non_zero:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return
        v, l, c = zip(*non_zero)
        wedges, texts, autotexts = ax.pie(
            v, labels=l, colors=c,
            autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
            startangle=140, pctdistance=0.75,
            wedgeprops={"linewidth": 1, "edgecolor": "white"}
        )
        for t in texts:
            t.set_fontsize(10)
        for at in autotexts:
            at.set_fontsize(8)
            at.set_color("white")
            at.set_fontweight("bold")
        ax.set_title(title, fontsize=12, pad=10)

    make_pie(ax1, rule_vals, f"Rule-based\n({sum(rule_vals)} spans)")
    make_pie(ax2, llm_vals,  f"LLM (Claude)\n({sum(llm_vals)} spans)")

    plt.suptitle("Label composition — rule-based vs LLM", fontsize=13, y=1.01)
    plt.tight_layout()
    path = out_dir / "04_label_composition_pie.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved → {path}")


# ── Summary table ─────────────────────────────────────────────────────────────

def print_summary(rule_tasks, llm_tasks, rule_counts, llm_counts):
    r_cov, total, r_spans = coverage_stats(rule_tasks)
    l_cov, _,     l_spans = coverage_stats(llm_tasks)
    both, llm_only, rule_only, neither = overlap_stats(rule_tasks, llm_tasks)

    print("\n" + "="*60)
    print("  ANNOTATION COMPARISON SUMMARY")
    print("="*60)
    print(f"  {'Metric':<30} {'Rule-based':>12} {'LLM':>12}")
    print("-"*60)
    print(f"  {'Total sentences':<30} {total:>12} {total:>12}")
    print(f"  {'Sentences with spans':<30} {r_cov:>12} {l_cov:>12}")
    print(f"  {'Coverage %':<30} {r_cov/total*100:>11.1f}% {l_cov/total*100:>11.1f}%")
    print(f"  {'Total spans':<30} {r_spans:>12} {l_spans:>12}")
    print(f"  {'Avg spans / sentence':<30} {r_spans/total:>12.2f} {l_spans/total:>12.2f}")
    print("-"*60)
    print("  Label breakdown:")
    for label in LABEL_ORDER:
        rv = rule_counts.get(label, 0)
        lv = llm_counts.get(label, 0)
        print(f"    {label:<28} {rv:>12} {lv:>12}  ({lv-rv:+d})")
    print("-"*60)
    print("  Sentence overlap:")
    print(f"    {'Both found spans':<28} {both:>12}")
    print(f"    {'LLM only (rules missed)':<28} {llm_only:>12}")
    print(f"    {'Rules only (LLM missed)':<28} {rule_only:>12}")
    print(f"    {'Neither found':<28} {neither:>12}")
    print("="*60)
    print(f"\n  Recommendation: import  sib_annotated_llm.json  into Label Studio")
    print(f"  (LLM covers {l_cov/total*100:.0f}% of sentences vs {r_cov/total*100:.0f}% for rules)\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compare rule-based vs LLM annotations")
    parser.add_argument("--rule", default="annotation/preannotated_1000.json",
                        help="Path to rule-based JSON (default: annotation/preannotated_1000.json)")
    parser.add_argument("--llm",  default="annotation/sib_annotated_llm.json",
                        help="Path to LLM JSON (default: annotation/sib_annotated_llm.json)")
    parser.add_argument("--out",  default="annotation/plots",
                        help="Output directory for plots (default: annotation/plots)")
    args = parser.parse_args()

    # Load
    print(f"\nLoading {args.rule} ...")
    rule_tasks = load(args.rule)
    print(f"Loading {args.llm} ...")
    llm_tasks  = load(args.llm)

    assert len(rule_tasks) == len(llm_tasks), \
        f"Task count mismatch: {len(rule_tasks)} vs {len(llm_tasks)}"

    rule_counts = label_counts(rule_tasks)
    llm_counts  = label_counts(llm_tasks)

    # Output dir
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Print summary
    print_summary(rule_tasks, llm_tasks, rule_counts, llm_counts)

    # Save plots
    print("Saving plots...")
    plot_label_distribution(rule_counts, llm_counts, out_dir)
    plot_coverage_overview(rule_tasks, llm_tasks, out_dir)
    plot_sentence_overlap(rule_tasks, llm_tasks, out_dir)
    plot_label_pie_comparison(rule_counts, llm_counts, out_dir)

    print(f"\nAll plots saved to: {out_dir}/\n")


if __name__ == "__main__":
    main()