export interface User {
  id: string;
  sub?: string;
  email: string;
  role: "student" | "teacher" | "admin";
  is_active: boolean;
  first_name?: string;
  last_name?: string;
  phone?: string;
  address?: string;
  office?: string;
  photo_url?: string | null;
  student_code?: string | null;
  teacher_code?: string | null;
  filiere_id?: string | null;
  filiere_name?: string | null;
  filiere_code?: string | null;
  level_name?: string | null;
  assigned_modules?: AssignedModule[];
  assigned_filieres?: AssignedFiliere[];
  assigned_module_count?: number;
  assigned_filiere_count?: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export interface Conversation {
  id: string;
  title: string;
  context_summary: string | null;
  started_at: string;
  updated_at: string;
  last_message: string | null;
}

export interface Message {
  id: string;
  sender_type: "user" | "assistant" | "system";
  content: string;
  message_type: string;
  artifact?: ChatArtifact | null;
  created_at: string;
}

export interface ChatArtifact {
  type: string;
  file_name?: string;
  download_url?: string;
  mime_type?: string;
  expires_at?: string;
}

export interface Course {
  id: string;
  module_id: string | null;
  title: string;
  description: string | null;
  file_url: string;
  file_type: string;
  index_status?: "pending" | "indexed" | "failed" | string;
  visibility_scope?: "public" | "filiere" | "module";
  filiere_id?: string | null;
  filiere_name?: string | null;
  filiere_code?: string | null;
  created_at: string;
  module_name: string | null;
  teacher_first_name: string | null;
  teacher_last_name: string | null;
  teacher_code?: string | null;
  uploaded_by?: string | null;
  uploader_name?: string | null;
  uploader_role?: string | null;
}

export interface AdminDocument {
  id: string;
  source_id: string;
  title: string | null;
  description: string | null;
  document_category: string;
  source_type: string;
  file_url: string | null;
  file_type: string | null;
  visibility_scope: "public" | "filiere" | "module";
  filiere_id: string | null;
  module_id: string | null;
  storage_path: string | null;
  uploaded_by?: string | null;
  uploader_name?: string | null;
  uploader_role?: string | null;
  accessibility?: string | null;
  chunk_count: number;
  created_at: string;
}

export interface Module {
  id: string;
  name: string;
  code: string;
  semester: number;
  filiere_id?: string | null;
  filiere_name?: string | null;
}

export interface Filiere {
  id: string;
  name: string;
  code: string;
  department_name?: string | null;
}

export interface Event {
  id: string;
  title: string;
  description: string | null;
  event_type: "exam" | "conference" | "holiday" | "meeting";
  start_date: string;
  end_date: string | null;
  location: string | null;
  visibility_scope?: "public" | "filiere" | "module";
  filiere_id?: string | null;
  module_id?: string | null;
  created_by: string;
  created_at: string;
}

export interface AssignedModule {
  id: string;
  name: string;
  code: string;
  semester?: number | null;
  filiere_id?: string | null;
  filiere_name?: string | null;
  filiere_code?: string | null;
  teacher_first_name?: string | null;
  teacher_last_name?: string | null;
}

export interface AssignedFiliere {
  id: string;
  name: string;
  code: string;
}
