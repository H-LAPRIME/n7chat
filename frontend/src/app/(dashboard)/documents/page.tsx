/**
 * app/(dashboard)/documents/page.tsx
 * Document management page — admins can upload PDFs. Light academic theme.
 */
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tokenStore, getUserRole } from "@/lib/auth";
import { 
  Upload, 
  FileText, 
  Search, 
  Plus, 
  Trash2, 
  ExternalLink, 
  Loader2,
  AlertCircle
} from "lucide-react";

type Doc = { id: string; filename: string; created_at: string };

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [role, setRole] = useState<"student" | "admin">("student");
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const token = tokenStore.getAccess() ?? "";
    setRole(getUserRole(token) ?? "student");
    refreshDocs(token);
  }, []);

  async function refreshDocs(token: string) {
    try {
      const res = await api.documents.list(token);
      setDocs(res.documents as Doc[]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!file) return;
    const token = tokenStore.getAccess() ?? "";
    setUploading(true);
    setStatus("Téléchargement...");
    try {
      await api.documents.upload(file, token);
      setStatus("Document ajouté avec succès !");
      setFile(null);
      refreshDocs(token);
    } catch (e) {
      setStatus("Erreur lors de l'envoi");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-8 bg-white h-full text-slate-900">
      <div className="max-w-5xl mx-auto">
        <header className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-serif font-bold text-slate-900 mb-2">Gestion des Documents</h1>
            <p className="text-slate-500">Consultez et gérez les ressources documentaires de l&apos;école.</p>
          </div>
        </header>

        {role === "admin" && (
          <div className="mb-12 p-8 rounded-3xl bg-slate-50 border border-slate-200 shadow-sm">
            <h2 className="text-lg font-serif font-bold mb-4 flex items-center gap-2">
              <Upload className="text-brand" size={20} /> Ajouter un nouveau document
            </h2>
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <label className="flex-1 w-full group cursor-pointer">
                <div className="flex items-center gap-3 p-4 rounded-xl border-2 border-dashed border-slate-200 bg-white group-hover:border-brand/40 transition-all">
                  <div className="p-2 rounded-lg bg-slate-100 text-slate-400 group-hover:text-brand transition-colors">
                    <Plus size={20} />
                  </div>
                  <span className="text-sm font-medium text-slate-500 truncate">
                    {file ? file.name : "Cliquez pour sélectionner un PDF..."}
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf"
                    onChange={(e) => {
                      setFile(e.target.files?.[0] || null);
                      setStatus("");
                    }}
                  />
                </div>
              </label>
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="w-full sm:w-auto rounded-xl bg-brand px-8 py-4 text-sm font-bold text-white shadow-lg shadow-brand/20 hover:bg-brand-hover disabled:opacity-40 transition-all active:scale-95 flex items-center justify-center gap-2"
              >
                {uploading ? <Loader2 size={18} className="animate-spin" /> : null}
                {uploading ? "Envoi..." : "Uploader"}
              </button>
            </div>
            {status && (
              <p className={`mt-4 text-xs font-bold uppercase tracking-widest flex items-center gap-2 ${status.includes("succès") ? "text-green-600" : "text-brand"}`}>
                <AlertCircle size={14} /> {status}
              </p>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 mb-6 p-3 rounded-xl bg-slate-100 border border-slate-200">
          <Search className="text-slate-400" size={18} />
          <input 
            type="text" 
            placeholder="Rechercher un document..." 
            className="bg-transparent border-none outline-none text-sm w-full placeholder-slate-400"
          />
        </div>

        <h2 className="text-xl font-serif font-bold mb-6 flex items-center gap-2">
          <FileText size={24} className="text-brand" /> Ressources Disponibles
        </h2>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 opacity-40">
            <Loader2 className="animate-spin text-brand mb-4" size={40} />
            <p className="font-medium">Chargement des documents...</p>
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-20 bg-slate-50 rounded-3xl border border-dashed border-slate-200">
            <p className="text-slate-400 font-medium italic">Aucun document trouvé.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {docs.map((d) => (
              <div
                key={d.id}
                className="group flex items-center gap-4 p-5 rounded-2xl border border-slate-200 bg-white hover:shadow-lg hover:border-brand/20 transition-all duration-300"
              >
                <div className="p-3 rounded-xl bg-red-50 text-brand group-hover:scale-110 transition-transform">
                  <FileText size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-bold text-slate-900 truncate group-hover:text-brand transition-colors">
                    {d.filename}
                  </h3>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">
                    Uploadé le {new Date(d.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 rounded-lg text-slate-400 hover:text-brand hover:bg-red-50 transition-all" title="Ouvrir">
                    <ExternalLink size={18} />
                  </button>
                  {role === "admin" && (
                    <button className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-all" title="Supprimer">
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
