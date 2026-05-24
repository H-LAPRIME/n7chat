"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Upload } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Filiere, Module } from "@/lib/types";

type DocumentCategory = "admin_document" | "timetable" | "news" | "event" | "other";

export default function DocumentsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<DocumentCategory>("admin_document");
  const [visibilityScope, setVisibilityScope] = useState<"public" | "filiere" | "module">("public");
  const [selectedFiliere, setSelectedFiliere] = useState("");
  const [selectedModule, setSelectedModule] = useState("");
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [modules, setModules] = useState<Module[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (user?.role !== "admin") {
      router.push("/dashboard/chat");
    }
  }, [router, user]);

  useEffect(() => {
    if (user?.role !== "admin") return;
    async function loadAudienceOptions() {
      try {
        const [filiereData, moduleData] = await Promise.all([
          fetchApi<Filiere[]>("/courses/filieres"),
          fetchApi<Module[]>("/courses/modules"),
        ]);
        setFilieres(filiereData);
        setModules(moduleData);
      } catch (error) {
        console.error(error);
      }
    }
    void loadAudienceOptions();
  }, [user]);

  if (user?.role !== "admin") return null;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;

    setSubmitting(true);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_category", category);
      formData.append("visibility_scope", visibilityScope);
      if (visibilityScope === "filiere") formData.append("filiere_id", selectedFiliere);
      if (visibilityScope === "module") formData.append("module_id", selectedModule);
      if (title) formData.append("title", title);
      if (description) formData.append("description", description);

      await fetchApi("/documents/upload", {
        method: "POST",
        body: formData,
      });

      setFile(null);
      setTitle("");
      setDescription("");
      setCategory("admin_document");
      setVisibilityScope("public");
      setSelectedFiliere("");
      setSelectedModule("");
      setMessage("Document uploaded. It will be available in chat after indexing finishes.");
    } catch {
      setMessage("Upload failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text">Admin Documents</h1>
        <p className="text-text-muted mt-1">
          Upload public academic documents for the assistant to search.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-border rounded-xl p-6 shadow-sm space-y-5">
        <div className="flex items-center gap-3 pb-4 border-b border-border">
          <div className="w-11 h-11 bg-primary-light rounded-lg flex items-center justify-center text-primary">
            <FileText size={22} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-text">Upload Document</h2>
            <p className="text-sm text-text-muted">PDF, DOCX, PPTX, text, markdown, or CSV.</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-text-muted mb-1">File</label>
          <input
            type="file"
            required
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="w-full text-sm border border-border rounded-lg p-2 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-light file:text-primary hover:file:bg-primary hover:file:text-white transition-colors"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-text-muted mb-1">Title</label>
            <input
              type="text"
              className="input-field"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Defaults to filename"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-text-muted mb-1">Category</label>
            <select
              className="input-field bg-white"
              value={category}
              onChange={(event) => setCategory(event.target.value as DocumentCategory)}
            >
              <option value="admin_document">Administrative document</option>
              <option value="timetable">Timetable</option>
              <option value="news">News</option>
              <option value="event">Event</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-text-muted mb-1">Description</label>
          <textarea
            className="input-field resize-none h-24"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Short context for search results"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-text-muted mb-1">Audience</label>
            <select
              className="input-field bg-white"
              value={visibilityScope}
              onChange={(event) => setVisibilityScope(event.target.value as typeof visibilityScope)}
            >
              <option value="public">Public</option>
              <option value="filiere">Specific filiere</option>
              <option value="module">Specific module</option>
            </select>
          </div>
          {visibilityScope === "filiere" && (
            <div>
              <label className="block text-sm font-semibold text-text-muted mb-1">Filiere</label>
              <select required className="input-field bg-white" value={selectedFiliere} onChange={(event) => setSelectedFiliere(event.target.value)}>
                <option value="">Select filiere</option>
                {filieres.map((filiere) => (
                  <option key={filiere.id} value={filiere.id}>{filiere.code} - {filiere.name}</option>
                ))}
              </select>
            </div>
          )}
          {visibilityScope === "module" && (
            <div>
              <label className="block text-sm font-semibold text-text-muted mb-1">Module</label>
              <select required className="input-field bg-white" value={selectedModule} onChange={(event) => setSelectedModule(event.target.value)}>
                <option value="">Select module</option>
                {modules.map((module) => (
                  <option key={module.id} value={module.id}>{module.code} - {module.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-border gap-4">
          <p className={`text-sm ${message.includes("failed") ? "text-danger" : "text-emerald-600"}`}>
            {message}
          </p>
          <button type="submit" disabled={!file || submitting} className="btn-primary px-6 flex items-center gap-2">
            <Upload size={18} /> {submitting ? "Uploading..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}
