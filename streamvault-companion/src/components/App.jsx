import { useState, useEffect } from "react";
import Header from "./Header";
import StatsBar from "./StatsBar";
import ProgressSidebar from "./ProgressSidebar";
import DiagramPanel from "./DiagramPanel";
import CompletionCelebration from "./CompletionCelebration";
import { useProgress } from "../hooks/useProgress";
import { useActiveComponents } from "../hooks/useActiveComponents";

export default function App() {
    const {
        completedSteps,
        timestamps,
        toggleStep,
        resetProgress,
        completedCount,
        totalCount,
        completionPercentage,
        currentWeek,
        servicesActivated,
        weeksFinished,
    } = useProgress();

    const { activeNodes, activeEdges } = useActiveComponents(completedSteps);

    const [showCelebration, setShowCelebration] = useState(false);
    const [hasCelebrated, setHasCelebrated] = useState(() => {
        return localStorage.getItem("streamvault-celebrated") === "true";
    });

    useEffect(() => {
        if (completionPercentage === 100 && !hasCelebrated) {
            const t = setTimeout(() => {
                setShowCelebration(true);
                setHasCelebrated(true);
                localStorage.setItem("streamvault-celebrated", "true");
            }, 600);
            return () => clearTimeout(t);
        }
    }, [completionPercentage, hasCelebrated]);

    function handleReset() {
        resetProgress();
        setHasCelebrated(false);
        setShowCelebration(false);
        localStorage.removeItem("streamvault-celebrated");
    }

    return (
        <>
            <Header onReset={handleReset} completionPercentage={completionPercentage} />
            <StatsBar
                completedCount={completedCount}
                totalCount={totalCount}
                servicesActivated={servicesActivated}
                weeksFinished={weeksFinished}
            />
            <main className="main-layout">
                <ProgressSidebar
                    completedSteps={completedSteps}
                    timestamps={timestamps}
                    onToggle={toggleStep}
                    completionPercentage={completionPercentage}
                    completedCount={completedCount}
                    totalCount={totalCount}
                    currentWeek={currentWeek}
                />
                <DiagramPanel
                    activeNodes={activeNodes}
                    activeEdges={activeEdges}
                    completedSteps={completedSteps}
                />
            </main>

            {showCelebration && (
                <CompletionCelebration onDismiss={() => setShowCelebration(false)} />
            )}
        </>
    );
}
