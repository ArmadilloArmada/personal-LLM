export type WorkflowNodeType =
  | 'noteTrigger'
  | 'captureTrigger'
  | 'llm'
  | 'personaRag'
  | 'transform'
  | 'branch'
  | 'vaultWrite'
  | 'output';

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  /** When set on edges from a branch node, only follow matching branch */
  when?: 'true' | 'false';
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowRecord {
  id: string;
  name: string;
  description: string;
  icon: string;
  definition: WorkflowDefinition;
}

export interface WorkflowPublic {
  id: string;
  name: string;
  description: string;
  icon: string;
  definition: WorkflowDefinition;
}

export interface ExecutionContext {
  note: {
    path: string;
    title: string;
    content: string;
    tags: string[];
    wikilinks: string[];
    frontmatter: Record<string, unknown>;
  } | null;
  capture?: {
    personaId: string;
    personaName: string;
    userMessage: string;
    assistantMessage: string;
    dailyNotePath: string;
    personaNotePath: string;
  };
  llm: { output: string };
  rag: { context: string; chunks: Array<{ path: string; title: string; snippet: string }> };
  transform: { output: unknown };
  branch: { result: boolean };
  output: { value: unknown };
}
