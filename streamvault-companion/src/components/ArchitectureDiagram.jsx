import { useRef, useEffect, useState, useCallback } from "react";
import DiagramNode from "./DiagramNode";
import DiagramEdge from "./DiagramEdge";
import { DIAGRAM_NODES, DIAGRAM_EDGES } from "../data/projectData";

export default function ArchitectureDiagram({ activeNodes, activeEdges, completedSteps, onJumpToStep }) {
    const containerRef = useRef(null);
    const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

    useEffect(() => {
        const measure = () => {
            if (containerRef.current) {
                const { width, height } = containerRef.current.getBoundingClientRect();
                setContainerSize({ width, height });
            }
        };

        measure();
        const ro = new ResizeObserver(measure);
        if (containerRef.current) ro.observe(containerRef.current);
        return () => ro.disconnect();
    }, []);

    return (
        <div ref={containerRef} className="diagram-container">
            {/* SVG layer for edges — drawn behind nodes */}
            <svg className="diagram-svg" style={{ zIndex: 1 }}>
                <defs>
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>
                {DIAGRAM_EDGES.map((edge) => (
                    <DiagramEdge
                        key={edge.id}
                        edge={edge}
                        isActive={activeEdges[edge.id]}
                        containerSize={containerSize}
                    />
                ))}
            </svg>

            {/* Node layer — on top of SVG */}
            {Object.values(DIAGRAM_NODES).map((node) => (
                <DiagramNode
                    key={node.id}
                    node={node}
                    isActive={activeNodes[node.id]}
                    completedSteps={completedSteps}
                    onJumpToStep={onJumpToStep}
                />
            ))}
        </div>
    );
}
