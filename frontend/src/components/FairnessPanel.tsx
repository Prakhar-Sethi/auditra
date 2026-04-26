import { useState, useEffect } from 'react'
import { FairnessMetrics } from '../services/api'

interface Props {
  metrics: FairnessMetrics[]
  mitigatedMetrics: FairnessMetrics[]
}

type Status = 'good' | 'warn' | 'bad'

function getStatus(key: string, val: number): Status {
  if (key === 'disparate_impact_ratio') {
    if (val >= 0.9) return 'good'
    if (val >= 0.8) return 'warn'
    return 'bad'
  }
  const abs = Math.abs(val)
  if (abs <= 0.1) return 'good'
  if (abs <= 0.2) return 'warn'
  return 'bad'
}

const STATUS: Record<Status, { text: string; bg: string; border: string; glow: string }> = {
  good: { text: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-600/30', glow: '#22c55e' },
  warn: { text: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-600/30', glow: '#eab308' },
  bad:  { text: 'text-red-400',   bg: 'bg-red-400/10',   border: 'border-red-700/40',    glow: '#ef4444' },
}

function AnimBar({ fill, color, animated, delay = 0 }: {
  fill: number; color: string; animated: boolean; delay?: number
}) {
  const pct = Math.min(100, Math.max(0, fill * 100))
  return (
    <div className="relative h-2.5 bg-slate-700/80 rounded-full overflow-hidden">
      <div
        className="absolute left-0 top-0 h-full rounded-full"
        style={{
          width: animated ? `${pct}%` : '0%',
          transition: `width 1.1s cubic-bezier(0.4,0,0.2,1) ${delay}ms`,
          background: `linear-gradient(to right, ${color}50, ${color})`,
          boxShadow: animated ? `0 0 8px ${color}60` : 'none',
        }}
      />
    </div>
  )
}

const METRICS = [
  {
    key: 'statistical_parity_diff' as const,
    label: 'Statistical Parity',
    abbrev: 'SPD',
    desc: 'Prediction rate gap between groups',
    scale: 0.5,
    paper: { ref: "Kamiran '12", val: 0.1965 },
  },
  {
    key: 'disparate_impact_ratio' as const,
    label: 'Disparate Impact',
    abbrev: 'DI',
    desc: '80% rule — ratio of group prediction rates',
    scale: 2.0,
    paper: { ref: "Feldman '15", val: 0.36 },
    isDI: true,
  },
  {
    key: 'equal_opportunity_diff' as const,
    label: 'Equal Opportunity',
    abbrev: 'EOD',
    desc: 'True positive rate gap',
    scale: 0.5,
  },
  {
    key: 'average_odds_diff' as const,
    label: 'Average Odds',
    abbrev: 'AOD',
    desc: 'Avg of FPR and TPR differences',
    scale: 0.5,
  },
]

export default function FairnessPanel({ metrics, mitigatedMetrics }: Props) {
  const [sel, setSel] = useState(0)
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    setAnimated(false)
    const t = setTimeout(() => setAnimated(true), 80)
    return () => clearTimeout(t)
  }, [sel, metrics])

  if (!metrics?.length) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-slate-500 text-sm">No fairness metrics — run audit with outcome column</p>
      </div>
    )
  }

  const m = metrics[sel]
  const mit = mitigatedMetrics?.find(x => x.protected_attribute === m.protected_attribute)

  return (
    <div className="flex flex-col h-full overflow-y-auto space-y-3 pr-0.5">
      {/* Attribute tabs */}
      {metrics.length > 1 && (
        <div className="flex gap-1 shrink-0">
          {metrics.map((x, i) => (
            <button
              key={x.protected_attribute}
              onClick={() => setSel(i)}
              className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-colors
                ${sel === i ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'}`}
            >
              {x.protected_attribute}
            </button>
          ))}
        </div>
      )}

      {/* Context line */}
      <div className="shrink-0 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
        <span>outcome: <span className="text-slate-300 font-mono">{m.outcome_column}</span></span>
        <span>positive: <span className="text-slate-300 font-mono">{m.positive_outcome}</span></span>
        <span>privileged: <span className="text-slate-300 font-mono">{m.privileged_group}</span></span>
        {m.model_accuracy_overall > 0 && (
          <span>accuracy: <span className="text-slate-300">{(m.model_accuracy_overall * 100).toFixed(1)}%</span></span>
        )}
      </div>

      {/* Metric cards */}
      <div className="space-y-2.5 shrink-0">
        {METRICS.map((row, idx) => {
          const raw = m[row.key]
          const mitigated = mit ? mit[row.key] : null
          const rawStatus = getStatus(row.key, raw)
          const mitStatus = mitigated !== null ? getStatus(row.key, mitigated) : null
          const rawC = STATUS[rawStatus]
          const mitC = mitStatus ? STATUS[mitStatus] : null

          const rawFill = row.isDI
            ? Math.min(1, raw / row.scale)
            : Math.min(1, Math.abs(raw) / row.scale)
          const mitFill = mitigated !== null
            ? (row.isDI ? Math.min(1, mitigated / row.scale) : Math.min(1, Math.abs(mitigated) / row.scale))
            : null

          const improved = mitigated !== null && row.isDI
            ? mitigated > raw
            : mitigated !== null ? Math.abs(mitigated) < Math.abs(raw) : false

          return (
            <div key={row.key} className={`rounded-xl border p-3 ${rawC.bg} ${rawC.border} transition-all`}>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white text-xs font-bold">{row.label}</span>
                    <span className={`text-xs font-black px-1.5 py-0.5 rounded font-mono ${rawC.bg} ${rawC.text} border ${rawC.border}`}>
                      {row.abbrev}
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs mt-0.5">{row.desc}</p>
                </div>
                <div className="text-right shrink-0">
                  <div className={`text-base font-black font-mono ${rawC.text}`}>
                    {raw.toFixed(3)}
                  </div>
                  {mitigated !== null && mitC && (
                    <div className={`text-xs font-bold font-mono flex items-center gap-1 justify-end ${mitC.text}`}>
                      {improved ? '▼' : '▲'} {mitigated.toFixed(3)}
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 w-14 shrink-0">Unmitigated</span>
                  <div className="flex-1">
                    <AnimBar fill={rawFill} color={rawC.glow} animated={animated} delay={idx * 80} />
                  </div>
                </div>
                {mitFill !== null && mitC && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 w-14 shrink-0">Mitigated</span>
                    <div className="flex-1">
                      <AnimBar fill={mitFill} color={mitC.glow} animated={animated} delay={idx * 80 + 200} />
                    </div>
                  </div>
                )}
              </div>

              {row.paper && (
                <div className="mt-1.5 text-xs text-slate-600 flex items-center gap-1">
                  <span className="inline-block w-3 border-t border-dashed border-slate-600" />
                  paper baseline ({row.paper.ref}): {row.paper.val}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Group breakdown */}
      {Object.keys(m.group_metrics).length > 0 && (
        <div className="shrink-0">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
            Group Breakdown — {m.protected_attribute}
          </h4>
          <div className="space-y-2">
            {Object.entries(m.group_metrics).map(([grp, gm]) => {
              const actualPct = gm.base_rate
              const predPct = gm.prediction_rate
              return (
                <div key={grp} className="bg-slate-800/60 rounded-lg p-2.5 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold text-slate-200 truncate">{grp}</span>
                    <span className="text-xs text-slate-500 ml-2 shrink-0">{gm.size.toLocaleString()} rows</span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 w-14 shrink-0">Actual</span>
                      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500/70 rounded-full"
                          style={{
                            width: animated ? `${actualPct * 100}%` : '0%',
                            transition: 'width 1s cubic-bezier(0.4,0,0.2,1) 400ms',
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-400 w-10 text-right shrink-0">
                        {(actualPct * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 w-14 shrink-0">Predicted</span>
                      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-red-500/70 rounded-full"
                          style={{
                            width: animated ? `${predPct * 100}%` : '0%',
                            transition: 'width 1s cubic-bezier(0.4,0,0.2,1) 500ms',
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-400 w-10 text-right shrink-0">
                        {(predPct * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="mt-1.5 flex gap-3 text-xs text-slate-600">
                    <span>TPR {(gm.tpr * 100).toFixed(1)}%</span>
                    <span>FPR {(gm.fpr * 100).toFixed(1)}%</span>
                    <span>Acc {(gm.accuracy * 100).toFixed(1)}%</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
