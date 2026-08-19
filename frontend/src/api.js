// api.js
// Every backend call lives here. If the backend URL or an endpoint path
// changes, this is the ONLY file you need to touch.
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

export const api = {
  baseUrl: API_BASE_URL,

  rawVideoUrl: (filename) => `${API_BASE_URL}/raw-videos/${encodeURIComponent(filename)}`,

  listVideos: () => client.get("/api/videos/list").then((r) => r.data.videos),

  uploadVideo: (file) => {
    const form = new FormData();
    form.append("file", file);
    return client
      .post("/api/videos/upload", form, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data.videos);
  },

  processVideo: (filename, saveAnnotatedVideo = true) =>
    client
      .post("/api/videos/process", { filename, save_annotated_video: saveAnnotatedVideo })
      .then((r) => r.data),

  getJobStatus: (jobId) => client.get(`/api/videos/jobs/${jobId}`).then((r) => r.data),

  getJobResults: (jobId) => client.get(`/api/videos/jobs/${jobId}/results`).then((r) => r.data),

  listCameras: () => client.get("/api/streams/cameras").then((r) => r.data.cameras),

  connectStream: (cameraName, durationSeconds = 60) =>
    client
      .post("/api/streams/connect", { camera_name: cameraName, duration_seconds: durationSeconds })
      .then((r) => r.data),
};
