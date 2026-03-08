import { useState, useCallback, useMemo } from "react";
import { WEEKS } from "../data/projectData";

const STORAGE_KEY = "streamvault-progress";
const TIMESTAMPS_KEY = "streamvault-timestamps";

function loadFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch {
        return new Set();
    }
}

function loadTimestamps() {
    try {
        const raw = localStorage.getItem(TIMESTAMPS_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveToStorage(completedSet) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...completedSet]));
}

function saveTimestamps(timestamps) {
    localStorage.setItem(TIMESTAMPS_KEY, JSON.stringify(timestamps));
}

const allSteps = WEEKS.flatMap((w) => w.steps);
const totalCount = allSteps.length;

export function useProgress() {
    const [completedSteps, setCompletedSteps] = useState(() => loadFromStorage());
    const [timestamps, setTimestamps] = useState(() => loadTimestamps());

    const toggleStep = useCallback((stepId) => {
        setCompletedSteps((prev) => {
            const next = new Set(prev);
            if (next.has(stepId)) {
                next.delete(stepId);
            } else {
                next.add(stepId);
                setTimestamps((ts) => {
                    const updated = { ...ts, [stepId]: Date.now() };
                    saveTimestamps(updated);
                    return updated;
                });
            }
            saveToStorage(next);
            return next;
        });
    }, []);

    const resetProgress = useCallback(() => {
        const empty = new Set();
        setCompletedSteps(empty);
        setTimestamps({});
        saveToStorage(empty);
        saveTimestamps({});
    }, []);

    const completedCount = completedSteps.size;
    const completionPercentage = Math.round((completedCount / totalCount) * 100);

    const currentWeek = useMemo(() => {
        for (let i = WEEKS.length - 1; i >= 0; i--) {
            const week = WEEKS[i];
            const hasAny = week.steps.some((s) => completedSteps.has(s.id));
            if (hasAny) return week;
        }
        return WEEKS[0];
    }, [completedSteps]);

    const servicesActivated = useMemo(() => {
        // simple proxy: count weeks with ≥1 step done
        return WEEKS.filter((w) => w.steps.some((s) => completedSteps.has(s.id))).length;
    }, [completedSteps]);

    const weeksFinished = useMemo(() => {
        return WEEKS.filter((w) => w.steps.every((s) => completedSteps.has(s.id))).length;
    }, [completedSteps]);

    return {
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
    };
}
