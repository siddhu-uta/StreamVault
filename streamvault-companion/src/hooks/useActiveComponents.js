import { useMemo } from "react";
import { DIAGRAM_NODES, DIAGRAM_EDGES } from "../data/projectData";

export function useActiveComponents(completedSteps) {
    const activeNodes = useMemo(() => {
        const result = {};
        for (const [id, node] of Object.entries(DIAGRAM_NODES)) {
            result[id] = node.requiredSteps.every((s) => completedSteps.has(s));
        }
        return result;
    }, [completedSteps]);

    const activeEdges = useMemo(() => {
        const result = {};
        for (const edge of DIAGRAM_EDGES) {
            result[edge.id] = edge.requiredSteps.every((s) => completedSteps.has(s));
        }
        return result;
    }, [completedSteps]);

    return { activeNodes, activeEdges };
}
