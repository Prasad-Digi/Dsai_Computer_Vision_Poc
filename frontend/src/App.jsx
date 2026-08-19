import React, { useState } from "react";
import VideoSourceSelector from "./components/VideoSourceSelector.jsx";
import JobProgress from "./components/JobProgress.jsx";
import ResultsDashboard from "./components/ResultsDashboard.jsx";

export default function App() {
  const [activeJob, setActiveJob] = useState(null); // { jobId, sourceLabel }
  const [report, setReport] = useState(null);

  function handleJobStarted(jobId, sourceLabel) {
    setReport(null);
    setActiveJob({ jobId, sourceLabel });
  }

  function handleCompleted(results) {
    setReport(results);
  }

  function reset() {
    setActiveJob(null);
    setReport(null);
  }

  return (
    <div className="app">
      <header>
        <h1>Vision Analytics POC</h1>
        <p>People &amp; vehicle detection · dwell time · uniform/cap/shoes attributes — powered by YOLO26</p>
      </header>

      <VideoSourceSelector onJobStarted={handleJobStarted} />

      {activeJob && !report && (
        <JobProgress jobId={activeJob.jobId} sourceLabel={activeJob.sourceLabel} onCompleted={handleCompleted} />
      )}

      {report && (
        <>
          <ResultsDashboard report={report} />
          <button className="secondary" onClick={reset}>Run another video</button>
        </>
      )}
    </div>
  );
}
