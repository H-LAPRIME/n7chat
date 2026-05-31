"use client";
/* eslint-disable @next/next/no-img-element */

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { fetchApi } from "@/lib/api";
import { User } from "@/lib/types";
import { User as UserIcon, Camera, Save, Mail, Briefcase, Phone, MapPin, Loader2, BookOpen, GraduationCap } from "lucide-react";

type ProfilePhotoUploadResponse = {
  ok: boolean;
  profile: User;
};

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const canEditProfile = user?.role === "student" || user?.role === "teacher";
  const [phone, setPhone] = useState(user?.phone || "");
  const [address, setAddress] = useState(user?.address || "");
  const [office, setOffice] = useState(user?.office || "");
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void fetchApi<User>("/profile/me")
      .then((profile) => setUser(profile))
      .catch(() => undefined);
  }, [setUser]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPhone(user?.phone || "");
    setAddress(user?.address || "");
    setOffice(user?.office || "");
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEditProfile) {
      setMessage("This account type has no editable profile fields.");
      return;
    }
    setSaving(true);
    setMessage("");
    
    try {
      const payload: { phone: string | null; address?: string | null; office?: string | null } = {
        phone: phone || null,
      };
      if (user?.role === "student") payload.address = address || null;
      if (user?.role === "teacher") payload.office = office || null;

      const updated = await fetchApi<User>("/profile/me", {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      
      setUser(updated);
      setMessage("Profile updated successfully");
      setTimeout(() => setMessage(""), 3000);
    } catch {
      setMessage("Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handlePhotoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setMessage("Please select an image file");
      event.target.value = "";
      return;
    }

    setUploadingPhoto(true);
    setMessage("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await fetchApi<ProfilePhotoUploadResponse>("/profile/photo", {
        method: "POST",
        body: formData,
      });
      setUser(result.profile);
      setMessage("Profile photo updated successfully");
      setTimeout(() => setMessage(""), 3000);
    } catch {
      setMessage("Failed to upload profile photo");
    } finally {
      setUploadingPhoto(false);
      event.target.value = "";
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-text mb-8">Account Profile</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Col: Avatar & Immutable details */}
        <div className="col-span-1">
          <div className="bg-white p-6 rounded-2xl border border-border shadow-sm flex flex-col items-center text-center">
            <div className="relative group mb-4">
              <div className="w-32 h-32 bg-primary-light rounded-full border-4 border-white shadow-md flex items-center justify-center overflow-hidden">
                {user?.photo_url ? (
                  <img
                    src={user.photo_url}
                    alt="Profile photo"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <UserIcon size={48} className="text-primary opacity-80" />
                )}
              </div>
              {canEditProfile && (
                <>
                  <input
                    id="profile-photo-input"
                    type="file"
                    accept="image/*"
                    className="sr-only"
                    disabled={uploadingPhoto}
                    onChange={handlePhotoUpload}
                  />
                  <label
                    htmlFor="profile-photo-input"
                    className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                    title="Upload profile photo"
                  >
                    {uploadingPhoto ? (
                      <Loader2 className="text-white animate-spin" size={24} />
                    ) : (
                      <Camera className="text-white" size={24} />
                    )}
                  </label>
                </>
              )}
            </div>
            
            <h2 className="text-xl font-bold text-text mb-1">
              {user?.first_name} {user?.last_name}
            </h2>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 border border-slate-200 rounded-full text-xs font-semibold text-slate-600 uppercase tracking-wide mb-4">
              <Briefcase size={12} /> {user?.role}
            </div>
            
            <div className="w-full pt-4 border-t border-slate-100 flex items-center gap-3 text-sm text-slate-600 justify-center">
               <Mail size={16} className="text-slate-400" />
               <span className="truncate">{user?.email}</span>
            </div>
            {user?.role === "student" && user.filiere_name && (
              <div className="w-full mt-4 pt-4 border-t border-slate-100 text-sm text-slate-600 space-y-2">
                <div className="flex items-center justify-center gap-2">
                  <GraduationCap size={16} className="text-slate-400" />
                  <span className="font-semibold">{user.filiere_code} - {user.filiere_name}</span>
                </div>
                {user.level_name && <div>{user.level_name}</div>}
              </div>
            )}
            {user?.role === "teacher" && (
              <div className="w-full mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                  <div className="text-lg font-bold text-text">{user.assigned_module_count || 0}</div>
                  <div className="text-xs text-slate-500">Modules</div>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                  <div className="text-lg font-bold text-text">{user.assigned_filiere_count || 0}</div>
                  <div className="text-xs text-slate-500">Classes</div>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Right Col: Editable Form */}
        <div className="col-span-1 md:col-span-2">
          <div className="bg-white p-8 rounded-2xl border border-border shadow-sm">
            <h3 className="text-xl font-bold text-text mb-6">Personal Information</h3>
            
            {canEditProfile ? (
            <form onSubmit={handleSave} className="space-y-6">
              
              <div className="space-y-4">
                <div>
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-1.5">
                    <Phone size={16} className="text-slate-400" /> Phone Number
                  </label>
                  <input 
                    type="tel" 
                    className="input-field" 
                    placeholder="+1 234 567 8900"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
                
                {user?.role === "student" && (
                  <div>
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-1.5">
                      <MapPin size={16} className="text-slate-400" /> Address
                    </label>
                    <textarea 
                      className="input-field resize-none h-20" 
                      placeholder="Your delivery or physical address"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                    />
                  </div>
                )}
                
                {user?.role === "teacher" && (
                  <div>
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-1.5">
                      <Briefcase size={16} className="text-slate-400" /> Office Location
                    </label>
                    <input 
                      type="text" 
                      className="input-field" 
                      placeholder="e.g. Building A, Room 302"
                      value={office}
                      onChange={(e) => setOffice(e.target.value)}
                    />
                  </div>
                )}
              </div>
              
              <div className="pt-6 border-t border-slate-100 flex items-center justify-between">
                <div>
                  {message && (
                    <span className={`text-sm font-medium ${message.includes("success") ? "text-emerald-600" : "text-danger"}`}>
                      {message}
                    </span>
                  )}
                </div>
                <button 
                  type="submit" 
                  disabled={saving}
                  className="btn-primary px-6 flex items-center gap-2"
                >
                  <Save size={18} /> {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
            ) : (
              <div className="rounded-xl border border-border bg-surface-2 p-5">
                <p className="text-sm text-text-muted">
                  Admin accounts do not have student or teacher profile fields to edit here.
                </p>
              </div>
            )}
          </div>

          {(user?.role === "student" || user?.role === "teacher") && (
            <div className="bg-white p-8 rounded-2xl border border-border shadow-sm mt-6">
              <h3 className="text-xl font-bold text-text mb-5 flex items-center gap-2">
                <BookOpen size={20} className="text-primary" /> Assignments
              </h3>
              {user?.role === "teacher" && user.assigned_filieres && user.assigned_filieres.length > 0 && (
                <div className="mb-5 flex flex-wrap gap-2">
                  {user.assigned_filieres.map((filiere) => (
                    <span key={filiere.id} className="px-3 py-1 rounded-md bg-primary-light text-primary text-xs font-semibold border border-primary/10">
                      {filiere.code} - {filiere.name}
                    </span>
                  ))}
                </div>
              )}
              <div className="divide-y divide-slate-100 border border-slate-100 rounded-xl overflow-hidden">
                {(user?.assigned_modules || []).length === 0 ? (
                  <div className="p-4 text-sm text-text-muted">No assigned modules found.</div>
                ) : (
                  (user?.assigned_modules || []).map((module) => {
                    const teacher = [module.teacher_first_name, module.teacher_last_name].filter(Boolean).join(" ");
                    return (
                      <div key={module.id} className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div>
                          <div className="font-semibold text-text">{module.code} - {module.name}</div>
                          <div className="text-xs text-text-muted">
                            {module.filiere_name || teacher || "Assigned"}
                          </div>
                        </div>
                        {module.semester && (
                          <span className="text-xs font-semibold text-slate-600 bg-slate-100 border border-slate-200 rounded-md px-2.5 py-1 w-fit">
                            Semester {module.semester}
                          </span>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
