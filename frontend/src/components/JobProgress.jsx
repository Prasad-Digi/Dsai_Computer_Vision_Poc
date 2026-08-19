import React, { useEffect, useState } from "react";
import { api } from "../api";

/**
 * Polls GET /api/videos/jobs/{job_id} every 2s until status is
 * "completed" or "failed", then hands the finished job up to the parent.
 */
export default function JobProgress({ jobId, sourceLabel, onCompleted }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const interval = setInterval(async () => {
      const s = await api.getJobStatus(jobId);
      if (cancelled) return;
      setStatus(s);
      if (s.status === "completed") {
        clearInterval(interval);
        const results = await api.getJobResults(jobId);
        onCompleted(results);
      } else if (s.status === "failed") {
        clearInterval(interval);
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [jobId]);

  return (
    <div className="card">
      <h2>2. Processing: {sourceLabel}</h2>
      <p>Job ID: <code>{jobId}</code></p>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${status?.progress_percent || 0}%` }} />
      </div>
      <p>{status?.progress_percent ?? 0}% - status: {status?.status ?? "starting..."}</p>
      {status?.error && <p className="error">{status.error}</p>}
    </div>
  );
}
