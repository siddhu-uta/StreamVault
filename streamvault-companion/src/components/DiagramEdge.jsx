import { useRef, useEffect, useState } from "react";
import { DIAGRAM_NODES } from "../data/projectData";

// Get center position of a node as pixel offsets within the container
function getNodeCenter(node, containerW, containerH) {
    const nodeW = 140; // approximate node width in px
    const nodeH = 72;  // approximate node height in px
    const x = (node.x / 100) * containerW;
    const y = (node.y / 100) * containerH + nodeH / 2;
    return { x, y };
}

// Create a smooth curved SVG path between two points
function makePath(x1, y1, x2, y2, style) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const midX = x1 + dx / 2;
    const midY = y1 + dy / 2;

    if (style === "auth") {
        // horizontal-ish auth line: cubic bezier
        return `M ${x1} ${y1} C ${x1 + dx * 0.5} ${y1}, ${x2 - dx * 0.3} ${y2}, ${x2} ${y2}`;
    }
    if (style === "observability") {
        // dashed line to observability sidebar
        return `M ${x1} ${y1} C ${x1 + dx * 0.6} ${y1}, ${x2 - dx * 0.3} ${y2}, ${x2} ${y2}`;
    }
    // default: smooth elbow
    return `M ${x1} ${y1} C ${x1} ${midY + Math.abs(dy) * 0.1}, ${x2} ${midY - Math.abs(dy) * 0.1}, ${x2} ${y2}`;
}

const STYLE_CONFIG = {
    data: { stroke: "#6366f1", strokeWidth: 2, dasharray: "none", opacity: 1 },
    auth: { stroke: "#ef4444", strokeWidth: 1.5, dasharray: "6 4", opacity: 0.8 },
    failure: { stroke: "#ec4899", strokeWidth: 1.5, dasharray: "5 5", opacity: 0.85 },
    read: { stroke: "#3b82f6", strokeWidth: 2, dasharray: "none", opacity: 1 },
    observability: { stroke: "#475569", strokeWidth: 1, dasharray: "4 4", opacity: 0.6 },
    inactive: { stroke: "#1e293b", strokeWidth: 1.5, dasharray: "4 4", opacity: 0.4 },
};

export default function DiagramEdge({ edge, isActive, containerSize }) {
    const fromNode = DIAGRAM_NODES[edge.from];
    const toNode = DIAGRAM_NODES[edge.to];
    if (!fromNode || !toNode) return null;

    const { width, height } = containerSize;
    if (!width || !height) return null;

    const from = getNodeCenter(fromNode, width, height);
    const to = getNodeCenter(toNode, width, height);

    const pathD = makePath(from.x, from.y, to.x, to.y, isActive ? edge.style : "inactive");
    const config = isActive ? (STYLE_CONFIG[edge.style] || STYLE_CONFIG.data) : STYLE_CONFIG.inactive;

    const edgeId = `edge-path-${edge.id}`;
    const animSpeed = edge.style === "observability" ? 2.4 : 1.8;

    return (
        <g>
            {/* Main path */}
            <path
                id={edgeId}
                d={pathD}
                fill="none"
                stroke={config.stroke}
                strokeWidth={config.strokeWidth}
                strokeDasharray={config.dasharray === "none" ? undefined : config.dasharray}
                opacity={config.opacity}
                style={{ transition: "all 0.4s ease" }}
            />

            {/* Arrowhead */}
            {isActive && (
                <defs>
                    <marker
                        id={`arrow-${edge.id}`}
                        markerWidth="8"
                        markerHeight="8"
                        refX="6"
                        refY="3"
                        orient="auto"
                    >
                        <path d="M0,0 L0,6 L8,3 z" fill={config.stroke} opacity={config.opacity} />
                    </marker>
                </defs>
            )}

            {/* Re-draw path with arrowhead */}
            {isActive && (
                <path
                    d={pathD}
                    fill="none"
                    stroke={config.stroke}
                    strokeWidth={config.strokeWidth}
                    strokeDasharray={config.dasharray === "none" ? undefined : config.dasharray}
                    opacity={config.opacity}
                    markerEnd={`url(#arrow-${edge.id})`}
                />
            )}

            {/* Traveling data packet dot */}
            {isActive && edge.style !== "observability" && (
                <circle r="4" fill={config.stroke} opacity="0.9">
                    <animateMotion
                        dur={`${animSpeed}s`}
                        repeatCount="indefinite"
                        path={pathD}
                    />
                </circle>
            )}

            {/* Edge label */}
            {isActive && edge.label && (
                <text
                    x={(from.x + to.x) / 2}
                    y={(from.y + to.y) / 2 - 8}
                    textAnchor="middle"
                    fontSize="9"
                    fill={config.stroke}
                    opacity="0.8"
                    fontFamily="Inter, sans-serif"
                    fontWeight="600"
                >
                    {edge.label}
                </text>
            )}
        </g>
    );
}
