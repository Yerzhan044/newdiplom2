import React, { useEffect, useState } from 'react';

export default function InteractionGraph({ apiUrl }) {
  const [loading, setLoading] = useState(true);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeTab, setActiveTab] = useState('nodes');

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const baseUrl = apiUrl || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/transactions/graph/interactions?limit=100`);
        const data = await response.json();

        if (!data.nodes || !data.edges) {
          console.error('Invalid graph data');
          setLoading(false);
          return;
        }

        setNodes(data.nodes);
        setEdges(data.edges);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching graph data:', error);
        setLoading(false);
      }
    };

    fetchGraph();
  }, [apiUrl]);

  const getRiskColor = (risk) => {
    if (risk === 'high') return 'bg-red-900 text-red-200 border-red-700';
    if (risk === 'medium') return 'bg-yellow-900 text-yellow-200 border-yellow-700';
    return 'bg-green-900 text-green-200 border-green-700';
  };

  const getRiskBadgeColor = (risk) => {
    if (risk === 'high') return '🔴';
    if (risk === 'medium') return '🟠';
    return '🟢';
  };

  return (
    <div className="h-full w-full flex flex-col bg-gradient-to-br from-gray-900 to-gray-800 text-white rounded-lg overflow-hidden border border-gray-700">
      {/* Header */}
      <div className="bg-black bg-opacity-50 px-6 py-4 border-b border-gray-700">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <span>🌐</span> Transaction Network Analysis
        </h2>
        <p className="text-gray-400 text-sm mt-2">
          {nodes.length} users | {edges.length} connections
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700 bg-black bg-opacity-50">
        <button
          onClick={() => setActiveTab('nodes')}
          className={`px-6 py-3 font-bold transition ${
            activeTab === 'nodes'
              ? 'border-b-2 border-blue-500 text-blue-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          👥 Users ({nodes.length})
        </button>
        <button
          onClick={() => setActiveTab('edges')}
          className={`px-6 py-3 font-bold transition ${
            activeTab === 'edges'
              ? 'border-b-2 border-blue-500 text-blue-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          🔗 Connections ({edges.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-white font-bold">Loading network...</p>
            </div>
          </div>
        ) : activeTab === 'nodes' ? (
          <div className="p-6">
            {/* Nodes Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-600 bg-gray-800">
                    <th className="text-left py-3 px-4">User</th>
                    <th className="text-center py-3 px-4">Country</th>
                    <th className="text-right py-3 px-4">Transactions</th>
                    <th className="text-right py-3 px-4">Blocked</th>
                    <th className="text-center py-3 px-4">Risk Level</th>
                  </tr>
                </thead>
                <tbody>
                  {nodes.map((node) => (
                    <tr
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className="border-b border-gray-700 hover:bg-gray-800 transition cursor-pointer"
                    >
                      <td className="py-3 px-4 font-semibold text-blue-400">
                        {node.label}
                      </td>
                      <td className="py-3 px-4 text-center">🌍 {node.country}</td>
                      <td className="py-3 px-4 text-right text-white font-bold">
                        {node.transactions}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-red-400 font-bold">
                          {node.blocked_count}
                        </span>
                        <span className="text-gray-400"> / {node.transactions}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getRiskColor(node.risk)}`}>
                          {getRiskBadgeColor(node.risk)} {node.risk.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="p-6">
            {/* Edges Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-600 bg-gray-800">
                    <th className="text-left py-3 px-4">From → To</th>
                    <th className="text-right py-3 px-4">Count</th>
                    <th className="text-right py-3 px-4">Fraud</th>
                    <th className="text-right py-3 px-4">Total Amount</th>
                    <th className="text-center py-3 px-4">Status Breakdown</th>
                  </tr>
                </thead>
                <tbody>
                  {edges.map((edge, idx) => (
                    <tr key={idx} className="border-b border-gray-700 hover:bg-gray-800 transition">
                      <td className="py-3 px-4 font-semibold">
                        <span className="text-green-400">User {edge.from}</span>
                        <span className="text-gray-500"> → </span>
                        <span className="text-blue-400">User {edge.to}</span>
                      </td>
                      <td className="py-3 px-4 text-right text-white font-bold">
                        {edge.weight}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-red-400 font-bold">{edge.fraud_count}</span>
                        <span className="text-gray-400"> / {edge.weight}</span>
                      </td>
                      <td className="py-3 px-4 text-right text-yellow-400 font-bold">
                        {edge.total_amount.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex gap-1 justify-center">
                          {edge.statuses.APPROVED > 0 && (
                            <span title={`Approved: ${edge.statuses.APPROVED}`} className="bg-green-600 px-2 py-1 rounded text-xs font-bold">
                              ✅ {edge.statuses.APPROVED}
                            </span>
                          )}
                          {edge.statuses.REVIEW > 0 && (
                            <span title={`Review: ${edge.statuses.REVIEW}`} className="bg-yellow-600 px-2 py-1 rounded text-xs font-bold">
                              ⚠️ {edge.statuses.REVIEW}
                            </span>
                          )}
                          {edge.statuses.BLOCKED > 0 && (
                            <span title={`Blocked: ${edge.statuses.BLOCKED}`} className="bg-red-600 px-2 py-1 rounded text-xs font-bold">
                              ❌ {edge.statuses.BLOCKED}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="bg-slate-800 border-t border-gray-700 p-4">
          <div className="max-w-4xl mx-auto flex justify-between items-start">
            <div>
              <h3 className="text-xl font-bold text-white mb-2">{selectedNode.label}</h3>
              <p className="text-sm text-gray-400">🌍 {selectedNode.country}</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-700 p-3 rounded-lg text-center">
                <p className="text-gray-400 text-xs font-bold uppercase">Transactions</p>
                <p className="text-2xl font-bold text-blue-400">{selectedNode.transactions}</p>
              </div>
              <div className="bg-slate-700 p-3 rounded-lg text-center">
                <p className="text-gray-400 text-xs font-bold uppercase">Blocked</p>
                <p className="text-2xl font-bold text-red-400">{selectedNode.blocked_count}</p>
              </div>
              <div className="bg-slate-700 p-3 rounded-lg text-center">
                <p className="text-gray-400 text-xs font-bold uppercase">Risk</p>
                <p className={`text-2xl font-bold ${
                  selectedNode.risk === 'high' ? 'text-red-400' :
                  selectedNode.risk === 'medium' ? 'text-yellow-400' :
                  'text-green-400'
                }`}>
                  {getRiskBadgeColor(selectedNode.risk)}
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-400 hover:text-white text-2xl"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
