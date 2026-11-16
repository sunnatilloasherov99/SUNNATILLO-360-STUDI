import { useEffect, useRef, useState } from "react";
import { Viewer } from "@photo-sphere-viewer/core";
import "@photo-sphere-viewer/core/index.css";

type Language = "uz" | "ru" | "en";
type Project = { id: string; name: string; mode: "ai" | "manual" | "collab"; updatedAt: string };
type Asset = { id: string; projectId: string; name: string; contentType: string; sizeBytes: number; createdAt: string; url: string };
type Props = { language: Language; projectId: string; projectName: string; projects: Project[]; onBack: () => void; onSelectProject: (project: Project) => void; onRefreshProjects: () => Promise<void> };
const copy = {
 uz:{title:"360° panorama ko‘ruvchi",invalid:"Faqat JPG, PNG yoki WebP rasmlarini tanlang.",readError:"Tanlangan rasmni o‘qib bo‘lmadi.",back:"Orqaga",import:"Panorama rasmini tanlash",hint:"JPG, PNG yoki WebP. To‘liq sferik panorama uchun 2:1 nisbat tavsiya etiladi.",empty:"Hozircha panorama tanlanmagan",ratio:"Rasm nisbati",resolution:"O‘lchami",status:"Tekshiruv",pass:"360° ko‘rish uchun mos",warn:"Nisbat 2:1 emas — panorama noto‘g‘ri ko‘rinishi mumkin",low:"Aniqlik past — yuqori sifatli manba tavsiya etiladi",ready:"Panorama serverga saqlandi. Asl fayl o‘zgartirilmaydi.",replace:"Boshqa rasm tanlash",uploading:"Yuklanmoqda…",failed:"Faylni serverga yuklab bo‘lmadi.",chooseProject:"Avval loyiha tanlang",project:"Loyiha",files:"Saqlangan panoramalar",noFiles:"Bu loyihada hali panorama yo‘q",saved:"Serverda saqlangan",uploadHint:"Fayl loyiha bilan bog‘lanadi va serverda saqlanadi."},
 ru:{title:"Просмотр панорамы 360°",invalid:"Выберите изображение JPG, PNG или WebP.",readError:"Не удалось прочитать выбранное изображение.",back:"Назад",import:"Выбрать панорамное изображение",hint:"JPG, PNG или WebP. Для сферической панорамы рекомендуется соотношение 2:1.",empty:"Панорама ещё не выбрана",ratio:"Соотношение сторон",resolution:"Разрешение",status:"Проверка",pass:"Подходит для просмотра 360°",warn:"Соотношение не 2:1 — панорама может отображаться некорректно",low:"Низкое разрешение — рекомендуется исходник более высокого качества",ready:"Панорама сохранена на сервере. Исходный файл не изменяется.",replace:"Выбрать другое изображение",uploading:"Загрузка…",failed:"Не удалось загрузить файл на сервер.",chooseProject:"Сначала выберите проект",project:"Проект",files:"Сохранённые панорамы",noFiles:"В этом проекте пока нет панорам",saved:"Сохранено на сервере",uploadHint:"Файл будет привязан к проекту и сохранён на сервере."},
 en:{title:"360° panorama viewer",invalid:"Please select a JPG, PNG or WebP image.",readError:"The selected image could not be read.",back:"Back",import:"Choose panorama image",hint:"JPG, PNG or WebP. A 2:1 ratio is recommended for a full spherical panorama.",empty:"No panorama selected yet",ratio:"Aspect ratio",resolution:"Resolution",status:"Validation",pass:"Suitable for 360° viewing",warn:"Not a 2:1 ratio — the panorama may display incorrectly",low:"Low resolution — a higher-quality source is recommended",ready:"Panorama saved to the server. The original file remains unchanged.",replace:"Choose another image",uploading:"Uploading…",failed:"Could not upload the file to the server.",chooseProject:"Select a project first",project:"Project",files:"Saved panoramas",noFiles:"This project has no panoramas yet",saved:"Saved on server",uploadHint:"The file will be linked to this project and stored on the server."}
};
export default function MediaStudio({ language, projectId, projectName, projects, onBack, onSelectProject, onRefreshProjects }: Props) {
 const t=copy[language]; const host=useRef<HTMLDivElement>(null);
 const [url,setUrl]=useState<string|null>(null); const [meta,setMeta]=useState<{width:number;height:number;name:string}|null>(null);
 const [assets,setAssets]=useState<Asset[]>([]); const [error,setError]=useState(""); const [uploading,setUploading]=useState(false);
 async function loadAssets(id:string){try{const r=await fetch(`/api/projects/${id}/media`);if(!r.ok)throw new Error();setAssets(await r.json());setError("");}catch{setError(t.failed);}}
 useEffect(()=>{setUrl(null);setMeta(null);setAssets([]);if(projectId)void loadAssets(projectId);},[projectId]);
 useEffect(()=>{if(!url||!host.current)return;const viewer=new Viewer({container:host.current,panorama:url,navbar:["zoom","move","fullscreen"]});return()=>viewer.destroy();},[url]);
 function showAsset(asset:Asset){const image=new Image();const fileUrl=asset.url;image.onload=()=>{setMeta({width:image.naturalWidth,height:image.naturalHeight,name:asset.name});setUrl(fileUrl);setError("");};image.onerror=()=>setError(t.readError);image.src=fileUrl;}
 async function choose(file?:File){
  if(!file)return;
  if(!["image/jpeg","image/png","image/webp"].includes(file.type)){setError(t.invalid);return;}
  if(!projectId){setError(t.chooseProject);return;}
  const localUrl=URL.createObjectURL(file);const image=new Image();
  image.onload=async()=>{
   setMeta({width:image.naturalWidth,height:image.naturalHeight,name:file.name});setUrl(localUrl);setUploading(true);setError("");
   try{const body=new FormData();body.append("file",file);const response=await fetch(`/api/projects/${projectId}/media`,{method:"POST",body});if(!response.ok)throw new Error();const asset:Asset=await response.json();URL.revokeObjectURL(localUrl);setAssets(current=>[asset,...current.filter(a=>a.id!==asset.id)]);setUrl(asset.url);setMeta({width:image.naturalWidth,height:image.naturalHeight,name:asset.name});}
   catch{setError(t.failed);}
   finally{setUploading(false);}
  };
  image.onerror=()=>{URL.revokeObjectURL(localUrl);setError(t.readError);};image.src=localUrl;
 }
 const valid=!!meta&&Math.abs(meta.width/meta.height-2)<.02;
 return <section className="media-studio">
  <div className="media-head"><div><div className="eyebrow muted">MEDIA WORKSPACE · SERVER STORAGE</div><h2>{t.title}</h2></div><button className="secondary" onClick={onBack}>{t.back}</button></div>
  {!projectId?<div className="media-empty"><strong>{t.chooseProject}</strong><select className="project-picker" defaultValue="" onChange={e=>{const p=projects.find(x=>x.id===e.target.value);if(p)onSelectProject(p);}}><option value="" disabled>{t.project}</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></div>:<>
   <div className="media-project-label">{t.project}: <strong>{projectName}</strong></div>
   <div className="media-toolbar"><label className="primary upload-button">＋ {url?t.replace:t.import}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>choose(e.target.files?.[0])}/></label><span>{t.hint}</span></div>
   <div className="media-upload-note">{uploading?t.uploading:t.uploadHint}</div>
   {error&&<div className="media-alert">{error}</div>}
   {url&&meta?<><div className="panorama-viewer" ref={host}/><div className="media-report"><div><span>{t.resolution}</span><strong>{meta.width} × {meta.height}</strong></div><div><span>{t.ratio}</span><strong>{(meta.width/meta.height).toFixed(2)}:1</strong></div><div><span>{t.status}</span><strong className={valid?"good":"warning"}>{valid?t.pass:t.warn}</strong></div></div>{meta.width<4000&&<p className="media-warning">{t.low}</p>}<p className="media-success">✓ {t.ready} <span>· {meta.name}</span></p></>:<div className="media-empty"><div>360°</div><strong>{t.empty}</strong><span>{t.hint}</span></div>}
   <div className="saved-media"><h3>{t.files}</h3>{assets.length===0?<p>{t.noFiles}</p>:<div className="saved-media-list">{assets.map(asset=><button key={asset.id} className="saved-media-item" onClick={()=>showAsset(asset)}><span>360°</span><strong>{asset.name}</strong><small>{(asset.sizeBytes/1024/1024).toFixed(1)} MB · {t.saved}</small></button>)}</div>}</div>
  </>}
 </section>;
}
