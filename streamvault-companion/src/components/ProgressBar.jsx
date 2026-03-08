export default function ProgressBar({ percentage, height = 8, gradient }) {
    const fill = gradient || `linear-gradient(90deg, #6366f1 0%, #8b5cf6 ${percentage}%, #10b981 100%)`;
    return (
        <div className="progress-bar-wrap">
            <div className="progress-bar-header">
                <span className="progress-bar-label">Overall Progress</span>
                <span className="progress-bar-pct">{percentage}%</span>
            </div>
            <div className="progress-bar-track" style={{ height }}>
                <div
                    className="progress-bar-fill"
                    style={{
                        width: `${percentage}%`,
                        background: fill,
                    }}
                />
            </div>
        </div>
    );
}
