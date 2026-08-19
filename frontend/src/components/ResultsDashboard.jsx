import React from "react";
import { api } from "../api";

function BoolBadge({ value }) {
  if (value === null || value === undefined) return <span className="badge unknown">n/a</span>;
  return value ? <span className="badge yes">Yes</span> : <span className="badge no">No</span>;
}

export default function ResultsDashboard({ report }) {
  const annotatedUrl = report.annotated_video_url ? `${api.baseUrl}${report.annotated_video_url}` : null;
  const rawUrl = report.raw_video_url ? `${api.baseUrl}${report.raw_video_url}` : null;

  return (
    <div className="card">
      <h2>3. Results — {report.source_video}</h2>

      <div className="stat-row">
        <div className="stat"><span>{report.total_unique_persons}</span><label>People detected</label></div>
        <div className="stat"><span>{report.total_unique_vehicles}</span><label>Vehicles detected</label></div>
        <div className="stat"><span>{report.video_duration_sec}s</span><label>Video duration</label></div>
      </div>

      {(annotatedUrl || rawUrl) && (
        <div className="video-compare">
          {rawUrl && (
            <div className="video-wrap">
              <h3>Raw video</h3>
              <video src={rawUrl} controls width="100%" />
            </div>
          )}
          {annotatedUrl && (
            <div className="video-wrap">
              <h3>Annotated video (boxes + labels + live attributes)</h3>
              <video src={annotatedUrl} controls width="100%" />
            </div>
          )}
        </div>
      )}

      <h3>Vehicle breakdown</h3>
      <table>
        <thead><tr><th>Type</th><th>Count</th></tr></thead>
        <tbody>
          {report.vehicle_type_breakdown.map((v) => (
            <tr key={v.type}><td>{v.type}</td><td>{v.count}</td></tr>
          ))}
          {report.vehicle_type_breakdown.length === 0 && <tr><td colSpan={2}>No vehicles detected</td></tr>}
        </tbody>
      </table>

      <h3>People — dwell time & attributes</h3>
      <table>
        <thead>
          <tr>
            <th>Track ID</th><th>First seen (s)</th><th>Last seen (s)</th><th>Dwell (s)</th>
            <th>Jacket</th><th>Uniform</th><th>Cap</th><th>Helmet</th><th>Shoes</th>
          </tr>
        </thead>
        <tbody>
          {report.persons.map((p) => (
            <tr key={p.track_id}>
              <td>{p.track_id}</td>
              <td>{p.first_seen_sec}</td>
              <td>{p.last_seen_sec}</td>
              <td>{p.dwell_time_sec}</td>
              <td><BoolBadge value={p.wearing_jacket} /></td>
              <td><BoolBadge value={p.wearing_uniform} /></td>
              <td><BoolBadge value={p.wearing_cap} /></td>
              <td><BoolBadge value={p.wearing_helmet} /></td>
              <td><BoolBadge value={p.wearing_shoes} /></td>
            </tr>
          ))}
          {report.persons.length === 0 && <tr><td colSpan={9}>No people detected</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
