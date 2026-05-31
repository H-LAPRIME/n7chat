"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ExternalLink, FileText, Pencil, Save, Search, Trash2, Upload, X } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AdminDocument, Filiere, Module } from "@/lib/types";

type DocumentCategory = "admin_document" | "timetable" | "news" | "event" | "other";
type VisibilityScope = "public" | "filiere" | "module";

const categoryLabels: Record<string, string> = {
  admin_document: "Administrative",
  timetable: "Timetable",
  news: "News",
  event: "Event",
  other: "Other",
};

export default function DocumentsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<DocumentCategory>("admin_document");
  const [visibilityScope, setVisibilityScope] = useState<VisibilityScope>("public");
  const [selectedFiliere, setSelectedFiliere] = useState("");
  const [selectedModule, setSelectedModule] = useState("");
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [modules, setModules] = useState<Module[]>([]);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [editingDocument, setEditingDocument] = useState<AdminDocument | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editCategory, setEditCategory] = useState<DocumentCategory>("admin_document");
  const [editVisibilityScope, setEditVisibilityScope] = useState<VisibilityScope>("public");
  const [editFiliere, setEditFiliere] = useState("");
  const [editModule, setEditModule] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "admin") router.push("/dashboard/chat");
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

  const loadDocuments = useCallback(async () => {
    if (user?.role !== "admin") return;
    setLoadingDocuments(true);
    try {
      setDocuments(await fetchApi<AdminDocument[]>("/documents"));
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingDocuments(false);
    }
  }, [user]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadDocuments();
  }, [loadDocuments]);

  const filteredDocuments = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return documents.filter((document) => {
      const matchesCategory = !categoryFilter || document.document_category === categoryFilter;
      const searchable = [document.title, document.description, document.storage_path, document.file_type]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesCategory && (!needle || searchable.includes(needle));
    });
  }, [documents, search, categoryFilter]);

  if (user?.role !== "admin") return null;

  const resetUploadForm = () => {
    setFile(null);
    setTitle("");
    setDescription("");
    setCategory("admin_document");
    setVisibilityScope("public");
    setSelectedFiliere("");
    setSelectedModule("");
  };

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

      await fetchApi("/documents/upload", { method: "POST", body: formData });
      resetUploadForm();
      setShowUpload(false);
      setMessage("Document uploaded. It will be available in chat after indexing finishes.");
      void loadDocuments();
    } catch {
      setMessage("Upload failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const openEdit = (document: AdminDocument) => {
    setEditingDocument(document);
    setEditTitle(document.title || "");
    setEditDescription(document.description || "");
    setEditCategory((document.document_category || "admin_document") as DocumentCategory);
    setEditVisibilityScope(document.visibility_scope || "public");
    setEditFiliere(document.filiere_id || "");
    setEditModule(document.module_id || "");
  };

  const handleEdit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!editingDocument || !editTitle.trim()) return;
    setSavingEdit(true);
    try {
      await fetchApi(`/documents/${editingDocument.source_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: editTitle.trim(),
          description: editDescription || null,
          document_category: editCategory,
          visibility_scope: editVisibilityScope,
          filiere_id: editVisibilityScope === "filiere" ? editFiliere : null,
          module_id: editVisibilityScope === "module" ? editModule : null,
        }),
      });
      setEditingDocument(null);
      setMessage("Document updated.");
      void loadDocuments();
    } catch (error) {
      console.error(error);
      setMessage("Document update failed.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async (document: AdminDocument) => {
    if (!confirm(`Delete "${document.title || "this document"}" from documents and vector search?`)) return;
    setDeletingId(document.source_id);
    try {
      await fetchApi(`/documents/${document.source_id}`, { method: "DELETE" });
      setDocuments((prev) => prev.filter((item) => item.source_id !== document.source_id));
      setMessage("Document deleted from storage index.");
    } catch (error) {
      console.error(error);
      setMessage("Document delete failed.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start xl:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text">Admin Documents</h1>
          <p className="text-text-muted mt-1">Manage indexed academic documents used by the assistant.</p>
        </div>

        <div className="flex gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:flex-initial">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-white focus:outline-none focus:border-primary transition-colors shadow-sm"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="border border-border rounded-lg bg-white px-3 py-2 shadow-sm text-sm focus:outline-none focus:border-primary"
          >
            <option value="">All Categories</option>
            {Object.entries(categoryLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <button onClick={() => setShowUpload(true)} className="btn-primary flex items-center gap-2 whitespace-nowrap shadow-sm bg-accent">
            <Upload size={18} /> Upload
          </button>
        </div>
      </div>

      {message && (
        <div className={`mb-5 rounded-lg border px-4 py-3 text-sm font-medium ${
          message.includes("failed") ? "border-danger/20 bg-danger/10 text-danger" : "border-emerald-200 bg-emerald-50 text-emerald-700"
        }`}>
          {message}
        </div>
      )}

      {loadingDocuments ? (
        <div className="flex justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : filteredDocuments.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-border text-center shadow-sm">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText size={32} className="text-slate-400" />
          </div>
          <h3 className="text-lg font-bold text-text mb-1">No documents found</h3>
          <p className="text-slate-500">Upload documents or change your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredDocuments.map((document) => (
            <div key={document.source_id} className="bg-white rounded-xl border border-border overflow-hidden hover:border-primary/40 hover:shadow-md transition-all group flex flex-col">
              <div className="px-5 pt-4 flex justify-end">
                <span className="px-2.5 py-1 rounded-md border text-xs font-semibold bg-primary-light text-primary border-primary/20">
                  {categoryLabels[document.document_category] || document.document_category}
                </span>
              </div>
              <div className="p-5 flex-1">
                <div className="w-12 h-12 bg-primary-light rounded-xl flex items-center justify-center mb-4 text-primary shadow-inner">
                  <FileText size={24} />
                </div>
                <h3 className="font-bold text-text text-lg leading-tight mb-1 line-clamp-2" title={document.title || ""}>
                  {document.title || "Untitled document"}
                </h3>
                <span className="inline-block px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-semibold rounded-md mb-3 border border-slate-200">
                  {document.accessibility || document.visibility_scope} - {document.chunk_count} chunks
                </span>
                <div className="text-xs text-slate-500 mb-3">
                  Uploaded by <span className="font-semibold text-slate-700">{document.uploader_name || document.uploaded_by || "Admin"}</span>
                </div>
                {(document.description || document.storage_path) && (
                  <p className="text-sm text-slate-500 line-clamp-3 my-2 bg-slate-50 p-3 rounded-lg border border-slate-100 italic">
                    {document.description || document.storage_path}
                  </p>
                )}
              </div>
              <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex justify-between items-center mt-auto">
                <div className="text-xs text-slate-500">
                  {document.created_at ? new Date(document.created_at).toLocaleDateString() : "-"}
                </div>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => openEdit(document)} className="text-slate-600 hover:text-primary bg-white p-2 rounded-md border border-slate-200 shadow-sm transition-colors" title="Edit">
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    disabled={deletingId === document.source_id}
                    onClick={() => void handleDelete(document)}
                    className="text-danger hover:bg-danger/10 bg-white p-2 rounded-md border border-slate-200 shadow-sm transition-colors disabled:opacity-50"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                  {document.file_url && (
                    <a href={document.file_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary-dark font-medium text-sm flex items-center gap-1 bg-white px-3 py-1.5 rounded-md border border-slate-200 shadow-sm transition-colors">
                      View <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showUpload && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl overflow-hidden border border-border/50">
            <div className="px-6 py-4 border-b border-border bg-slate-50 flex justify-between items-center">
              <h3 className="text-lg font-bold text-text flex items-center gap-2">
                <Upload size={20} className="text-primary" /> Upload Document
              </h3>
              <button onClick={() => setShowUpload(false)} className="text-slate-400 hover:text-text transition-colors p-1">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <InputFile onChange={(nextFile) => setFile(nextFile)} />
              <TextField label="Title" value={title} onChange={setTitle} placeholder="Defaults to filename" />
              <SelectField label="Category" value={category} onChange={(value) => setCategory(value as DocumentCategory)}>
                <option value="admin_document">Administrative document</option>
                <option value="timetable">Timetable</option>
                <option value="news">News</option>
                <option value="event">Event</option>
                <option value="other">Other</option>
              </SelectField>
              <TextAreaField label="Description" value={description} onChange={setDescription} placeholder="Short context for search results" />
              <AudienceFields
                visibilityScope={visibilityScope}
                onVisibilityScope={setVisibilityScope}
                selectedFiliere={selectedFiliere}
                onSelectedFiliere={setSelectedFiliere}
                selectedModule={selectedModule}
                onSelectedModule={setSelectedModule}
                filieres={filieres}
                modules={modules}
              />
              <div className="pt-4 flex justify-end gap-3 border-t border-border mt-6">
                <button type="button" className="btn-outline px-5" onClick={() => setShowUpload(false)}>Cancel</button>
                <button type="submit" disabled={!file || submitting} className="btn-primary px-6 flex items-center gap-2">
                  {submitting ? "Uploading..." : "Upload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingDocument && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl overflow-hidden border border-border/50">
            <div className="px-6 py-4 border-b border-border bg-slate-50 flex justify-between items-center">
              <h3 className="text-lg font-bold text-text flex items-center gap-2">
                <Pencil size={20} className="text-primary" /> Edit Document
              </h3>
              <button onClick={() => setEditingDocument(null)} className="text-slate-400 hover:text-text transition-colors p-1">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleEdit} className="p-6 space-y-4">
              <TextField label="Title" value={editTitle} onChange={setEditTitle} required />
              <SelectField label="Category" value={editCategory} onChange={(value) => setEditCategory(value as DocumentCategory)}>
                <option value="admin_document">Administrative document</option>
                <option value="timetable">Timetable</option>
                <option value="news">News</option>
                <option value="event">Event</option>
                <option value="other">Other</option>
              </SelectField>
              <TextAreaField label="Description" value={editDescription} onChange={setEditDescription} />
              <AudienceFields
                visibilityScope={editVisibilityScope}
                onVisibilityScope={setEditVisibilityScope}
                selectedFiliere={editFiliere}
                onSelectedFiliere={setEditFiliere}
                selectedModule={editModule}
                onSelectedModule={setEditModule}
                filieres={filieres}
                modules={modules}
              />
              <div className="pt-4 flex justify-end gap-3 border-t border-border mt-6">
                <button type="button" className="btn-outline px-5" onClick={() => setEditingDocument(null)}>Cancel</button>
                <button type="submit" disabled={savingEdit} className="btn-primary px-6 flex items-center gap-2">
                  <Save size={18} /> {savingEdit ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function InputFile({ onChange }: { onChange: (file: File | null) => void }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-muted mb-1">File</label>
      <input
        type="file"
        required
        onChange={(event) => onChange(event.target.files?.[0] || null)}
        className="w-full text-sm border border-border rounded-lg p-2 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-light file:text-primary hover:file:bg-primary hover:file:text-white transition-colors"
      />
    </div>
  );
}

function TextField({ label, value, onChange, placeholder, required = false }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; required?: boolean }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-muted mb-1">{label}</label>
      <input className="input-field" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required={required} />
    </div>
  );
}

function TextAreaField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-muted mb-1">{label}</label>
      <textarea className="input-field resize-none h-24" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </div>
  );
}

function SelectField({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-text-muted mb-1">{label}</label>
      <select className="input-field bg-white" value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </div>
  );
}

function AudienceFields({
  visibilityScope,
  onVisibilityScope,
  selectedFiliere,
  onSelectedFiliere,
  selectedModule,
  onSelectedModule,
  filieres,
  modules,
}: {
  visibilityScope: VisibilityScope;
  onVisibilityScope: (value: VisibilityScope) => void;
  selectedFiliere: string;
  onSelectedFiliere: (value: string) => void;
  selectedModule: string;
  onSelectedModule: (value: string) => void;
  filieres: Filiere[];
  modules: Module[];
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <SelectField label="Audience" value={visibilityScope} onChange={(value) => onVisibilityScope(value as VisibilityScope)}>
        <option value="public">Public</option>
        <option value="filiere">Specific filiere</option>
        <option value="module">Specific module</option>
      </SelectField>
      {visibilityScope === "filiere" && (
        <SelectField label="Filiere" value={selectedFiliere} onChange={onSelectedFiliere}>
          <option value="">Select filiere</option>
          {filieres.map((filiere) => (
            <option key={filiere.id} value={filiere.id}>{filiere.code} - {filiere.name}</option>
          ))}
        </SelectField>
      )}
      {visibilityScope === "module" && (
        <SelectField label="Module" value={selectedModule} onChange={onSelectedModule}>
          <option value="">Select module</option>
          {modules.map((module) => (
            <option key={module.id} value={module.id}>{module.code} - {module.name}</option>
          ))}
        </SelectField>
      )}
    </div>
  );
}
