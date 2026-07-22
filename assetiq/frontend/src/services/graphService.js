import axios from "axios";

const API_BASE = "http://localhost:8000";

export async function fetchGraphData() {
  const response = await axios.get(`${API_BASE}/graph`);
  return response.data; // { nodes: [...], edges: [...] }
}