export default function StatsBar({ completedCount, totalCount, servicesActivated, weeksFinished }) {
    return (
        <div className="stats-bar" aria-label="Progress Statistics">
            <div className="stats-item">
                <div className="stats-value">{completedCount}<span style={{ fontSize: "14px", color: "var(--text-muted)" }}>/{totalCount}</span></div>
                <div className="stats-label">Steps Done</div>
            </div>
            <div className="stats-item">
                <div className="stats-value">{servicesActivated}</div>
                <div className="stats-label">Weeks Started</div>
            </div>
            <div className="stats-item">
                <div className="stats-value">{weeksFinished}</div>
                <div className="stats-label">Weeks Complete</div>
            </div>
        </div>
    );
}
