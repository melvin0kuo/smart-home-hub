export type IntegrationOption = {
  domain: string;
  name: string;
  category: string;
  keywords: string;
  available: boolean;
  requirements: string;
  instructions: string;
  documentation_url: string | null;
  setup_url: string | null;
};
export type OnboardingData = {
  mode: "mock" | "real";
  catalog_status: "available" | "unavailable" | "demo";
  discovery_status: "available" | "unavailable" | "demo";
  catalog: IntegrationOption[];
  discovered: {
    id: number;
    domain: string;
    name: string;
    source: string;
    setup_url: string | null;
  }[];
  warnings: string[];
  local_only_url: boolean;
};
