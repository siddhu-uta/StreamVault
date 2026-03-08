import { useState } from "react";

export default function Header({ onReset, completionPercentage }) {
    const [showConfirm, setShowConfirm] = useState(false);

    function handleReset() {
        onReset();
        setShowConfirm(false);
    }

    return (
        <>
            <header className="header">
                <div className="header-logo">
                    <div className="header-logo-icon">⚡</div>
                    <div>
                        <div className="header-title">StreamVault Learning Companion</div>
                        <div className="header-subtitle">Interactive Architecture Guide · {completionPercentage}% Complete</div>
                    </div>
                </div>

                <div className="header-actions">
                    <a
                        id="btn-arch-doc"
                        href="https://github.com/VinayakSiddu/StreamVault/blob/main/ARCHITECTURE.md"
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-ghost"
                    >
                        <span>📄</span>
                        <span>Architecture Doc</span>
                    </a>
                    <button
                        id="btn-reset"
                        className="btn btn-danger"
                        onClick={() => setShowConfirm(true)}
                    >
                        <span>↺</span>
                        <span>Reset Progress</span>
                    </button>
                </div>
            </header>

            {showConfirm && (
                <div className="dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
                    <div className="dialog-card">
                        <div className="dialog-title" id="dialog-title">Reset all progress?</div>
                        <div className="dialog-message">
                            This will uncheck all steps and clear your saved progress from localStorage.
                            Your actual AWS resources are not affected — only this tracker resets.
                        </div>
                        <div className="dialog-actions">
                            <button
                                id="btn-reset-cancel"
                                className="btn btn-ghost"
                                onClick={() => setShowConfirm(false)}
                            >
                                Cancel
                            </button>
                            <button
                                id="btn-reset-confirm"
                                className="btn btn-danger"
                                onClick={handleReset}
                            >
                                Yes, Reset
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
