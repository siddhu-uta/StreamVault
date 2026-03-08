function getRelativeTime(ts) {
    if (!ts) return null;
    const diff = Date.now() - ts;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
}

export default function StepItem({ step, isChecked, onToggle, timestamp }) {
    const relTime = getRelativeTime(timestamp);

    return (
        <div
            id={`step-${step.id}`}
            className={`step-item ${isChecked ? "is-checked" : ""}`}
            onClick={() => onToggle(step.id)}
            role="checkbox"
            aria-checked={isChecked}
            tabIndex={0}
            onKeyDown={(e) => e.key === " " && (e.preventDefault(), onToggle(step.id))}
        >
            <div className="step-checkbox">
                {isChecked && <span className="step-check-icon">✓</span>}
            </div>
            <div className="step-content">
                <div className="step-label">{step.label}</div>
                {!isChecked && (
                    <div className="step-unlocks">
                        <span>⚡</span>
                        {step.unlocks}
                    </div>
                )}
                {isChecked && relTime && (
                    <div className="step-timestamp">✓ Completed {relTime}</div>
                )}
            </div>
        </div>
    );
}
