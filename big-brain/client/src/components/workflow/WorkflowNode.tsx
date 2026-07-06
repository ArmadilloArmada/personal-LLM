import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';

function WorkflowNode({ data }: NodeProps) {
  const nodeType = String(data.nodeType ?? 'unknown');
  const label = String(data.label ?? nodeType);

  return (
    <div className="flow-node">
      <Handle type="target" position={Position.Left} />
      <div className="flow-node-type">{nodeType}</div>
      <div className="flow-node-label">{label}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export default memo(WorkflowNode);
