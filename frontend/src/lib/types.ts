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
  created_at: string;
}

export interface Course {
  id: string;
  module_id: string | null;
  title: string;
  description: string | null;
  file_url: string;
  file_type: string;
  created_at: string;
  module_name: string | null;
  teacher_first_name: string | null;
  teacher_last_name: string | null;
}

export interface Module {
  id: string;
  name: string;
  code: string;
  semester: number;
}

export interface Event {
  id: string;
  title: string;
  description: string | null;
  event_type: "exam" | "conference" | "holiday" | "meeting";
  start_date: string;
  end_date: string | null;
  location: string | null;
  created_by: string;
  created_at: string;
}
