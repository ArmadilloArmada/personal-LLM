/** Shared types between Big Brain and Persona integration */

export type CaptureMode = 'every_turn' | 'manual' | 'session_end' | 'starred';

export interface CapturePayload {
  personaId: string;
  personaName?: string;
  workspaceId?: string;
  userMessage: string;
  assistantMessage: string;
  mode?: string;
  sessionId?: string;
  captureMode?: CaptureMode;
  starred?: boolean;
  autoTitle?: string;
  redact?: boolean;
}

export interface CaptureResult {
  ok: boolean;
  dailyNotePath: string;
  personaNotePath: string;
  sessionNotePath?: string;
  topicNotePath?: string;
  skipped?: boolean;
  reason?: string;
}

export type GraphNodeKind = 'persona' | 'chat' | 'session' | 'project' | 'note';

export interface GraphNode {
  id: string;
  title: string;
  kind: GraphNodeKind;
}

export interface BrainConfig {
  captureMode: CaptureMode;
  captureEnabled: boolean;
  ragEnabled: boolean;
  ragMaxChunks: number;
  personaApiUrl: string;
  onCaptureWorkflowId?: string;
}

export const DEFAULT_BRAIN_CONFIG: BrainConfig = {
  captureMode: 'every_turn',
  captureEnabled: true,
  ragEnabled: true,
  ragMaxChunks: 5,
  personaApiUrl: 'http://127.0.0.1:8765',
};
