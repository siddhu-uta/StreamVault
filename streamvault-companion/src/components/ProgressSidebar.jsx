import ProgressBar from "./ProgressBar";
import WeekSection from "./WeekSection";
import { WEEKS } from "../data/projectData";

export default function ProgressSidebar({
    completedSteps,
    timestamps,
    onToggle,
    completionPercentage,
    completedCount,
    totalCount,
    currentWeek,
}) {
    return (
        <aside className="sidebar" aria-label="Build Progress Tracker">
            <div className="sidebar-header">
                <div className="sidebar-title">
                    <span className="sidebar-title-icon">📋</span>
                    Build Progress
                </div>
                <ProgressBar percentage={completionPercentage} />
                <div className="sidebar-current-week">
                    <span className="sidebar-current-week-dot" />
                    Currently in: <strong style={{ color: "var(--text-secondary)", marginLeft: 4 }}>
                        {currentWeek.title}
                    </strong>
                </div>
            </div>

            <div className="sidebar-scroll">
                {WEEKS.map((week, i) => (
                    <WeekSection
                        key={week.id}
                        week={week}
                        weekIndex={i}
                        completedSteps={completedSteps}
                        timestamps={timestamps}
                        onToggle={onToggle}
                        isCurrentWeek={currentWeek.id === week.id}
                    />
                ))}
            </div>
        </aside>
    );
}
