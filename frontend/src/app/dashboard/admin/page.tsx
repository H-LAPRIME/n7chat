"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  Building2,
  GraduationCap,
  Layers,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  UserCog,
  Users,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

type Role = "student" | "teacher" | "admin";
type StudentStatus = "active" | "suspended" | "graduated";
type AdminTab = "people" | "students" | "teachers" | "academics";

interface AdminOverview {
  users: number;
  students: number;
  teachers: number;
  departments: number;
  filieres: number;
  modules: number;
}

interface AdminUser {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at?: string;
}

interface Department {
  id: string;
  name: string;
  description?: string | null;
}

interface Level {
  id: string;
  name: string;
  order_number: number;
}

interface Filiere {
  id: string;
  department_id?: string | null;
  department_name?: string | null;
  name: string;
  code: string;
  duration_years?: number | null;
}

interface Teacher {
  id: string;
  user_id: string;
  email: string;
  teacher_code: string;
  first_name: string;
  last_name: string;
  specialization?: string | null;
  department_id?: string | null;
  department_name?: string | null;
}

interface Student {
  id: string;
  user_id: string;
  email: string;
  student_code: string;
  first_name: string;
  last_name: string;
  filiere_id?: string | null;
  filiere_name?: string | null;
  level_id?: string | null;
  level_name?: string | null;
  status: StudentStatus;
}

interface AdminModule {
  id: string;
  filiere_id: string;
  filiere_name?: string | null;
  teacher_id?: string | null;
  teacher_first_name?: string | null;
  teacher_last_name?: string | null;
  name: string;
  code: string;
  semester?: number | null;
}

const emptyUser = { email: "", password: "", role: "student" as Role, is_active: true };
const emptyStudent = { user_id: "", student_code: "", first_name: "", last_name: "", filiere_id: "", level_id: "", status: "active" as StudentStatus };
const emptyTeacher = { user_id: "", teacher_code: "", first_name: "", last_name: "", specialization: "", department_id: "" };
const emptyDepartment = { name: "", description: "" };
const emptyFiliere = { department_id: "", name: "", code: "", duration_years: "" };
const emptyLevel = { name: "", order_number: "" };
const emptyModule = { filiere_id: "", teacher_id: "", name: "", code: "", semester: "" };

export default function AdminPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<AdminTab>("people");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [modules, setModules] = useState<AdminModule[]>([]);

  const [userForm, setUserForm] = useState(emptyUser);
  const [studentForm, setStudentForm] = useState(emptyStudent);
  const [teacherForm, setTeacherForm] = useState(emptyTeacher);
  const [departmentForm, setDepartmentForm] = useState(emptyDepartment);
  const [filiereForm, setFiliereForm] = useState(emptyFiliere);
  const [levelForm, setLevelForm] = useState(emptyLevel);
  const [moduleForm, setModuleForm] = useState(emptyModule);
  const [studentAssignment, setStudentAssignment] = useState({ student_id: "", filiere_id: "", level_id: "", status: "" });
  const [moduleAssignment, setModuleAssignment] = useState({ module_id: "", teacher_id: "" });

  const teacherUsers = useMemo(() => users.filter((item) => item.role === "teacher"), [users]);
  const studentUsers = useMemo(() => users.filter((item) => item.role === "student"), [users]);

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const [overviewData, userData, departmentData, levelData, filiereData, teacherData, studentData, moduleData] = await Promise.all([
        fetchApi<AdminOverview>("/admin/overview"),
        fetchApi<AdminUser[]>("/admin/users"),
        fetchApi<Department[]>("/admin/departments"),
        fetchApi<Level[]>("/admin/levels"),
        fetchApi<Filiere[]>("/admin/filieres"),
        fetchApi<Teacher[]>("/admin/teachers"),
        fetchApi<Student[]>("/admin/students"),
        fetchApi<AdminModule[]>("/admin/modules"),
      ]);
      setOverview(overviewData);
      setUsers(userData);
      setDepartments(departmentData);
      setLevels(levelData);
      setFilieres(filiereData);
      setTeachers(teacherData);
      setStudents(studentData);
      setModules(moduleData);
    } catch (error) {
      console.error(error);
      setMessage("Impossible de charger les donnees admin.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role !== "admin") {
      router.push("/dashboard/chat");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadAdminData();
  }, [loadAdminData, router, user]);

  if (user?.role !== "admin") return null;

  async function submitJson(endpoint: string, method: "POST" | "PATCH", body: unknown, success: string) {
    setMessage("");
    try {
      await fetchApi(endpoint, { method, body: JSON.stringify(body) });
      setMessage(success);
      await loadAdminData();
    } catch (error) {
      console.error(error);
      setMessage(error instanceof Error ? error.message : "Action echouee.");
    }
  }

  async function handleDelete(table: string, id: string) {
    if (!confirm("Supprimer cet element ?")) return;
    setMessage("");
    try {
      await fetchApi(`/admin/${table}/${id}`, { method: "DELETE" });
      setMessage("Element supprime.");
      await loadAdminData();
    } catch (error) {
      console.error(error);
      setMessage(error instanceof Error ? error.message : "Suppression echouee.");
    }
  }

  const stats = [
    { label: "Utilisateurs", value: overview?.users ?? 0, icon: Users },
    { label: "Etudiants", value: overview?.students ?? 0, icon: GraduationCap },
    { label: "Professeurs", value: overview?.teachers ?? 0, icon: UserCog },
    { label: "Filieres", value: overview?.filieres ?? 0, icon: Layers },
    { label: "Modules", value: overview?.modules ?? 0, icon: BookOpen },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Administration</h1>
          <p className="text-text-muted mt-1">Gerer les comptes, professeurs, etudiants, filieres et affectations.</p>
        </div>
        <button onClick={() => void loadAdminData()} className="btn-outline flex items-center gap-2 w-fit">
          <RefreshCw size={18} /> Actualiser
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white border border-border rounded-lg p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-text-muted">{stat.label}</p>
                <Icon size={19} className="text-primary" />
              </div>
              <p className="text-3xl font-bold text-text mt-3">{stat.value}</p>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2 border-b border-border">
        {[
          { id: "people", label: "Comptes" },
          { id: "students", label: "Etudiants" },
          { id: "teachers", label: "Professeurs" },
          { id: "academics", label: "Filieres & modules" },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id as AdminTab)}
            className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
              tab === item.id ? "border-primary text-primary" : "border-transparent text-text-muted hover:text-text"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {message && (
        <div className={`border rounded-lg px-4 py-3 text-sm ${message.includes("echou") || message.includes("Impossible") ? "bg-danger/10 border-danger/20 text-danger" : "bg-emerald-50 border-emerald-200 text-emerald-700"}`}>
          {message}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : (
        <>
          {tab === "people" && (
            <section className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
              <Panel title="Nouveau compte" icon={ShieldCheck}>
                <form
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void submitJson("/admin/users", "POST", userForm, "Compte cree.").then(() => setUserForm(emptyUser));
                  }}
                >
                  <Input label="Email" type="email" value={userForm.email} onChange={(value) => setUserForm({ ...userForm, email: value })} required />
                  <Input label="Mot de passe" type="password" value={userForm.password} onChange={(value) => setUserForm({ ...userForm, password: value })} required />
                  <Select label="Role" value={userForm.role} onChange={(value) => setUserForm({ ...userForm, role: value as Role })}>
                    <option value="student">Etudiant</option>
                    <option value="teacher">Professeur</option>
                    <option value="admin">Admin</option>
                  </Select>
                  <button className="btn-primary flex items-center gap-2 w-full justify-center">
                    <Plus size={18} /> Creer le compte
                  </button>
                </form>
              </Panel>
              <Panel title="Comptes existants" icon={Users}>
                <DataTable
                  headers={["Email", "Role", "Etat", ""]}
                  rows={users.map((item) => [
                    item.email,
                    item.role,
                    item.is_active ? "Actif" : "Inactif",
                    <button key={item.id} onClick={() => void handleDelete("users", item.id)} className="text-danger hover:bg-danger/10 p-2 rounded-md" title="Supprimer">
                      <Trash2 size={16} />
                    </button>,
                  ])}
                />
              </Panel>
            </section>
          )}

          {tab === "students" && (
            <section className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
              <div className="space-y-6">
                <Panel title="Profil etudiant" icon={GraduationCap}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const payload = { ...studentForm, filiere_id: studentForm.filiere_id || null, level_id: studentForm.level_id || null };
                      void submitJson("/admin/students", "POST", payload, "Etudiant cree.").then(() => setStudentForm(emptyStudent));
                    }}
                  >
                    <Select label="Compte etudiant" value={studentForm.user_id} onChange={(value) => setStudentForm({ ...studentForm, user_id: value })} required>
                      <option value="">Selectionner</option>
                      {studentUsers.map((item) => <option key={item.id} value={item.id}>{item.email}</option>)}
                    </Select>
                    <Input label="Code etudiant" value={studentForm.student_code} onChange={(value) => setStudentForm({ ...studentForm, student_code: value })} required />
                    <div className="grid grid-cols-2 gap-3">
                      <Input label="Prenom" value={studentForm.first_name} onChange={(value) => setStudentForm({ ...studentForm, first_name: value })} required />
                      <Input label="Nom" value={studentForm.last_name} onChange={(value) => setStudentForm({ ...studentForm, last_name: value })} required />
                    </div>
                    <AcademicSelects
                      filieres={filieres}
                      levels={levels}
                      filiereValue={studentForm.filiere_id}
                      levelValue={studentForm.level_id}
                      onFiliere={(value) => setStudentForm({ ...studentForm, filiere_id: value })}
                      onLevel={(value) => setStudentForm({ ...studentForm, level_id: value })}
                    />
                    <button className="btn-primary flex items-center gap-2 w-full justify-center">
                      <Plus size={18} /> Ajouter
                    </button>
                  </form>
                </Panel>
                <Panel title="Affecter etudiant" icon={Save}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const payload = {
                        filiere_id: studentAssignment.filiere_id || null,
                        level_id: studentAssignment.level_id || null,
                        status: studentAssignment.status || undefined,
                      };
                      void submitJson(`/admin/students/${studentAssignment.student_id}/assignment`, "PATCH", payload, "Affectation etudiant mise a jour.");
                    }}
                  >
                    <Select label="Etudiant" value={studentAssignment.student_id} onChange={(value) => setStudentAssignment({ ...studentAssignment, student_id: value })} required>
                      <option value="">Selectionner</option>
                      {students.map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name}</option>)}
                    </Select>
                    <AcademicSelects
                      filieres={filieres}
                      levels={levels}
                      filiereValue={studentAssignment.filiere_id}
                      levelValue={studentAssignment.level_id}
                      onFiliere={(value) => setStudentAssignment({ ...studentAssignment, filiere_id: value })}
                      onLevel={(value) => setStudentAssignment({ ...studentAssignment, level_id: value })}
                    />
                    <Select label="Statut" value={studentAssignment.status} onChange={(value) => setStudentAssignment({ ...studentAssignment, status: value })}>
                      <option value="">Ne pas changer</option>
                      <option value="active">Actif</option>
                      <option value="suspended">Suspendu</option>
                      <option value="graduated">Diplome</option>
                    </Select>
                    <button className="btn-primary flex items-center gap-2 w-full justify-center">
                      <Save size={18} /> Enregistrer
                    </button>
                  </form>
                </Panel>
              </div>
              <Panel title="Etudiants" icon={GraduationCap}>
                <DataTable
                  headers={["Code", "Nom", "Email", "Filiere", "Niveau", "Statut", ""]}
                  rows={students.map((item) => [
                    item.student_code,
                    `${item.first_name} ${item.last_name}`,
                    item.email,
                    item.filiere_name || "-",
                    item.level_name || "-",
                    item.status,
                    <button key={item.id} onClick={() => void handleDelete("students", item.id)} className="text-danger hover:bg-danger/10 p-2 rounded-md" title="Supprimer">
                      <Trash2 size={16} />
                    </button>,
                  ])}
                />
              </Panel>
            </section>
          )}

          {tab === "teachers" && (
            <section className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
              <div className="space-y-6">
                <Panel title="Profil professeur" icon={UserCog}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const payload = { ...teacherForm, department_id: teacherForm.department_id || null, specialization: teacherForm.specialization || null };
                      void submitJson("/admin/teachers", "POST", payload, "Professeur cree.").then(() => setTeacherForm(emptyTeacher));
                    }}
                  >
                    <Select label="Compte professeur" value={teacherForm.user_id} onChange={(value) => setTeacherForm({ ...teacherForm, user_id: value })} required>
                      <option value="">Selectionner</option>
                      {teacherUsers.map((item) => <option key={item.id} value={item.id}>{item.email}</option>)}
                    </Select>
                    <Input label="Code professeur" value={teacherForm.teacher_code} onChange={(value) => setTeacherForm({ ...teacherForm, teacher_code: value })} required />
                    <div className="grid grid-cols-2 gap-3">
                      <Input label="Prenom" value={teacherForm.first_name} onChange={(value) => setTeacherForm({ ...teacherForm, first_name: value })} required />
                      <Input label="Nom" value={teacherForm.last_name} onChange={(value) => setTeacherForm({ ...teacherForm, last_name: value })} required />
                    </div>
                    <Input label="Specialite" value={teacherForm.specialization} onChange={(value) => setTeacherForm({ ...teacherForm, specialization: value })} />
                    <Select label="Departement" value={teacherForm.department_id} onChange={(value) => setTeacherForm({ ...teacherForm, department_id: value })}>
                      <option value="">Aucun</option>
                      {departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </Select>
                    <button className="btn-primary flex items-center gap-2 w-full justify-center">
                      <Plus size={18} /> Ajouter
                    </button>
                  </form>
                </Panel>
                <Panel title="Affecter module" icon={BookOpen}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void submitJson(`/admin/modules/${moduleAssignment.module_id}/teacher`, "PATCH", { teacher_id: moduleAssignment.teacher_id || null }, "Module affecte au professeur.");
                    }}
                  >
                    <Select label="Module" value={moduleAssignment.module_id} onChange={(value) => setModuleAssignment({ ...moduleAssignment, module_id: value })} required>
                      <option value="">Selectionner</option>
                      {modules.map((item) => <option key={item.id} value={item.id}>{item.code} - {item.name}</option>)}
                    </Select>
                    <Select label="Professeur" value={moduleAssignment.teacher_id} onChange={(value) => setModuleAssignment({ ...moduleAssignment, teacher_id: value })}>
                      <option value="">Aucun</option>
                      {teachers.map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name}</option>)}
                    </Select>
                    <button className="btn-primary flex items-center gap-2 w-full justify-center">
                      <Save size={18} /> Enregistrer
                    </button>
                  </form>
                </Panel>
              </div>
              <Panel title="Professeurs" icon={UserCog}>
                <DataTable
                  headers={["Code", "Nom", "Email", "Departement", "Specialite", ""]}
                  rows={teachers.map((item) => [
                    item.teacher_code,
                    `${item.first_name} ${item.last_name}`,
                    item.email,
                    item.department_name || "-",
                    item.specialization || "-",
                    <button key={item.id} onClick={() => void handleDelete("enseignants", item.id)} className="text-danger hover:bg-danger/10 p-2 rounded-md" title="Supprimer">
                      <Trash2 size={16} />
                    </button>,
                  ])}
                />
              </Panel>
            </section>
          )}

          {tab === "academics" && (
            <section className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
              <div className="space-y-6">
                <Panel title="Departement" icon={Building2}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void submitJson("/admin/departments", "POST", departmentForm, "Departement cree.").then(() => setDepartmentForm(emptyDepartment));
                    }}
                  >
                    <Input label="Nom" value={departmentForm.name} onChange={(value) => setDepartmentForm({ ...departmentForm, name: value })} required />
                    <Input label="Description" value={departmentForm.description} onChange={(value) => setDepartmentForm({ ...departmentForm, description: value })} />
                    <button className="btn-primary flex items-center gap-2 w-full justify-center"><Plus size={18} /> Ajouter</button>
                  </form>
                </Panel>
                <Panel title="Filiere" icon={Layers}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const payload = {
                        ...filiereForm,
                        department_id: filiereForm.department_id || null,
                        duration_years: filiereForm.duration_years ? Number(filiereForm.duration_years) : null,
                      };
                      void submitJson("/admin/filieres", "POST", payload, "Filiere creee.").then(() => setFiliereForm(emptyFiliere));
                    }}
                  >
                    <Select label="Departement" value={filiereForm.department_id} onChange={(value) => setFiliereForm({ ...filiereForm, department_id: value })}>
                      <option value="">Aucun</option>
                      {departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </Select>
                    <Input label="Nom" value={filiereForm.name} onChange={(value) => setFiliereForm({ ...filiereForm, name: value })} required />
                    <Input label="Code" value={filiereForm.code} onChange={(value) => setFiliereForm({ ...filiereForm, code: value })} required />
                    <Input label="Duree annees" type="number" value={filiereForm.duration_years} onChange={(value) => setFiliereForm({ ...filiereForm, duration_years: value })} />
                    <button className="btn-primary flex items-center gap-2 w-full justify-center"><Plus size={18} /> Ajouter</button>
                  </form>
                </Panel>
                <Panel title="Niveau" icon={GraduationCap}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void submitJson("/admin/levels", "POST", { name: levelForm.name, order_number: Number(levelForm.order_number) }, "Niveau cree.").then(() => setLevelForm(emptyLevel));
                    }}
                  >
                    <Input label="Nom" value={levelForm.name} onChange={(value) => setLevelForm({ ...levelForm, name: value })} required />
                    <Input label="Ordre" type="number" value={levelForm.order_number} onChange={(value) => setLevelForm({ ...levelForm, order_number: value })} required />
                    <button className="btn-primary flex items-center gap-2 w-full justify-center"><Plus size={18} /> Ajouter</button>
                  </form>
                </Panel>
                <Panel title="Module" icon={BookOpen}>
                  <form
                    className="space-y-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const payload = {
                        ...moduleForm,
                        teacher_id: moduleForm.teacher_id || null,
                        semester: moduleForm.semester ? Number(moduleForm.semester) : null,
                      };
                      void submitJson("/admin/modules", "POST", payload, "Module cree.").then(() => setModuleForm(emptyModule));
                    }}
                  >
                    <Select label="Filiere" value={moduleForm.filiere_id} onChange={(value) => setModuleForm({ ...moduleForm, filiere_id: value })} required>
                      <option value="">Selectionner</option>
                      {filieres.map((item) => <option key={item.id} value={item.id}>{item.code} - {item.name}</option>)}
                    </Select>
                    <Select label="Professeur" value={moduleForm.teacher_id} onChange={(value) => setModuleForm({ ...moduleForm, teacher_id: value })}>
                      <option value="">Aucun</option>
                      {teachers.map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name}</option>)}
                    </Select>
                    <Input label="Nom" value={moduleForm.name} onChange={(value) => setModuleForm({ ...moduleForm, name: value })} required />
                    <Input label="Code" value={moduleForm.code} onChange={(value) => setModuleForm({ ...moduleForm, code: value })} required />
                    <Input label="Semestre" type="number" value={moduleForm.semester} onChange={(value) => setModuleForm({ ...moduleForm, semester: value })} />
                    <button className="btn-primary flex items-center gap-2 w-full justify-center"><Plus size={18} /> Ajouter</button>
                  </form>
                </Panel>
              </div>
              <div className="space-y-6">
                <Panel title="Filieres" icon={Layers}>
                  <DataTable
                    headers={["Code", "Nom", "Departement", "Duree", ""]}
                    rows={filieres.map((item) => [
                      item.code,
                      item.name,
                      item.department_name || "-",
                      item.duration_years ? `${item.duration_years} ans` : "-",
                      <button key={item.id} onClick={() => void handleDelete("filieres", item.id)} className="text-danger hover:bg-danger/10 p-2 rounded-md" title="Supprimer">
                        <Trash2 size={16} />
                      </button>,
                    ])}
                  />
                </Panel>
                <Panel title="Modules" icon={BookOpen}>
                  <DataTable
                    headers={["Code", "Nom", "Filiere", "Professeur", "Semestre", ""]}
                    rows={modules.map((item) => [
                      item.code,
                      item.name,
                      item.filiere_name || "-",
                      item.teacher_first_name ? `${item.teacher_first_name} ${item.teacher_last_name}` : "-",
                      item.semester ?? "-",
                      <button key={item.id} onClick={() => void handleDelete("modules", item.id)} className="text-danger hover:bg-danger/10 p-2 rounded-md" title="Supprimer">
                        <Trash2 size={16} />
                      </button>,
                    ])}
                  />
                </Panel>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-border bg-slate-50 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary-light text-primary flex items-center justify-center">
          <Icon size={19} />
        </div>
        <h2 className="font-bold text-text">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) {
  return (
    <label className="block">
      <span className="block text-sm font-semibold text-text-muted mb-1">{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} required={required} className="input-field" />
    </label>
  );
}

function Select({ label, value, onChange, children, required = false }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode; required?: boolean }) {
  return (
    <label className="block">
      <span className="block text-sm font-semibold text-text-muted mb-1">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} required={required} className="input-field bg-white">
        {children}
      </select>
    </label>
  );
}

function AcademicSelects({
  filieres,
  levels,
  filiereValue,
  levelValue,
  onFiliere,
  onLevel,
}: {
  filieres: Filiere[];
  levels: Level[];
  filiereValue: string;
  levelValue: string;
  onFiliere: (value: string) => void;
  onLevel: (value: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <Select label="Filiere" value={filiereValue} onChange={onFiliere}>
        <option value="">Aucune</option>
        {filieres.map((item) => <option key={item.id} value={item.id}>{item.code} - {item.name}</option>)}
      </Select>
      <Select label="Niveau" value={levelValue} onChange={onLevel}>
        <option value="">Aucun</option>
        {levels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </Select>
    </div>
  );
}

function DataTable({ headers, rows }: { headers: string[]; rows: React.ReactNode[][] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-text-muted py-6 text-center">Aucune donnee.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-text-muted border-b border-border">
            {headers.map((header) => (
              <th key={header} className="py-2.5 px-3 font-semibold whitespace-nowrap">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="py-3 px-3 text-text align-middle whitespace-nowrap">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
