import { Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { checkHealth } from '../services/api'

export default function Sidebar() {
  const location = useLocation()
  const [online, setOnline] = useState(null)

  useEffect(() => {
    checkHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  const items = [
    { path: '/', label: 'Home', icon: '⌂' },
    { path: '/copilot', label: 'Copilot', icon: '◈' },
    { path: '/upload', label: 'Upload', icon: '⇧' },
    { path: '/rca', label: 'RCA', icon: '⚡' },
    { path: '/safety', label: 'Safety', icon: '⛨' },
    { path: '/summary', label: 'Summary', icon: '▤' },
  ]

  return (
    <div className="sidebar">
      <div className="hazard-trim" />
      <div className="sidebar__inner">
        <div className="sidebar__brand">
          <span className="sidebar__mark">◎</span>
          <span className="sidebar__name">ASSET<b>IQ</b></span>
        </div>

        <nav className="sidebar__nav">
          {items.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={
                'sidebar__link' +
                (location.pathname === item.path ? ' sidebar__link--active' : '')
              }
            >
              <span className="sidebar__icon">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="sidebar__status">
          <span
            className={
              'status-dot' +
              (online === true ? ' status-dot--green' : '') +
              (online === false ? ' status-dot--red' : '')
            }
          />
          <span className="sidebar__status-label">
            {online === null && 'CHECKING…'}
            {online === true && 'BACKEND ONLINE'}
            {online === false && 'BACKEND OFFLINE'}
          </span>
        </div>
      </div>
    </div>
  )
}
