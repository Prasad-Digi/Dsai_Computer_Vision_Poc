import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";

/**
 * Lets the user pick HOW to feed the pipeline:
 *  - an existing file already in backend/data/videos (fastest, this is what
 *    you'll use most during POC iteration)
 *  - upload a brand new file straight from the browser
 *  - (once configured) a live CCTV camera from credentials/cctv_credentials.json
 *
 * As soon as a source is picked (existing file selected, or a file chosen
 * for upload), the RAW video previews right in this card - so you can
 * confirm you picked the right clip before spending time running detection
 * on it.
 */
export default function VideoSourceSelector({ onJobStarted }) {
  const [mode, setMode] = useState("existing"); // existing | upload | live
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState("");
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const uploadPreviewUrl = useRef(null); // object URL for a locally chosen (not-yet-uploaded) file

  useEffect(() => {
    api.listVideos().then((v) => {
      setVideos(v);
      if (v.length) setSelectedVideo(v[0]);
    });
    api.listCameras().then(setCameras).catch(() => setCameras([])); // ok if none configured yet
  }, []);

  function handleFileChosen(file) {
    setUploadFile(file);
    if (uploadPreviewUrl.current) URL.revokeObjectURL(uploadPreviewUrl.current);
    uploadPreviewUrl.current = file ? URL.createObjectURL(file) : null;
  }

  async function handleStart() {
    setError("");
    setBusy(true);
    try {
      if (mode === "existing") {
        if (!selectedVideo) throw new Error("Pick a video first");
        const job = await api.processVideo(selectedVideo);
        onJobStarted(job.job_id, selectedVideo);
      } else if (mode === "upload") {
        if (!uploadFile) throw new Error("Choose a file to upload first");
        const list = await api.uploadVideo(uploadFile);
        const job = await api.processVideo(uploadFile.name);
        setVideos(list);
        onJobStarted(job.job_id, uploadFile.name);
      } else if (mode === "live") {
        if (!selectedCamera) throw new Error("Pick a camera first");
        const job = await api.connectStream(selectedCamera, 60);
        onJobStarted(job.job_id, `LIVE: ${selectedCamera}`);
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>1. Choose a video source</h2>

      <div className="tabs">
        <button className={mode === "existing" ? "tab active" : "tab"} onClick={() => setMode("existing")}>
          Existing test video
        </button>
        <button className={mode === "upload" ? "tab active" : "tab"} onClick={() => setMode("upload")}>
          Upload new video
        </button>
        <button className={mode === "live" ? "tab active" : "tab"} onClick={() => setMode("live")}>
          Live CCTV
        </button>
      </div>

      {mode === "existing" && (
        <>
          <select value={selectedVideo} onChange={(e) => setSelectedVideo(e.target.value)}>
            {videos.length === 0 && <option>No videos in data/videos yet</option>}
            {videos.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
          {selectedVideo && (
            <div className="video-wrap">
              <p className="preview-label">Raw video preview</p>
              {/* key= forces the <video> to reload when the selection changes */}
              <video key={selectedVideo} src={api.rawVideoUrl(selectedVideo)} controls width="100%" />
            </div>
          )}
        </>
      )}

      {mode === "upload" && (
        <>
          <input type="file" accept="video/*" onChange={(e) => handleFileChosen(e.target.files[0])} />
          {uploadFile && (
            <div className="video-wrap">
              <p className="preview-label">Raw video preview (not uploaded yet)</p>
              <video key={uploadFile.name} src={uploadPreviewUrl.current} controls width="100%" />
            </div>
          )}
        </>
      )}

      {mode === "live" && (
        <select value={selectedCamera} onChange={(e) => setSelectedCamera(e.target.value)}>
          <option value="">-- select camera --</option>
          {cameras.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
          {cameras.length === 0 && <option disabled>No cameras configured - see credentials/cctv_credentials.json</option>}
        </select>
      )}

      <button className="primary" disabled={busy} onClick={handleStart}>
        {busy ? "Starting..." : "Start Analysis"}
      </button>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
