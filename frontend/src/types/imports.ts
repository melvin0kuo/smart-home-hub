export interface ImportCandidate {
  entity_id: string;
  name: string;
  type: string;
  supported: boolean;
  available: boolean;
  already_imported: boolean;
  can_test: boolean;
  state: string;
  tested_actions: string[];
  capabilities: string[];
  note: string;
}
export interface ImportItem {
  entity_id: string;
  name: string;
  room: string;
  protected: boolean;
  enable_control: boolean;
}
export interface ImportDiscovery {
  mode: "mock" | "real";
  connected: boolean;
  candidates: ImportCandidate[];
}
