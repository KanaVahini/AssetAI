import axios from 'axios'

const BASE_URL = "http://localhost:8000"

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json"
  }
})

// POST /ask
// Input:  { question: string, plant_name: string (optional) }
// Output: { answer: string, sources: string[], chunks_used: number }
export const askQuestion = async (question, plantName = null) => {
  const response = await api.post("/ask", 
    JSON.stringify({
      question: question,
      plant_name: plantName
    }),
    {
      headers: { "Content-Type": "application/json" }
    }
  )
  return response.data
}

// POST /upload
// Input:  FormData with file
// Output: { message: string }
// ✅ REPLACE old uploadFile with this
export const uploadFiles = async (files) => {
  const formData = new FormData()
  
  // Append all files with same key "files"
  files.forEach(file => {
    formData.append("files", file)
  })

  const response = await axios.post(`${BASE_URL}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  })
  return response.data
}

// GET /health
export const checkHealth = async () => {
  const response = await api.get("/health")
  return response.data
}

// GET /
export const getStatus = async () => {
  const response = await api.get("/")
  return response.data
}

// POST /rca
export const runRCA = async (equipmentTag) => {
  const response = await api.post("/rca", {
    equipment_tag: equipmentTag
  })
  return response.data
}

// GET /safety
// Output: { safety_report: string, sources: string[], generated_at: string }
export const getSafetyReport = async () => {
  const response = await api.get("/safety")
  return response.data
}

// POST /safety/check
// Input:  equipment tag string, e.g. "P-104"
// Output: { answer: string, sources: string[] }
export const checkEquipmentSafety = async (equipmentTag) => {
  const response = await api.post("/safety/check", {
    equipment_tag: equipmentTag
  })
  return response.data
}

// GET /summary
// Output: { answer: string, sources: string[] }
export const getFullSummary = async () => {
  const response = await api.get("/summary")
  return response.data
}

// POST /summary/document
// Input:  topic string, e.g. "Pump P-104 maintenance history"
// Output: { answer: string, sources: string[] }
export const summarizeTopic = async (topic) => {
  const response = await api.post("/summary/document", {
    topic: topic
  })
  return response.data
}
