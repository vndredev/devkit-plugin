"""Architecture visualization - Mermaid and ASCII diagrams.

TIER 2: May import from core, lib.
"""

from lib.config import get


def generate_mermaid_diagram(
    layers: dict | None = None,
    deps: dict[str, list[str]] | None = None,
    show_violations: bool = False,
) -> str:
    """Generate Mermaid diagram for architecture visualization.

    Args:
        layers: Layer config dict. Uses config if not provided.
        deps: Optional dependency map (layer -> list of imported layers).
        show_violations: Highlight violation edges in red.

    Returns:
        Mermaid diagram markup.
    """
    if layers is None:
        layers = get("arch.layers", {})

    if not layers:
        return "```mermaid\ngraph TD\n    A[No layers configured]\n```"

    # Sort layers by tier
    sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))

    lines = ["```mermaid", "graph TD"]

    # Define nodes
    for name, info in sorted_layers:
        tier = info.get("tier", 0)
        desc = info.get("description", "")[:20]
        node_label = f"{name}"
        if desc:
            node_label = f"{name}<br/><small>T{tier}: {desc}</small>"
        lines.append(f"    {name}[{node_label}]")

    lines.append("")

    # Add edges based on tier hierarchy (default)
    if deps is None:
        for i in range(len(sorted_layers) - 1):
            src = sorted_layers[i][0]
            dst = sorted_layers[i + 1][0]
            lines.append(f"    {src} --> {dst}")
    else:
        # Add edges based on actual dependencies
        for src, targets in deps.items():
            for dst in targets:
                if dst in layers:
                    src_tier = layers.get(src, {}).get("tier", 0)
                    dst_tier = layers.get(dst, {}).get("tier", 0)

                    # Check for violation (importing from higher tier)
                    if show_violations and dst_tier > src_tier:
                        lines.append(f"    {src} -.->|violation| {dst}")
                    else:
                        lines.append(f"    {src} --> {dst}")

    # Style violations if requested
    if show_violations:
        lines.extend([
            "",
            "    linkStyle default stroke:#333",
            "    classDef violation stroke:#f00,stroke-width:2px",
        ])

    lines.append("```")

    return "\n".join(lines)


def generate_ascii_diagram(layers: dict | None = None) -> str:
    """Generate ASCII diagram for terminal output.

    Fallback visualization for terminals without Mermaid support.

    Args:
        layers: Layer config dict. Uses config if not provided.

    Returns:
        ASCII diagram string.
    """
    if layers is None:
        layers = get("arch.layers", {})

    if not layers:
        return "No layers configured."

    # Sort layers by tier
    sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))

    # Calculate widths
    max_name = max(len(name) for name, _ in sorted_layers)
    max_desc = max(len(info.get("description", "")[:30]) for _, info in sorted_layers)
    box_width = max(max_name + 4, 20)

    lines = []
    lines.append("Architecture Layers")
    lines.append("=" * (box_width + max_desc + 10))
    lines.append("")

    for i, (name, info) in enumerate(sorted_layers):
        tier = info.get("tier", 0)
        desc = info.get("description", "-")[:30]

        # Box top
        lines.append(f"  ┌{'─' * box_width}┐")

        # Box content
        label = f"TIER {tier}: {name}"
        padding = box_width - len(label)
        lines.append(f"  │{label}{' ' * padding}│  {desc}")

        # Box bottom
        lines.append(f"  └{'─' * box_width}┘")

        # Arrow to next layer
        if i < len(sorted_layers) - 1:
            arrow_padding = box_width // 2
            lines.append(f"  {' ' * arrow_padding}│")
            lines.append(f"  {' ' * arrow_padding}▼")

    lines.append("")
    lines.append("Rule: Higher tiers may import from lower tiers only.")

    return "\n".join(lines)


def generate_dependency_matrix(deps: dict[str, list[str]], layers: dict | None = None) -> str:
    """Generate dependency matrix showing imports between layers.

    Args:
        deps: Dependency map (layer -> list of imported layers).
        layers: Layer config for ordering. Uses config if not provided.

    Returns:
        ASCII matrix showing dependencies.
    """
    if layers is None:
        layers = get("arch.layers", {})

    if not layers or not deps:
        return "No dependencies to display."

    # Get all layer names
    sorted_layers = sorted(layers.items(), key=lambda x: x[1].get("tier", 0))
    layer_names = [name for name, _ in sorted_layers]

    # Build matrix
    max_name = max(len(name) for name in layer_names)
    header = " " * (max_name + 2) + " ".join(f"{n[:3]:>3}" for n in layer_names)

    lines = ["Dependency Matrix (row imports column)", "=" * len(header), "", header, "-" * len(header)]

    for src in layer_names:
        row = f"{src:>{max_name}} │"
        src_deps = set(deps.get(src, []))

        for dst in layer_names:
            if dst in src_deps:
                # Check if valid import
                src_tier = layers.get(src, {}).get("tier", 0)
                dst_tier = layers.get(dst, {}).get("tier", 0)

                if dst_tier > src_tier:
                    row += "  X "  # Violation
                else:
                    row += "  ✓ "  # Valid
            else:
                row += "  · "  # No import

        lines.append(row)

    lines.extend(["", "Legend: ✓ = valid import, X = violation, · = no import"])

    return "\n".join(lines)
