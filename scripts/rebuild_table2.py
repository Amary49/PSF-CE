from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "artifacts" / "paper_revised_core10"
EXP3 = PAPER / "mechanism" / "experiment3" / "FINAL_EXPLORATORY_REPORT.json"
MIXING = PAPER / "mechanism" / "mixing_geometry" / "FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.json"
OUT = PAPER / "tables"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def main() -> None:
    exp3 = json.loads(EXP3.read_text(encoding="utf-8-sig"))
    mixing = json.loads(MIXING.read_text(encoding="utf-8-sig"))
    if exp3["analysis_status"] != "EXPLORATORY_NOT_CONFIRMATORY":
        raise RuntimeError("Experiment 3 analysis boundary changed")
    if mixing["analysis_status"] != "EXPLORATORY_NOT_CONFIRMATORY":
        raise RuntimeError("Mixing-geometry analysis boundary changed")

    core10_mix = mixing["cohort_profile_counts"]["REVISED_CORE10_NATIVE"]
    core9_mix = mixing["cohort_profile_counts"]["REVISED_CORE9_NO_CHAMELEON"]
    rows = [
        {
            "section": "True-class fragmentation",
            "diagnostic": "H(Zhat|Y)",
            "diagnostic_tex": r"$H(\hat{Z}\mid Y)$",
            "direction": "lower",
            "direction_tex": r"$\downarrow$",
            "favorable_comparators": int(exp3["native_core10"]["H3_A"]["favorable_comparators"]),
            "core9_favorable_comparators": int(exp3["exclude_chameleon_core9"]["H3_A"]["favorable_comparators"]),
            "source_file": "mechanism/experiment3/FINAL_EXPLORATORY_REPORT.json",
            "source_field": "native_core10.H3_A.favorable_comparators",
        },
        {
            "section": "True-class fragmentation",
            "diagnostic": "Macro fragmentation",
            "diagnostic_tex": "Macro fragmentation",
            "direction": "lower",
            "direction_tex": r"$\downarrow$",
            "favorable_comparators": int(exp3["native_core10"]["H3_B"]["favorable_comparators"]),
            "core9_favorable_comparators": int(exp3["exclude_chameleon_core9"]["H3_B"]["favorable_comparators"]),
            "source_file": "mechanism/experiment3/FINAL_EXPLORATORY_REPORT.json",
            "source_field": "native_core10.H3_B.favorable_comparators",
        },
        {
            "section": "Predicted-cluster purification",
            "diagnostic": "Homogeneity",
            "diagnostic_tex": "Homogeneity",
            "direction": "higher",
            "direction_tex": r"$\uparrow$",
            "favorable_comparators": int(core10_mix["homogeneity"]),
            "core9_favorable_comparators": int(core9_mix["homogeneity"]),
            "source_file": "mechanism/mixing_geometry/FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.json",
            "source_field": "cohort_profile_counts.REVISED_CORE10_NATIVE.homogeneity",
        },
        {
            "section": "Predicted-cluster purification",
            "diagnostic": "Macro mixing entropy",
            "diagnostic_tex": "Macro mixing entropy",
            "direction": "lower",
            "direction_tex": r"$\downarrow$",
            "favorable_comparators": int(core10_mix["MacroMixEntropy"]),
            "core9_favorable_comparators": int(core9_mix["MacroMixEntropy"]),
            "source_file": "mechanism/mixing_geometry/FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.json",
            "source_field": "cohort_profile_counts.REVISED_CORE10_NATIVE.MacroMixEntropy",
        },
        {
            "section": "Predicted-cluster purification",
            "diagnostic": "Macro purity",
            "diagnostic_tex": "Macro purity",
            "direction": "higher",
            "direction_tex": r"$\uparrow$",
            "favorable_comparators": int(core10_mix["MacroPurity"]),
            "core9_favorable_comparators": int(core9_mix["MacroPurity"]),
            "source_file": "mechanism/mixing_geometry/FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.json",
            "source_field": "cohort_profile_counts.REVISED_CORE10_NATIVE.MacroPurity",
        },
        {
            "section": "Residual inter-class mixing",
            "diagnostic": "Pair mixing rate",
            "diagnostic_tex": "Pair mixing rate",
            "direction": "lower",
            "direction_tex": r"$\downarrow$",
            "favorable_comparators": int(core10_mix["PairMixRate"]),
            "core9_favorable_comparators": int(core9_mix["PairMixRate"]),
            "source_file": "mechanism/mixing_geometry/FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.json",
            "source_field": "cohort_profile_counts.REVISED_CORE10_NATIVE.PairMixRate",
        },
    ]
    expected = [5, 5, 5, 5, 5, 1]
    observed = [row["favorable_comparators"] for row in rows]
    if observed != expected:
        raise RuntimeError(f"Table II profile drift: {observed} != {expected}")
    if any(row["core9_favorable_comparators"] != row["favorable_comparators"] for row in rows):
        raise RuntimeError("At least one displayed profile changes after excluding Chameleon")

    OUT.mkdir(parents=True, exist_ok=True)
    source_path = OUT / "table2_partition_structure_source.csv"
    # Keep generated evidence byte-stable across Git/Windows/Linux.  A BOM is
    # unnecessary for this ASCII-compatible CSV and would violate the release
    # package's UTF-8-without-BOM contract.
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "section", "diagnostic", "diagnostic_tex", "direction", "direction_tex",
                "favorable_comparators", "denominator", "gate_met", "core9_favorable_comparators",
                "core9_same_count", "analysis_status", "source_file", "source_field",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "denominator": 6,
                    "gate_met": row["favorable_comparators"] >= 4,
                    "core9_same_count": True,
                    "analysis_status": "EXPLORATORY_NOT_CONFIRMATORY",
                }
            )

    tex = r"""% Revised Core-10 manuscript Table II
% Requires: booktabs, amsmath
\begin{table}[t]
\centering
\caption{Exploratory partition-structure directional profiles on revised Core-10.}
\label{tab:partition_structure}
\begingroup
\fontsize{9}{10.2}\selectfont
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.01}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lcc@{}}
\toprule
Diagnostic & Direction & Fav./6 \\
\midrule
\multicolumn{3}{l}{\textit{True-class fragmentation}} \\
\quad $H(\hat{Z}\mid Y)$ & $\downarrow$ & \textbf{5/6} \\
\quad Macro fragmentation & $\downarrow$ & \textbf{5/6} \\
\addlinespace[1pt]
\multicolumn{3}{l}{\textit{Predicted-cluster purification}} \\
\quad Homogeneity & $\uparrow$ & \textbf{5/6} \\
\quad Macro mixing entropy & $\downarrow$ & \textbf{5/6} \\
\quad Macro purity & $\uparrow$ & \textbf{5/6} \\
\addlinespace[1pt]
\multicolumn{3}{l}{\textit{Residual inter-class mixing}} \\
\quad Pair mixing rate & $\downarrow$ & 1/6 \\
\bottomrule
\end{tabular*}

\vspace{2pt}
\begin{minipage}{\columnwidth}
\fontsize{9}{10.2}\selectfont
\textit{Note:} Fav./6 counts comparator-level median changes beyond the numerical tolerance in the stated direction; these are not significance-test counts. Bold denotes the prespecified $\geq 4/6$ profile gate. The macro/pair contrast is consistent with localized residual mixing. All counts are unchanged after excluding Chameleon.
\end{minipage}
\endgroup
\end{table}
"""
    tex_path = OUT / "table2_partition_structure.tex"
    write_text_lf(tex_path, tex)

    audit = {
        "status": "PASS",
        "analysis_status": "EXPLORATORY_NOT_CONFIRMATORY",
        "cohort": "REVISED_CORE10_NATIVE",
        "comparators": ["MCLA", "HBGF", "CEHM", "YACHT", "RANGE", "GPEC"],
        "displayed_counts": observed,
        "profile_gate": ">=4/6 comparator-level median changes in the stated direction",
        "counts_are_significance_tests": False,
        "exclude_chameleon_core9_all_six_counts_unchanged": True,
        "causal_claim": "NOT_ESTABLISHED",
        "source_files": [
            {"path": EXP3.relative_to(ROOT).as_posix(), "sha256": sha256_file(EXP3)},
            {"path": MIXING.relative_to(ROOT).as_posix(), "sha256": sha256_file(MIXING)},
        ],
        "source_csv": source_path.relative_to(ROOT).as_posix(),
        "source_csv_sha256": sha256_file(source_path),
        "tex": tex_path.relative_to(ROOT).as_posix(),
        "tex_sha256": sha256_file(tex_path),
        "latex_compile": "NOT_RUN_NO_LOCAL_TEX_ENGINE",
        "static_latex_checks": "performed by release validator",
    }
    audit_path = OUT / "TABLE2_VALIDATION.json"
    write_text_lf(audit_path, json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
