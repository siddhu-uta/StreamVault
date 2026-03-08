import ArchitectureDiagram from "./ArchitectureDiagram";

const LEGEND_ITEMS = [
    { color: "#f59e0b", label: "Lambda" },
    { color: "#f97316", label: "API Gateway" },
    { color: "#a855f7", label: "SQS" },
    { color: "#3b82f6", label: "DynamoDB" },
    { color: "#10b981", label: "S3" },
    { color: "#ef4444", label: "Cognito" },
    { color: "#1d4ed8", label: "CloudWatch" },
    { color: "#7c3aed", label: "X-Ray" },
    { color: "#6366f1", label: "Client" },
];

export default function DiagramPanel({ activeNodes, activeEdges, completedSteps, onJumpToStep }) {
    const activeCount = Object.values(activeNodes).filter(Boolean).length;
    const totalNodes = Object.keys(activeNodes).length;

    function handleJumpToStep(stepId) {
        const el = document.getElementById(`step-${stepId}`);
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            el.style.background = "rgba(99,102,241,0.1)";
            el.style.borderColor = "rgba(99,102,241,0.4)";
            setTimeout(() => {
                el.style.background = "";
                el.style.borderColor = "";
            }, 2000);
        }
        if (onJumpToStep) onJumpToStep(stepId);
    }

    return (
        <section className="diagram-panel" aria-label="Architecture Diagram">
            <div className="diagram-panel-header">
                <div className="diagram-panel-title">
                    <span className="diagram-panel-title-dot" />
                    Live Architecture — {activeCount} / {totalNodes} Services Active
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Check steps on the left to activate services →
                </div>
            </div>

            <div className="diagram-scroll">
                <ArchitectureDiagram
                    activeNodes={activeNodes}
                    activeEdges={activeEdges}
                    completedSteps={completedSteps}
                    onJumpToStep={handleJumpToStep}
                />
            </div>

            <div className="diagram-legend">
                <span className="legend-label">Services:</span>
                {LEGEND_ITEMS.map((item) => (
                    <div key={item.label} className="legend-item">
                        <span className="legend-dot" style={{ background: item.color }} />
                        <span className="legend-text">{item.label}</span>
                    </div>
                ))}
            </div>
        </section>
    );
}
