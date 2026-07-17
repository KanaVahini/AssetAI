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
export const uploadFile = async (file) => {
  const formData = new FormData()
  formData.append("file", file)

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