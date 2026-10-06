export type QueryRequirement = {
  need: string;
  state: string;
  evidence_ids: string[];
};

export type LocalizedEvidence = {
  language: string;
  evidence_id: string;
  claim_type: string | null;
  text: string | null;
  source_id: string;
  source_version: string | null;
  reference: string | null;
  source_url: string | null;
  work_title: string | null;
  authority_scope: string | null;
};

export type QueryEvidence = {
  evidence_id: string;
  domain: string;
  source_id: string;
  source_version: string | null;
  reference: string | null;
  source_url: string | null;
  work_title: string | null;
  author_name: string | null;
  institution: string | null;
  publisher: string | null;
  localized: LocalizedEvidence | null;
  claim_type: string | null;
  claim_value: string | null;
  used_in_answer: boolean;
  text: string | null;
  display_excerpt: string | null;
};

export type QueryCitation = {
  marker: string;
  evidence_id: string;
  domain: string;
  source_id: string;
  source_version: string | null;
  reference: string | null;
  source_url: string | null;
  work_title: string | null;
  author_name: string | null;
  institution: string | null;
  publisher: string | null;
};

export type StructuredClaim = {
  axis_id: string;
  claim_id: string;
  text: string;
  evidence_ids: string[];
};

export type QueryConflict = {
  type: string;
  group_id: string;
  evidence_ids: string[];
};

export type QuranVerificationCandidate = {
  reference: string;
  canonical_text: string;
  source_id: string | null;
  score: number;
};

export type QuranVerificationDifference = {
  kind: string;
  expected: string[];
  received: string[];
  is_substantive: boolean;
};

export type QuranVerificationResult = {
  status: string;
  input_text?: string | null;
  candidates: QuranVerificationCandidate[];
  differences: QuranVerificationDifference[];
  has_substantive_difference?: boolean;
};

export type QueryIntegrityReport = {
  literal_source_integrity: string;
  claims_checked: number;
  claim_ids: string[];
  linked_evidence_ids: string[];
  has_limitations: boolean;
  limitation_count: number;
  potential_source_conflict: boolean;
  conflict_count: number;
  conflict_types: string[];
  conflict_group_ids: string[];
  semantic_claim_verification: string;
  semantic_verification_issues: string[];
};

export type QueryExperienceTraceStep = {
  key: string;
  label: string;
  status: "complete" | "warning" | "blocked" | string;
  summary: string;
  evidence_ids: string[];
  source_ids: string[];
};

export type QueryExperience = {
  state:
    | "verified"
    | "grounded"
    | "limited"
    | "conflict"
    | "needs_more_evidence"
    | "regenerate"
    | "blocked"
    | "expert_review"
    | "abstained"
    | string;
  severity: "success" | "info" | "warning" | "danger" | string;
  label: string;
  headline: string;
  detail: string;
  can_publish: boolean;
  evidence_count: number;
  used_evidence_count: number;
  source_count: number;
  trace: QueryExperienceTraceStep[];
};

export type ExpertReviewConflict = {
  conflict_type: string;
  group_id: string;
  evidence_ids: string[];
};

export type ExpertReviewPacket = {
  case_id: string;
  status: string;
  question: string;
  intent: string;
  risk_tags: string[];
  escalation_reasons: string[];
  evidence_coverage: number;
  resolution_coverage: number;
  required_assessments: QueryRequirement[];
  unresolved_needs: string[];
  evidence: Array<Record<string, unknown>>;
  conflicts: ExpertReviewConflict[];
};

export type QueryResponse = {
  request_id: string;
  question: string;
  understanding: {
    intent: string;
    risk_tags: string[];
    entities: Array<{
      entity_type: string;
      value: string;
    }>;
    context_requirement: {
      required: string[];
      optional: string[];
    };
    confidence: number;
  };
  action: string;
  has_answer: boolean;
  answer: string | null;
  limitations: string[];
  citations: QueryCitation[];
  claims: StructuredClaim[];
  integrity_report: QueryIntegrityReport | null;
  experience: QueryExperience | null;
  evidence_coverage: number;
  resolution_coverage: number;
  requirements: QueryRequirement[];
  conflicts: QueryConflict[];
  evidence: QueryEvidence[];
  quran_verification: QuranVerificationResult | null;
  unavailable_domains: string[];
  expert_review: ExpertReviewPacket | null;
};

export type QueryRequest = {
  question: string;
  quran_reference?: string;
  language?: "ar" | "en";
};

const API_BASE_URL = (
  import.meta.env.VITE_BASIRA_API_URL ?? "http://127.0.0.1:8001"
).replace(/\/$/, "");

export async function queryBasira(
  payload: QueryRequest,
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Basira API request failed (${response.status})`);
  }

  return (await response.json()) as QueryResponse;
}

export type EvidenceDetail = {
  evidence_id: string;
  domain: string;
  source_id: string;
  source_version: string | null;
  reference: string | null;
  source_url: string | null;
  work_title: string | null;
  author_name: string | null;
  institution: string | null;
  publisher: string | null;
  text: string;
};

export async function getEvidenceDetail(
  evidenceId: string,
): Promise<EvidenceDetail> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(evidenceId)}`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(`Evidence request failed (${response.status})`);
  }

  return (await response.json()) as EvidenceDetail;
}
