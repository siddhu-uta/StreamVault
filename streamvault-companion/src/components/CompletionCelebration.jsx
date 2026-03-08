import { useEffect, useRef } from "react";
import confetti from "canvas-confetti";

export default function CompletionCelebration({ onDismiss }) {
    const firedRef = useRef(false);

    useEffect(() => {
        if (firedRef.current) return;
        firedRef.current = true;

        // Big confetti burst
        confetti({
            particleCount: 180,
            spread: 90,
            origin: { y: 0.5 },
            colors: ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981"],
        });

        // Secondary burst after 600ms
        setTimeout(() => {
            confetti({
                particleCount: 80,
                angle: 60,
                spread: 55,
                origin: { x: 0, y: 0.6 },
                colors: ["#6366f1", "#10b981"],
            });
            confetti({
                particleCount: 80,
                angle: 120,
                spread: 55,
                origin: { x: 1, y: 0.6 },
                colors: ["#a855f7", "#f59e0b"],
            });
        }, 600);
    }, []);

    return (
        <div className="celebration-overlay" role="dialog" aria-modal="true">
            <div className="celebration-card">
                <span className="celebration-emoji">🚀</span>
                <div className="celebration-title">StreamVault Complete!</div>
                <div className="celebration-message">
                    You've built a production-grade serverless event analytics pipeline on AWS.
                    Every service is connected, every alarm is set, every test is green.
                    <br /><br />
                    This belongs on your resume and your GitHub — you earned it.
                </div>
                <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
                    <a
                        id="btn-celebrate-github"
                        href="https://github.com/VinayakSiddu/StreamVault"
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-ghost"
                        style={{ fontSize: "14px", padding: "10px 20px" }}
                    >
                        View on GitHub →
                    </a>
                    <button
                        id="btn-celebrate-dismiss"
                        className="btn"
                        style={{
                            background: "linear-gradient(135deg, #6366f1, #a855f7)",
                            color: "white",
                            fontSize: "14px",
                            padding: "10px 20px",
                            border: "none",
                        }}
                        onClick={onDismiss}
                    >
                        Keep Exploring
                    </button>
                </div>
            </div>
        </div>
    );
}
