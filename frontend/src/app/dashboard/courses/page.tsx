"use client";

import { useCallback, useEffect, useState } from "react";
import { Course, Module } from "@/lib/types";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BookOpen, FileText, Upload, ExternalLink, Search, X } from "lucide-react";

export default function CoursesPage() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedModule, setSelectedModule] = useState("");
  
  // Upload modal state
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDesc, setUploadDesc] = useState("");
  const [uploadModule, setUploadModule] = useState("");
  const [uploading, setUploading] = useState(false);

  const fetchCourses = useCallback(async () => {
    try {
      setLoading(true);
      let query = `?limit=50`;
      if (search) query += `&search=${encodeURIComponent(search)}`;
      if (selectedModule) query += `&module_id=${selectedModule}`;
      
      const data = await fetchApi<Course[]>(`/courses${query}`);
      setCourses(data);
      
      if (user?.role === "teacher" || user?.role === "admin") {
        const mods = await fetchApi<Module[]>("/courses/modules");
        setModules(mods);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [search, selectedModule, user]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchCourses();
  }, [fetchCourses]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    if (!uploadModule) {
      alert("Please select a module before uploading course material.");
      return;
    }
    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (uploadTitle) formData.append("title", uploadTitle);
      if (uploadDesc) formData.append("description", uploadDesc);
      formData.append("module_id", uploadModule);

      await fetchApi("/courses/upload", {
        method: "POST",
        body: formData,
      });
      
      setShowUpload(false);
      setFile(null);
      setUploadTitle("");
      setUploadDesc("");
      fetchCourses();
    } catch (e) {
      console.error("Upload failed", e);
      alert("Failed to upload course material");
    } finally {
      setUploading(false);
    }
  };

  const getFileIcon = () => {
    return <FileText size={24} className="text-primary" />;
  };

  const getIndexStatus = (status?: string) => {
    switch (status) {
      case "indexed":
        return { label: "Ready for chat", className: "bg-emerald-50 text-emerald-700 border-emerald-200" };
      case "failed":
        return { label: "Index failed", className: "bg-danger/10 text-danger border-danger/20" };
      default:
        return { label: "Indexing", className: "bg-amber-50 text-amber-700 border-amber-200" };
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start xl:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text">Course Materials</h1>
          <p className="text-text-muted mt-1">Access logic, lectures, and resources for your modules.</p>
        </div>
        
        <div className="flex gap-3 w-full sm:w-auto">
          {/* Filtering */}
          <div className="relative flex-1 sm:flex-initial">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
             <input 
               type="text" 
               placeholder="Search..." 
               value={search}
               onChange={(e) => setSearch(e.target.value)}
               className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-white focus:outline-none focus:border-primary transition-colors shadow-sm"
             />
          </div>
          
          {(user?.role === "teacher" || user?.role === "admin") && (
            <>
              <select 
                value={selectedModule} 
                onChange={(e) => setSelectedModule(e.target.value)}
                className="border border-border rounded-lg bg-white px-3 py-2 shadow-sm text-sm focus:outline-none focus:border-primary"
              >
                <option value="">All Modules</option>
                {modules.map(m => (
                  <option key={m.id} value={m.id}>{m.code} - {m.name}</option>
                ))}
              </select>
              
              <button 
                onClick={() => setShowUpload(true)}
                className="btn-primary flex items-center gap-2 whitespace-nowrap shadow-sm bg-accent"
              >
                <Upload size={18} /> Upload
              </button>
            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : courses.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-border text-center shadow-sm">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <BookOpen size={32} className="text-slate-400" />
          </div>
          <h3 className="text-lg font-bold text-text mb-1">No materials found</h3>
          <p className="text-slate-500">There are no course materials available matching your criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {courses.map(course => (
            <div key={course.id} className="bg-white rounded-xl border border-border overflow-hidden hover:border-primary/40 hover:shadow-md transition-all group flex flex-col">
              {(() => {
                const status = getIndexStatus(course.index_status);
                return (
                  <div className="px-5 pt-4 flex justify-end">
                    <span className={`px-2.5 py-1 rounded-md border text-xs font-semibold ${status.className}`}>
                      {status.label}
                    </span>
                  </div>
                );
              })()}
              <div className="p-5 flex-1 relative">
                <div className="w-12 h-12 bg-primary-light rounded-xl flex items-center justify-center mb-4 text-primary shadow-inner">
                  {getFileIcon()}
                </div>
                
                <h3 className="font-bold text-text text-lg leading-tight mb-1 line-clamp-2" title={course.title}>
                  {course.title}
                </h3>
                
                {course.module_name && (
                  <span className="inline-block px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-semibold rounded-md mb-3 border border-slate-200">
                     {course.module_name}
                  </span>
                )}
                
                {course.description && (
                  <p className="text-sm text-slate-500 line-clamp-3 my-2 bg-slate-50 p-3 rounded-lg border border-slate-100 italic">
                    {course.description}
                  </p>
                )}
              </div>
              
              <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex justify-between items-center mt-auto">
                 <div className="text-xs text-slate-500">
                    {new Date(course.created_at).toLocaleDateString()}
                 </div>
                 <a 
                   href={course.file_url} 
                   target="_blank" 
                   rel="noopener noreferrer"
                   className="text-primary hover:text-primary-dark font-medium text-sm flex items-center gap-1 bg-white px-3 py-1.5 rounded-md border border-slate-200 shadow-sm transition-colors"
                 >
                   View <ExternalLink size={14} />
                 </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl overflow-hidden border border-border/50">
            <div className="px-6 py-4 border-b border-border bg-slate-50 flex justify-between items-center">
              <h3 className="text-lg font-bold text-text flex items-center gap-2">
                <Upload size={20} className="text-primary" /> Upload Material
              </h3>
              <button 
                onClick={() => setShowUpload(false)}
                className="text-slate-400 hover:text-text transition-colors p-1"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleUpload} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-text-muted mb-1">File</label>
                <input 
                  type="file" 
                  required
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-sm border border-border rounded-lg p-2 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-light file:text-primary hover:file:bg-primary hover:file:text-white transition-colors"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text-muted mb-1">Title (Optional)</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="Defaults to filename"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-text-muted mb-1">Module</label>
                <select 
                  className="input-field bg-white"
                  value={uploadModule}
                  onChange={(e) => setUploadModule(e.target.value)}
                >
                  <option value="">Select a module</option>
                  {modules.map(m => (
                    <option key={m.id} value={m.id}>{m.code} - {m.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text-muted mb-1">Description</label>
                <textarea 
                  className="input-field resize-none h-24" 
                  value={uploadDesc}
                  onChange={(e) => setUploadDesc(e.target.value)}
                  placeholder="Brief description of the material..."
                />
              </div>
              
              <div className="pt-4 flex justify-end gap-3 border-t border-border mt-6">
                <button 
                  type="button" 
                  className="btn-outline px-5"
                  onClick={() => setShowUpload(false)}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={!file || uploading}
                  className="btn-primary px-6 flex items-center gap-2"
                >
                  {uploading ? "Uploading..." : "Upload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

