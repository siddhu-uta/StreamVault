import { useState, useRef, useEffect } from "react";
import StepItem from "./StepItem";

export default function WeekSection({ week, weekIndex, completedSteps, timestamps, onToggle, isCurrentWeek }) {
    const allDone = week.steps.every((s) => completedSteps.has(s.id));
    const doneCount = week.steps.filter((s) => completedSteps.has(s.id)).length;
    const [open, setOpen] = useState(isCurrentWeek);
    const bodyRef = useRef(null);

    // Auto-open current week when it changes
    useEffect(() => {
        if (isCurrentWeek) setOpen(true);
    }, [isCurrentWeek]);

    const maxH = open ? `${week.steps.length * 80}px` : "0px";

    return (
        <div
            className={`week-section ${allDone ? "is-complete" : ""} ${isCurrentWeek && !allDone ? "is-active" : ""}`}
        >
            <button
                id={`week-header-${week.id}`}
                className="week-header"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
            >
                <span className="week-number">W{weekIndex + 1}</span>
                <div className="week-info">
                    <div className="week-title">{week.title.split(":")[1]?.trim() || week.title}</div>
                </div>
                <div className="week-counter">
                    <span className="week-progress-mini">
                        {doneCount}/{week.steps.length}
                    </span>
                    {allDone && <span className="week-complete-badge">🏆</span>}
                    <span className={`week-chevron ${open ? "is-open" : ""}`}>▾</span>
                </div>
            </button>

            <div className="week-body" style={{ maxHeight: maxH }} ref={bodyRef}>
                <div className="week-steps">
                    {week.steps.map((step) => (
                        <StepItem
                            key={step.id}
                            step={step}
                            isChecked={completedSteps.has(step.id)}
                            onToggle={onToggle}
                            timestamp={timestamps[step.id]}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
