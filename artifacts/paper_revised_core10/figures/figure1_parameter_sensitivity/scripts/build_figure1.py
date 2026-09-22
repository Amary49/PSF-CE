from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


FROZEN_Q = 0.72
FROZEN_LAMBDA = 0.665


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_number(value: float) -> str:
    return f"{value:g}"


def write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    data_path = root / "data" / "fig1_source.csv"
    data = pd.read_csv(data_path)
    if set(data["panel"]) != {"q", "lambda"}:
        raise RuntimeError("Expected q and lambda panels")
    if not data["n_datasets"].eq(10).all() or not data["n_pools"].eq(30).all():
        raise RuntimeError("Unexpected coverage in fig1_source.csv")

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 9.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "legend.fontsize": 9.0,
            "axes.linewidth": 0.65,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    scores = 100.0 * data[["ACC", "NMI"]].to_numpy().ravel()
    lower = max(0.0, math.floor((float(scores.min()) - 1.5) / 2.0) * 2.0)
    upper = min(100.0, math.ceil((float(scores.max()) + 1.5) / 2.0) * 2.0)
    if upper - lower < 8.0:
        center = 0.5 * (upper + lower)
        lower = max(0.0, math.floor(center - 4.0))
        upper = min(100.0, math.ceil(center + 4.0))

    # Native ICASSP single-column canvas (3.39 in).  The manuscript includes
    # this PDF at column width without down-scaling, so all visible text keeps
    # its 9 pt source size.
    fig, axes = plt.subplots(1, 2, figsize=(3.39, 1.82), sharey=True)
    colors = {"ACC": "#0072B2", "NMI": "#D55E00"}
    markers = {"ACC": "o", "NMI": "s"}
    line_styles = {"ACC": "-", "NMI": (0, (3.0, 1.6))}
    panels = [
        ("q", FROZEN_Q, r"(a) $q$ ($\lambda=0.665$)"),
        ("lambda", FROZEN_LAMBDA, r"(b) $\lambda$ ($q=0.72$)"),
    ]

    for ax, (panel_name, frozen_value, label) in zip(axes, panels):
        panel = data[data["panel"].eq(panel_name)].copy()
        expected = [0.3, 0.72, 1.0, 6.0, 12.0] if panel_name == "q" else [0.1, 0.5, 0.665, 1.0, 4.0, 12.0]
        expected_array = np.asarray(expected, dtype=float)
        orders = []
        for value in panel["parameter"].to_numpy(float):
            index = int(np.argmin(np.abs(expected_array - value)))
            if not np.isclose(value, expected_array[index], rtol=0.0, atol=1e-12):
                raise RuntimeError(f"Unexpected {panel_name} coordinate: {value}")
            orders.append(index)
        panel["order"] = orders
        panel = panel.sort_values("order")
        if not np.allclose(panel["parameter"].to_numpy(float), np.asarray(expected, dtype=float)):
            raise RuntimeError(f"Unexpected grid for {panel_name}")
        x = np.arange(len(panel), dtype=float)
        frozen_index = expected.index(frozen_value)
        for metric in ("ACC", "NMI"):
            y = 100.0 * panel[metric].to_numpy(float)
            ax.plot(
                x,
                y,
                color=colors[metric],
                linestyle=line_styles[metric],
                marker=markers[metric],
                markersize=3.7,
                markerfacecolor="white",
                markeredgecolor=colors[metric],
                markeredgewidth=0.9,
                linewidth=1.2,
                zorder=3,
            )
            ax.scatter(
                [x[frozen_index]],
                [y[frozen_index]],
                s=27,
                marker=markers[metric],
                facecolor=colors[metric],
                edgecolor="black",
                linewidth=0.7,
                zorder=4,
            )
        ax.axvline(
            x[frozen_index],
            color="#4D4D4D",
            linestyle=(0, (1.2, 2.0)),
            linewidth=0.8,
            zorder=2,
        )
        ax.set_xticks(x, [clean_number(value) for value in expected])
        ax.set_xlabel(label, labelpad=4.5)
        ax.set_ylim(lower, upper)
        ax.set_xlim(-0.22, len(x) - 0.78)
        ax.set_axisbelow(True)
        ax.grid(which="major", axis="both", color="#D7D7D7", linewidth=0.42, alpha=0.72)
        for spine in ax.spines.values():
            spine.set_color("#4D4D4D")
            spine.set_linewidth(0.62)
        ax.tick_params(axis="both", width=0.55, length=2.5, color="#4D4D4D", pad=1.5)

    axes[0].set_ylabel("Mean score (%)", labelpad=2.0)
    handles = [
        Line2D([0], [0], color=colors["ACC"], linestyle=line_styles["ACC"], marker=markers["ACC"], markerfacecolor="white", markeredgecolor=colors["ACC"], linewidth=1.2, label="ACC"),
        Line2D([0], [0], color=colors["NMI"], linestyle=line_styles["NMI"], marker=markers["NMI"], markerfacecolor="white", markeredgecolor=colors["NMI"], linewidth=1.2, label="NMI"),
        Line2D([0], [0], color="#4D4D4D", marker="o", markerfacecolor="#9E9E9E", markeredgecolor="black", linestyle=(0, (1.2, 2.0)), linewidth=0.8, label="Frozen"),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.54, 0.995),
        ncol=3,
        frameon=True,
        fancybox=False,
        facecolor="white",
        edgecolor="#B8B8B8",
        framealpha=0.96,
        borderpad=0.20,
        handlelength=1.35,
        handletextpad=0.30,
        columnspacing=0.65,
    )
    fig.subplots_adjust(left=0.17, right=0.995, bottom=0.275, top=0.72, wspace=0.12)

    figure_dir = root / "figures"
    audit_dir = root / "audit"
    figure_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    stem = figure_dir / "fig1_revised_core10_postfreeze_sensitivity"
    pdf_path = stem.with_suffix(".pdf")
    svg_path = stem.with_suffix(".svg")
    png_path = stem.with_suffix(".png")
    fig.savefig(pdf_path)
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=400)
    plt.close(fig)

    caption = (
        "Post-freeze parameter sensitivity of PSF-CE on the revised Core-10 cohort. "
        "(a) $q$ is varied with $\\lambda=0.665$ fixed, and (b) $\\lambda$ is varied with "
        "$q=0.72$ fixed. Each point first averages the three frozen base-partition pools within "
        "each dataset and then equally averages the ten datasets. The marked operating point "
        "$(q,\\lambda)=(0.72,0.665)$ was fixed during development before the reported revised "
        "Core-10 analysis and is shown only for reference; the sensitivity sweep is not used for "
        "parameter reselection. Parameter values are displayed at categorical grid positions for readability."
    )
    tex = (
        "\\begin{figure}[t]\n"
        "  \\centering\n"
        "  \\includegraphics[width=\\columnwidth]{figures/fig1_revised_core10_postfreeze_sensitivity.pdf}\n"
        f"  \\caption{{{caption}}}\n"
        "  \\label{fig:revised_core10_sensitivity}\n"
        "\\end{figure}\n"
    )
    tex_path = figure_dir / "fig1_revised_core10_postfreeze_sensitivity.tex"
    write_text_lf(tex_path, tex)

    audit = {
        "status": "PASS",
        "source_csv": "data/fig1_source.csv",
        "source_csv_sha256": sha256_file(data_path),
        "pdf": "figures/fig1_revised_core10_postfreeze_sensitivity.pdf",
        "pdf_sha256": sha256_file(pdf_path),
        "svg": "figures/fig1_revised_core10_postfreeze_sensitivity.svg",
        "svg_sha256": sha256_file(svg_path),
        "png": "figures/fig1_revised_core10_postfreeze_sensitivity.png",
        "png_sha256": sha256_file(png_path),
        "tex": "figures/fig1_revised_core10_postfreeze_sensitivity.tex",
        "tex_sha256": sha256_file(tex_path),
        "x_spacing": "categorical_equal_spacing",
        "shared_y_axis": True,
        "y_range_percent": [lower, upper],
        "frozen_marked_as_best": False,
        "data_values_modified_for_styling": False,
        "panel_labels_position": "below panels",
        "legend_position": "shared upper center",
        "legend_labels": ["ACC", "NMI", "Frozen"],
        "native_canvas_inches": [3.39, 1.82],
        "minimum_configured_font_pt": 9.0,
        "intended_manuscript_width": "one ICASSP column (3.39 inches)",
        "manuscript_downscaling_required": False,
    }
    write_text_lf(
        audit_dir / "FIG1_BUILD_AUDIT.json",
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
