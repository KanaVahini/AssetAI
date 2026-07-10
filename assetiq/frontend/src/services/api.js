import axios from 'axios'

const client = axios.create({ baseURL: 'http://localhost:8000' })

export function askQuestion(query) {
  return client.post('/ask', { query })
}

export function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  return client.post('/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export default client
