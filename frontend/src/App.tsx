import { useEffect, useMemo, useState } from "react";
import { Aperture, Bot, CheckCircle2, ChevronRight, CircleHelp, CloudUpload, FolderOpen, Globe2, Languages, Layers3, Plus, ShieldCheck, SlidersHorizontal, Sparkles, WandSparkles } from "lucide-react";
import { getMissingTranslations, translate } from "./i18n";
import type { Language } from "./i18n";
import MediaStudio from "./MediaStudio";

type Mode = "ai" | "manual" | "collab";
type Project = { id: string; name: string; mode: Mode; updatedAt: string };
const modeIcons = { ai: WandSparkles, manual: SlidersHorizontal, collab: Bot };
const modeKeys: { id: Mode; title: "aiMode" | "manualMode" | "collabMode"; description: "aiModeDesc" | "manualModeDesc" | "collabModeDesc" }[] = [
  { id: "ai", title: "aiMode", description: "aiModeDesc" },
  { id: "manual", title: "manualMode", description: "manualModeDesc" },
  { id: "collab", title: "collabMode", description: "collabModeDesc" }
];
export default function App() {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem("s360-language");
    return saved === "ru" || saved === "en" ? saved : "uz";
  });
  const [mode, setMode] = useState<Mode>("manual");
  const [showCreate, setShowCreate] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [showMedia, setShowMedia] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [apiError, setApiError] = useState("");
  const [savingProject, setSavingProject] = useState(false);
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key);
  const missing = useMemo(() => getMissingTranslations(), []);

  async function loadProjects() {
    setLoadingProjects(true);
    try {
      const response = await fetch("/api/projects");
      if (!response.ok) throw new Error("API");
      const data = await response.json();
      setProjects(Array.isArray(data) ? data : []);
      setApiError("");
    } catch {
      setApiError(language === "ru" ? "Не удалось подключиться к серверу. Проверьте, запущен ли API." : language === "en" ? "Could not connect to the server. Check whether the API is running." : "Serverga ulanib bo‘lmadi. API ishga tushirilganini tekshiring.");
    } finally { setLoadingProjects(false); }
  }
  useEffect(() => { void loadProjects(); }, []);
  function changeLanguage(next: Language) { setLanguage(next); localStorage.setItem("s360-language", next); }
  async function createProject() {
    if (!projectName.trim() || savingProject) return;
    setSavingProject(true);
    try {
      const response = await fetch("/api/projects", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: projectName.trim(), mode })
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(detail?.detail || "API");
      }
      const project: Project = await response.json();
      setProjects(current => [project, ...current.filter(item => item.id !== project.id)]);
      setActiveProject(project); setProjectName(""); setShowCreate(false); setApiError("");
    } catch (error) {
      setApiError(error instanceof Error && error.message !== "API" ? error.message : (language === "ru" ? "Не удалось сохранить проект на сервере." : language === "en" ? "Could not save the project to the server." : "Loyihani serverga saqlab bo‘lmadi."));
    } finally { setSavingProject(false); }
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Aperture size={23}/></div><div><strong>SUNNATILLO</strong><span>360° STUDIO</span></div></div>
      <div className="side-label">{t("workspace")}</div>
      <button className="nav-item active"><Layers3 size={17}/>{t("workspace")}</button>
      <button className="nav-item" onClick={() => setShowCreate(true)}><FolderOpen size={17}/>{t("projects")}</button>
      <div className="side-label tools-label">{t("studio")}</div>
      <button className="nav-item" onClick={() => setActiveProject(null)}><Globe2 size={17}/>{t("publisher")} <span className="soon">{t("comingSoon")}</span></button>
      <button className="nav-item"><ShieldCheck size={17}/>{t("quality")} <span className="soon">{t("comingSoon")}</span></button>
      <button className="nav-item" onClick={() => setShowMedia(true)}><CloudUpload size={17}/>{t("media")}</button>
      <div className="sidebar-bottom"><div className="privacy"><ShieldCheck size={16}/><span>{t("privacyNote")}</span></div><div className="version">{t("webEdition")} · 0.2.0</div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb">SUNNATILLO 360° STUDIO <span>/</span> {t("workspace")}</div><div className="top-actions"><span className="status"><i/> {t("independent")}</span><label className="language"><Languages size={16}/><select value={language} onChange={e => changeLanguage(e.target.value as Language)} aria-label={t("language")}><option value="uz">O‘zbekcha</option><option value="ru">Русский</option><option value="en">English</option></select></label></div></header>
      <section className="hero"><div className="hero-copy"><div className="eyebrow"><span/> {t("eyebrow")}</div><h1>{t("headline")}</h1><p>{t("subheadline")}</p><div className="hero-actions"><button className="primary" onClick={() => setShowCreate(true)}><Plus size={17}/>{t("newProject")}</button><button className="secondary" onClick={() => document.getElementById("projects")?.scrollIntoView({ behavior: "smooth" })}><FolderOpen size={17}/>{t("openProject")}</button></div></div><div className="hero-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="planet"><Aperture size={76} strokeWidth={1.1}/></div><div className="float-tag tag-top"><Sparkles size={14}/> {t("immersiveTag")}</div></div></section>
      <section className="mode-section"><div className="section-heading"><div><div className="eyebrow muted">{t("projectWorkflow")}</div><h2>{t("chooseMode")}</h2></div><span className="step">01 <i/> 03</span></div><div className="mode-grid">{modeKeys.map(item => { const Icon = modeIcons[item.id]; return <button key={item.id} className={`mode-card ${mode === item.id ? "selected" : ""}`} onClick={() => setMode(item.id)}><div className="mode-icon"><Icon size={21}/></div><div className="mode-title">{t(item.title)}</div><p>{t(item.description)}</p><div className="mode-select">{mode === item.id ? <><CheckCircle2 size={16}/> {t("selected")}</> : t("selectMode")}</div></button>; })}</div><div className="mode-footer"><div className="privacy-inline"><ShieldCheck size={16}/>{t("privacyNote")}</div><button className="primary" onClick={() => setShowCreate(true)}>{t("start")}<ChevronRight size={17}/></button></div></section>
      <section className="projects-section" id="projects"><div className="section-heading"><div><div className="eyebrow muted">{t("yourWork")}</div><h2>{t("projects")}</h2></div><button className="text-button" onClick={() => setShowCreate(true)}><Plus size={16}/>{t("newProject")}</button></div>
      {apiError && <div className="media-alert">{apiError}</div>}
      {loadingProjects ? <div className="empty"><strong>{language === "ru" ? "Загрузка проектов…" : language === "en" ? "Loading projects…" : "Loyihalar yuklanmoqda…"}</strong></div> : projects.length === 0 ? <div className="empty"><div className="empty-icon"><FolderOpen size={24}/></div><strong>{t("noProjects")}</strong><span>{language === "ru" ? "Проекты будут храниться на сервере" : language === "en" ? "Projects will be stored on the server" : "Loyihalar serverda saqlanadi"}</span></div> : <div className="project-list">{projects.map(project => <button className="project-row" key={project.id} onClick={() => { setActiveProject(project); setMode(project.mode); }}><div className="project-symbol"><Aperture size={20}/></div><div className="project-info"><strong>{project.name}</strong><span>{t(project.mode === "ai" ? "aiMode" : project.mode === "manual" ? "manualMode" : "collabMode")} · {new Date(project.updatedAt).toLocaleDateString()}</span></div><ChevronRight size={18}/></button>)}</div>}</section>
      {showMedia && <MediaStudio language={language} projectId={activeProject?.id || ""} projectName={activeProject?.name || ""} projects={projects} onBack={() => setShowMedia(false)} onSelectProject={setActiveProject}/>}
      {activeProject && !showMedia && <section className="active-project"><div><div className="eyebrow muted">{t("activeProject")}</div><h2>{activeProject.name}</h2><p>{t("comingSoon")}: editor modules are being implemented in stages.</p></div><button className="secondary" onClick={() => setShowMedia(true)}>{t("media")}</button></section>}
      <footer><span>© 2026 SUNNATILLO 360° STUDIO</span><span>{t("portableTag")}</span></footer>
    </main>
    {showCreate && <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) setShowCreate(false); }}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button className="modal-close" onClick={() => setShowCreate(false)}>×</button><div className="eyebrow muted">{t("newWorkspace")}</div><h2 id="modal-title">{t("newProject")}</h2><label className="field-label">{t("projectName")}<input autoFocus value={projectName} onChange={e => setProjectName(e.target.value)} placeholder={t("projectNamePlaceholder")} onKeyDown={e => e.key === "Enter" && void createProject()}/></label><div className="modal-mode">{t(mode === "ai" ? "aiMode" : mode === "manual" ? "manualMode" : "collabMode")}</div><div className="modal-actions"><button className="secondary" onClick={() => setShowCreate(false)}>{t("cancel")}</button><button className="primary" disabled={!projectName.trim() || savingProject} onClick={() => void createProject()}>{savingProject ? "…" : t("create")}<ChevronRight size={16}/></button></div></div></div>}
    {missing.length > 0 && <div className="translation-warning"><CircleHelp size={14}/> {missing.length} missing translations</div>}
  </div>;
}
