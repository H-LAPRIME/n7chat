"use client";

import { useEffect, useState } from "react";
import { Event } from "@/lib/types";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Calendar as CalendarIcon, MapPin, Plus, Clock, X, Bell } from "lucide-react";
import { useRouter } from "next/navigation";

export default function EventsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [eventType, setEventType] = useState<"exam" | "conference" | "holiday" | "meeting">("exam");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [location, setLocation] = useState("");
  const [notify, setNotify] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user && user.role !== "teacher" && user.role !== "admin") {
      router.push("/dashboard/chat");
      return;
    }
    fetchEvents();
  }, [user, router]);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const data = await fetchApi("/events?upcoming_only=false");
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openModal = (ev?: Event) => {
    if (ev) {
      setEditingId(ev.id);
      setTitle(ev.title);
      setDescription(ev.description || "");
      setEventType(ev.event_type);
      setStartDate(new Date(ev.start_date).toISOString().slice(0, 16));
      setEndDate(ev.end_date ? new Date(ev.end_date).toISOString().slice(0, 16) : "");
      setLocation(ev.location || "");
      setNotify(false);
    } else {
      setEditingId(null);
      setTitle("");
      setDescription("");
      setEventType("exam");
      setStartDate("");
      setEndDate("");
      setLocation("");
      setNotify(true);
    }
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    
    try {
      const payload = {
        title,
        description: description || null,
        event_type: eventType,
        start_date: new Date(startDate).toISOString(),
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        location: location || null,
        notify_students: notify,
      };

      if (editingId) {
        await fetchApi(`/events/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await fetchApi("/events", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      
      setShowModal(false);
      fetchEvents();
    } catch (e) {
      alert("Failed to save event");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this event?")) return;
    try {
      await fetchApi(`/events/${id}`, { method: "DELETE" });
      fetchEvents();
    } catch (e) {
      alert("Failed to delete event");
    }
  };

  const getTypeColor = (type: string) => {
    switch(type) {
      case "exam": return "bg-danger/10 text-danger border-danger/20";
      case "conference": return "bg-primary-light text-primary border-primary/20";
      case "holiday": return "bg-emerald-100 text-emerald-700 border-emerald-200";
      case "meeting": return "bg-amber-100 text-amber-700 border-amber-200";
      default: return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text">Events Management</h1>
          <p className="text-text-muted mt-1">Schedule and manage upcoming academic events.</p>
        </div>
        <button 
          onClick={() => openModal()}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} /> New Event
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : events.length === 0 ? (
         <div className="bg-white p-12 rounded-2xl border border-border text-center shadow-sm">
           <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
             <CalendarIcon size={32} className="text-slate-400" />
           </div>
           <h3 className="text-lg font-bold text-text mb-1">No events scheduled</h3>
           <p className="text-slate-500">Create an event to notify students.</p>
         </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {events.map(ev => (
            <div key={ev.id} className="bg-white p-5 rounded-xl border border-border shadow-sm flex flex-col">
              <div className="flex justify-between items-start mb-3">
                <span className={`px-2.5 py-1 text-xs font-bold uppercase rounded border ${getTypeColor(ev.event_type)}`}>
                  {ev.event_type}
                </span>
                <div className="flex gap-2">
                  <button onClick={() => openModal(ev)} className="text-sm font-medium text-accent hover:underline">Edit</button>
                  <button onClick={() => handleDelete(ev.id)} className="text-sm font-medium text-danger hover:underline">Delete</button>
                </div>
              </div>
              
              <h3 className="text-xl font-bold text-text mb-2">{ev.title}</h3>
              {ev.description && <p className="text-sm text-slate-500 mb-4 flex-1">{ev.description}</p>}
              
              <div className="mt-auto pt-4 space-y-2 border-t border-slate-100">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Clock size={16} className="text-slate-400" />
                  <span>{new Date(ev.start_date).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</span>
                </div>
                {ev.location && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <MapPin size={16} className="text-slate-400" />
                    <span>{ev.location}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Form */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden border border-border/50 max-h-[90vh] flex flex-col">
            <div className="px-6 py-4 border-b border-border bg-slate-50 flex justify-between items-center shrink-0">
              <h3 className="text-lg font-bold text-text">
                {editingId ? "Edit Event" : "Create New Event"}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-text">
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
              <div>
                <label className="block text-sm font-semibold text-text-muted mb-1">Event Title</label>
                <input required type="text" className="input-field" value={title} onChange={e => setTitle(e.target.value)} />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-text-muted mb-1">Type</label>
                  <select className="input-field bg-white" value={eventType} onChange={(e: any) => setEventType(e.target.value)}>
                    <option value="exam">Exam</option>
                    <option value="conference">Conference</option>
                    <option value="meeting">Meeting</option>
                    <option value="holiday">Holiday</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-text-muted mb-1">Location (Optional)</label>
                  <input type="text" className="input-field" value={location} onChange={e => setLocation(e.target.value)} />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-text-muted mb-1">Start Date & Time</label>
                  <input required type="datetime-local" className="input-field" value={startDate} onChange={e => setStartDate(e.target.value)} />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-text-muted mb-1">End Date & Time (Optional)</label>
                  <input type="datetime-local" className="input-field" value={endDate} onChange={e => setEndDate(e.target.value)} />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-text-muted mb-1">Description (Optional)</label>
                <textarea className="input-field resize-none h-24" value={description} onChange={e => setDescription(e.target.value)} />
              </div>
              
              {!editingId && (
                <label className="flex items-center gap-2 p-3 bg-primary-light/50 border border-primary/20 rounded-lg cursor-pointer">
                  <input type="checkbox" checked={notify} onChange={e => setNotify(e.target.checked)} className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium text-primary-dark flex items-center gap-1">
                    <Bell size={14} /> Send notification alert to students
                  </span>
                </label>
              )}
              
              <div className="pt-4 flex justify-end gap-3 border-t border-border mt-6">
                <button type="button" className="btn-outline px-5" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" disabled={submitting} className="btn-primary px-6">
                  {submitting ? "Saving..." : "Save Event"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
