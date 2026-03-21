import ReactFlow, { Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'

import type { Issue, PipelineIR } from '../../lib/api/types'

type Props = {
  ir: PipelineIR | null
  issues: Issue[]
}

export function PipelineGraphPanel({ ir, issues }: Props) {
  if (!ir || ir.nodes.length === 0) {
    return (
      <div className="stack">
        <h2>Pipeline Graph</h2>
        <p className="hint">Analyze a file to render graph nodes and edges.</p>
      </div>
    )
  }

  const issueNodeIds = new Set(issues.flatMap((issue) => issue.node_ids))
  const nodes = ir.nodes.map((node, idx) => ({
    id: node.id,
    data: { label: `${node.label} (${node.node_type})` },
    position: { x: idx * 220, y: 90 },
    style: issueNodeIds.has(node.id)
      ? { border: '1px solid #ef4444', background: '#fff1f2', width: 180 }
      : { border: '1px solid #d1d5db', width: 180 },
  }))
  const edges = ir.edges.map((edge, idx) => ({
    id: `e-${idx}-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    animated: true,
  }))

  return (
    <div className="stack">
      <h2>Pipeline Graph</h2>
      <div className="graph-wrap">
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
