/**
 * app/(dashboard)/documents/page.tsx
 * Document upload + list — admin only.
 */
"use client";

import { useRef, useState } from "react";
import { tokenStore } from "@/lib/auth";

export default function DocumentsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string>("");
  const [uploading, setUploading] = useState(false);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setUploading(true);
    setStatus("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "cours");

    const token = tokenStore.getAccess() ?? "";
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/documents/upload`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );
      const data = await res.json();
      setStatus(res.ok ? `✅ ${data.message}` : `❌ ${data.error}`);
    } catch {
      setStatus("❌ Erreur réseau");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0f0f1a] text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">
          📄 <span className="text-[#00B894]">Documents</span>
        </h1>

        <div className="rounded-2xl border border-dashed border-white/20 bg-white/5 p-8 text-center">
          <p className="text-white/50 mb-4 text-sm">
            Glissez un PDF ou cliquez pour sélectionner
          </p>
          <input
            ref={fileRef}
            id="doc-file-input"
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleUpload}
          />
          <button
            id="doc-upload-btn"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="rounded-lg bg-[#00B894] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#00a383] disabled:opacity-50 transition-colors"
          >
            {uploading ? "Envoi en cours…" : "Choisir un PDF"}
          </button>
          {status && (
            <p className="mt-4 text-sm text-white/70">{status}</p>
          )}
        </div>
      </div>
    </main>
  );
}
