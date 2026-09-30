// Mirrors the initial FastAPI response schemas; /api/openapi.json is authoritative.
export interface Admin {
  id: string;
  email: string;
  created_at: string;
  last_login: string | null;
}

export interface Activity {
  id: string;
  action: string;
  actor_type: string;
  created_at: string;
}

export interface ClientProcess {
  id: string;
  full_name: string;
  phone_number: string;
  status: string;
  created_at: string;
  updated_at: string;
  link_expires_at: string | null;
}
export interface IssuedLink {
  process_id: string;
  token: string;
  registration_url: string;
  expires_at: string;
}
export interface ProcessList {
  items: ClientProcess[];
  total: number;
  page: number;
  page_size: number;
}
export interface Overview {
  total_clients: number;
  pending_registration: number;
  submitted_videos: number;
  expired_links: number;
}
export interface ProcessDetail extends ClientProcess {
  date_of_birth: string | null;
  passport_number: string | null;
  consent: { consent_version: string; accepted_at: string } | null;
  video: {
    id: string;
    mime_type: string;
    file_size: number;
    duration: number;
    uploaded_at: string;
    deleted_at: string | null;
    status: string;
  } | null;
  history: Activity[];
}
export interface PublicState {
  full_name: string;
  registered: boolean;
  consent_accepted: boolean;
  expires_at: string;
  consent_version: string;
  consent_text: string;
  max_upload_bytes: number;
  max_video_seconds: number;
}
