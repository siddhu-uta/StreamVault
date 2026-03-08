import { useState, useEffect, useRef } from "react";

const SERVICE_ICONS = {
    client: "💻",
    apigateway: "🌐",
    lambda: "λ",
    sqs: "📬",
    dynamodb: "🗄️",
    s3: "🪣",
    cognito: "🔐",
    cloudwatch: "📊",
    xray: "🔍",
};

const SERVICE_DESCRIPTIONS = {
    client: "The frontend application or API consumer that sends events to StreamVault.",
    apigateway: "AWS API Gateway routes HTTP requests, enforces Cognito JWT auth, and handles throttling.",
    lambda: "AWS Lambda runs your Python code on demand — no servers to manage.",
    sqs: "Amazon SQS durably buffers messages between services, decoupling ingest from processing.",
    dynamodb: "Amazon DynamoDB stores events with millisecond-latency reads via partition+sort key design.",
    s3: "Amazon S3 archives raw JSON Lines files in Hive-partitioned structure for cheap long-term storage.",
    cognito: "AWS Cognito issues short-lived JWTs, enabling token-based auth without API key sprawl.",
    cloudwatch: "Amazon CloudWatch collects logs, metrics, and triggers alarms on anomalies.",
    xray: "AWS X-Ray traces requests across Lambdas and API Gateway for distributed debugging.",
};

export default function DiagramNode({ node, isActive, completedSteps, onJumpToStep }) {
    const [wasActive, setWasActive] = useState(false);
    const [isUnlocking, setIsUnlocking] = useState(false);
    const [showTooltip, setShowTooltip] = useState(false);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
    const nodeRef = useRef(null);

    useEffect(() => {
        if (isActive && !wasActive) {
            setIsUnlocking(true);
            const t = setTimeout(() => setIsUnlocking(false), 900);
            return () => clearTimeout(t);
        }
        setWasActive(isActive);
    }, [isActive]);

    const handleMouseEnter = (e) => {
        const rect = nodeRef.current?.getBoundingClientRect();
        if (rect) {
            setTooltipPos({
                x: Math.min(rect.right + 10, window.innerWidth - 300),
                y: Math.max(rect.top - 20, 10),
            });
        }
        setShowTooltip(true);
    };

    const handleMouseLeave = () => setShowTooltip(false);

    const doneSteps = node.requiredSteps.filter((s) => completedSteps.has(s));
    const pendingSteps = node.requiredSteps.filter((s) => !completedSteps.has(s));

    const glowColor = isActive ? node.activeColor : "transparent";
    const borderColor = isActive ? node.activeColor : "#1e293b";

    return (
        <>
            <div
                ref={nodeRef}
                id={`node-${node.id}`}
                className={`diagram-node ${isActive ? "is-active" : ""} ${isUnlocking ? "is-unlocking" : ""}`}
                style={{
                    left: `${node.x}%`,
                    top: `${node.y}%`,
                    borderColor,
                    boxShadow: isActive
                        ? `0 0 0 1px ${glowColor}33, 0 0 20px ${glowColor}44, 0 4px 12px rgba(0,0,0,0.4)`
                        : "0 2px 8px rgba(0,0,0,0.4)",
                    "--node-glow": glowColor,
                }}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
            >
                <span className="node-icon" style={{ filter: isActive ? "none" : "grayscale(1)" }}>
                    {SERVICE_ICONS[node.type] || "⬡"}
                </span>
                <div className="node-label" style={{ color: isActive ? node.activeColor : "var(--text-muted)" }}>
                    {node.label}
                </div>
                <div className="node-sublabel">{node.sublabel}</div>
            </div>

            {showTooltip && (
                <div
                    className="tooltip"
                    style={{ left: tooltipPos.x, top: tooltipPos.y }}
                >
                    <div className="tooltip-service-name">
                        {SERVICE_ICONS[node.type]} {node.label}
                        <span
                            className="tooltip-service-badge"
                            style={{
                                background: `${node.activeColor}22`,
                                color: node.activeColor,
                                border: `1px solid ${node.activeColor}44`,
                            }}
                        >
                            {isActive ? "ACTIVE" : "LOCKED"}
                        </span>
                    </div>
                    <div className="tooltip-description">
                        {SERVICE_DESCRIPTIONS[node.type] || "AWS Service component in StreamVault."}
                    </div>

                    {node.requiredSteps.length > 0 && (
                        <>
                            <div className="tooltip-section-title">
                                Required Steps ({doneSteps.length}/{node.requiredSteps.length})
                            </div>
                            <div className="tooltip-steps">
                                {doneSteps.map((sid) => (
                                    <div key={sid} className="tooltip-step tooltip-step-done">
                                        <span className="tooltip-step-icon">✓</span>
                                        <span>{sid}</span>
                                    </div>
                                ))}
                                {pendingSteps.map((sid) => (
                                    <div
                                        key={sid}
                                        className="tooltip-step"
                                        style={{ cursor: "pointer" }}
                                        onClick={() => {
                                            onJumpToStep(sid);
                                            setShowTooltip(false);
                                        }}
                                    >
                                        <span className="tooltip-step-icon">○</span>
                                        <span style={{ textDecoration: "underline" }}>{sid} ↗ Jump to step</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}
        </>
    );
}
