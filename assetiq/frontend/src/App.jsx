import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Copilot from './pages/Copilot'
import RCA from './pages/RCA'

export default function App() {
  return (
    <Router>
      <nav>
        <Link to="/">Home</Link> | <Link to="/copilot">Copilot</Link> | <Link to="/rca">RCA</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/copilot" element={<Copilot />} />
        <Route path="/rca" element={<RCA />} />
      </Routes>
    </Router>
  )
}
