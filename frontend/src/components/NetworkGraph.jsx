import React, { useMemo } from 'react';

export default function NetworkGraph({ evidenceBundle }) {
  const { nodes, edges } = useMemo(() => {
    if (!evidenceBundle || evidenceBundle.length === 0) return { nodes: [], edges: [] };

    const nodesMap = new Map();
    const edgesArr = [];
    
    // Process evidence to build nodes and edges
    evidenceBundle.forEach(ev => {
      const tool = ev.source_tool;
      const obs = ev.observation;
      const eid = ev.evidence_id;

      if (tool === 'get_transaction_context') {
        const txNode = { id: obs.transaction_id, type: 'transaction', label: 'Transaction', data: obs, evidenceId: eid };
        const accNode = { id: obs.account_id, type: 'account', label: 'Account', data: null, evidenceId: eid };
        const devNode = { id: obs.device_id, type: 'device', label: 'Device', data: null, evidenceId: eid };
        const merchNode = { id: obs.merchant_id, type: 'merchant', label: 'Merchant', data: null, evidenceId: eid };
        
        nodesMap.set(txNode.id, txNode);
        nodesMap.set(accNode.id, accNode);
        nodesMap.set(devNode.id, devNode);
        nodesMap.set(merchNode.id, merchNode);
        
        edgesArr.push({ source: txNode.id, target: accNode.id, evidenceId: eid });
        edgesArr.push({ source: txNode.id, target: devNode.id, evidenceId: eid });
        edgesArr.push({ source: txNode.id, target: merchNode.id, evidenceId: eid });
      }
      
      if (tool === 'get_account_history') {
        // Account history doesn't inherently add new target nodes except merchants_used, but we only have string IDs for merchants_used
        if (obs.merchants_used) {
          obs.merchants_used.forEach(m => {
            if (!nodesMap.has(m)) {
              nodesMap.set(m, { id: m, type: 'merchant', label: 'Historical Merchant', data: null, evidenceId: eid });
            }
            edgesArr.push({ source: obs.account_id, target: m, evidenceId: eid });
          });
        }
      }
      
      // We could add more relationships here based on get_device_relationships or get_network_relationships 
      // if they explicitly name other node IDs. Currently, they usually return aggregate counts.
    });

    return { nodes: Array.from(nodesMap.values()), edges: edgesArr };
  }, [evidenceBundle]);

  if (nodes.length === 0) {
    return <div className="text-gray-500 italic p-4">No network evidence available.</div>;
  }

  // Simple Force-Directed-like fixed layout for demonstration (Star/Radial layout)
  // We place the transaction in the center and others around it.
  const width = 600;
  const height = 400;
  const cx = width / 2;
  const cy = height / 2;
  
  const txNode = nodes.find(n => n.type === 'transaction');
  const otherNodes = nodes.filter(n => n.type !== 'transaction');
  
  const positionedNodes = nodes.map(n => {
    if (n.type === 'transaction') {
      return { ...n, x: cx, y: cy };
    }
    const idx = otherNodes.indexOf(n);
    const angle = (idx / otherNodes.length) * 2 * Math.PI;
    const r = 140; // fixed radius to avoid overlap, wide enough for typical cases
    return {
      ...n,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle)
    };
  });

  const nodeColor = (type) => {
    switch(type) {
      case 'transaction': return '#58a6ff';
      case 'account': return '#3fb950';
      case 'device': return '#d29922';
      case 'merchant': return '#f85149';
      default: return '#8b949e';
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden relative">
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        {edges.map((e, i) => {
          const source = positionedNodes.find(n => n.id === e.source);
          const target = positionedNodes.find(n => n.id === e.target);
          if (!source || !target) return null;
          return (
            <line 
              key={i} 
              x1={source.x} y1={source.y} 
              x2={target.x} y2={target.y} 
              stroke="#30363d" 
              strokeWidth="2" 
              className="transition-colors hover:stroke-gray-500"
            >
              <title>Evidence ID: {e.evidenceId}</title>
            </line>
          );
        })}
        {positionedNodes.map(n => (
          <g key={n.id} transform={`translate(${n.x}, ${n.y})`} className="cursor-pointer group">
            <title>{n.label}: {n.id}&#10;Evidence ID: {n.evidenceId}</title>
            <circle 
              r="12" 
              fill={nodeColor(n.type)} 
              className="stroke-gray-900 stroke-2 group-hover:stroke-gray-100 transition-all"
            />
            <text 
              y="24" 
              textAnchor="middle" 
              className="text-[10px] fill-gray-400 font-mono group-hover:fill-gray-100"
            >
              {n.id.substring(0, 8)}...
            </text>
          </g>
        ))}
      </svg>
      <div className="absolute top-4 left-4 flex gap-4 text-xs font-medium bg-gray-800/80 px-3 py-2 rounded-lg border border-gray-700 backdrop-blur-sm">
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-brand-500"></div> Tx</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-success-500"></div> Acc</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-warning-500"></div> Dev</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-danger-500"></div> Merch</div>
      </div>
    </div>
  );
}
