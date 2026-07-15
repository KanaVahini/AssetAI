import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import KnowledgeField from '../components/KnowledgeField'

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.12, delayChildren: 1.4 }
  }
}

const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } }
}

export default function Home() {
  return (
    <div className="hero">
      <KnowledgeField />
      <div className="hero__vignette" />

      <motion.div
        className="hero__content"
        variants={container}
        initial="hidden"
        animate="show"
      >
        <motion.span className="eyebrow" variants={item}>
          INDUSTRIAL KNOWLEDGE INTELLIGENCE
        </motion.span>

        <motion.h1 className="hero__title" variants={item}>
          Seven systems.
          <br />
          <span className="hero__title-accent">One brain.</span>
        </motion.h1>

        <motion.p className="hero__subtitle" variants={item}>
          Engineers spend 35% of their working hours searching for
          information that already exists — scattered across P&amp;IDs,
          work orders, SOPs, and inspection archives that don't talk to
          each other. AssetIQ reads all of it and answers in seconds,
          with the source attached.
        </motion.p>

        <motion.div className="hero__actions" variants={item}>
          <Link to="/copilot" className="btn btn--primary">
            Ask the Copilot →
          </Link>
          <Link to="/upload" className="btn btn--ghost">
            Upload documents
          </Link>
        </motion.div>

        <motion.div className="readout-strip" variants={item}>
          <div className="readout">
            <span className="readout__value">18–22%</span>
            <span className="readout__label">UNPLANNED DOWNTIME</span>
          </div>
          <div className="readout-strip__divider" />
          <div className="readout">
            <span className="readout__value">7–12</span>
            <span className="readout__label">DISCONNECTED SYSTEMS / PLANT</span>
          </div>
          <div className="readout-strip__divider" />
          <div className="readout">
            <span className="readout__value">25%</span>
            <span className="readout__label">ENGINEERS RETIRING THIS DECADE</span>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
