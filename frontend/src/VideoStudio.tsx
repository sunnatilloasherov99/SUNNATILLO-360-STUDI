import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { Language } from "./i18n";

type Asset = { id: string; name: string; contentType: string; sizeBytes: number; createdAt: string; url: string };
type Project = { id: string; name: string; mode: "ai" | "manual" | "collab"; updatedAt: string };
type Props = { token: string; language: Language; projectId: string; projectName: string; projects: Project[]; onBack: () => void; onSelectProject: (project: Project) => void };

const copy={
 uz:{title:"360° video studiyasi",back:"Orqaga",project:"Loyiha",chooseProject:"Avval loyiha tanlang",upload:"360° video yuklash",hint:"MP4 yoki WebM. To‘liq 360° ko‘rish uchun 2:1 equirectangular video tavsiya etiladi.",files:"Saqlangan videolar",empty:"Hali video yuklanmagan",play:"Ijro etish",pause:"Pauza",mute:"Ovozsiz",unmute:"Ovozli",uploading:"Yuklanmoqda…",failed:"Videoni yuklash yoki ochishda xatolik.",invalid:"Faqat MP4 yoki WebM videoni tanlang.",ratio:"Video nisbati",resolution:"Video o‘lchami",good:"360° formatga mos",warn:"Nisbat 2:1 emas — bu video 360° ko‘rinishda noto‘g‘ri chiqishi mumkin.",saved:"Serverda saqlangan",noVideo:"Video tanlanmagan",quality:"360° video uchun 2:1 format kerak.",trim:"Kesish oralig‘i",trimStart:"Boshlanish",trimEnd:"Tugash",saveTrim:"Kesish sozlamalarini saqlash",trimSaved:"Kesish sozlamalari saqlandi",trimError:"Kesish sozlamalarini saqlab bo‘lmadi."},
 ru:{title:"Студия видео 360°",back:"Назад",project:"Проект",chooseProject:"Сначала выберите проект",upload:"Загрузить видео 360°",hint:"MP4 или WebM. Для полного обзора 360° рекомендуется equirectangular 2:1.",files:"Сохранённые видео",empty:"Видео ещё не загружено",play:"Воспроизвести",pause:"Пауза",mute:"Без звука",unmute:"Со звуком",uploading:"Загрузка…",failed:"Ошибка загрузки или открытия видео.",invalid:"Выберите видео MP4 или WebM.",ratio:"Соотношение видео",resolution:"Размер видео",good:"Подходит для 360°",warn:"Соотношение не 2:1 — видео может отображаться некорректно.",saved:"Сохранено на сервере",noVideo:"Видео не выбрано",quality:"Для видео 360° требуется формат 2:1.",trim:"Диапазон обрезки",trimStart:"Начало",trimEnd:"Конец",saveTrim:"Сохранить обрезку",trimSaved:"Настройки обрезки сохранены",trimError:"Не удалось сохранить обрезку."},
 en:{title:"360° video studio",back:"Back",project:"Project",chooseProject:"Select a project first",upload:"Upload 360° video",hint:"MP4 or WebM. Equirectangular 2:1 video is recommended for full 360° viewing.",files:"Saved videos",empty:"No videos uploaded yet",play:"Play",pause:"Pause",mute:"Mute",unmute:"Unmute",uploading:"Uploading…",failed:"Could not upload or open the video.",invalid:"Choose an MP4 or WebM video.",ratio:"Video aspect ratio",resolution:"Video dimensions",good:"Suitable for 360°",warn:"Not a 2:1 ratio — this video may look distorted in 360° view.",saved:"Saved on server",noVideo:"No video selected",quality:"A 2:1 format is required for 360° video.",trim:"Trim range",trimStart:"Start",trimEnd:"End",saveTrim:"Save trim settings",trimSaved:"Trim settings saved",trimError:"Could not save trim settings."}
};

export default function VideoStudio({token,language,projectId,projectName,projects,onBack,onSelectProject}:Props){
 const t=copy[language];
 const host=useRef<HTMLDivElement>(null);
 const videoRef=useRef<HTMLVideoElement>(null);
 const [assets,setAssets]=useState<Asset[]>([]);
 const [videoUrl,setVideoUrl]=useState<string|null>(null);
 const [activeAsset,setActiveAsset]=useState<Asset|null>(null);
 const [uploading,setUploading]=useState(false);
 const [error,setError]=useState("");
 const [playing,setPlaying]=useState(false);
 const [muted,setMuted]=useState(false);
 const [duration,setDuration]=useState(0);
 const [currentTime,setCurrentTime]=useState(0);
 const [dimensions,setDimensions]=useState({width:0,height:0});
 const [trimStart,setTrimStart]=useState(0);
 const [trimEnd,setTrimEnd]=useState(0);
 const [trimSaving,setTrimSaving]=useState(false);
 const [trimMessage,setTrimMessage]=useState("");


 async function loadAssets(id:string){
  try{
   const response=await fetch(`/api/projects/${id}/media`,{headers:{Authorization:`Bearer ${token}`}});
   if(!response.ok)throw new Error();
   setAssets((await response.json()).filter((asset:Asset)=>asset.contentType.startsWith("video/")));
  }catch{setError(t.failed);}
 }
 useEffect(()=>{
  setVideoUrl(null);setActiveAsset(null);setAssets([]);
  if(projectId)void loadAssets(projectId);
 },[projectId,token]);
 useEffect(()=>{
  setTrimStart(0);setTrimEnd(0);setTrimMessage("");
  if(!projectId)return;
  void fetch(`/api/projects/${projectId}/video-settings`,{headers:{Authorization:`Bearer ${token}`}})
   .then(response=>{if(!response.ok)throw new Error();return response.json();})
   .then(settings=>{setTrimStart(Number(settings.start_seconds)||0);setTrimEnd(Number(settings.end_seconds)||0);})
   .catch(()=>setError(t.failed));
 },[projectId,token]);

 useEffect(()=>()=>{if(videoUrl)URL.revokeObjectURL(videoUrl);},[videoUrl]);

 async function openAsset(asset:Asset){
  try{
   const response=await fetch(asset.url,{headers:{Authorization:`Bearer ${token}`}});
   if(!response.ok)throw new Error();
   const blob=await response.blob();
   setVideoUrl(URL.createObjectURL(blob));setActiveAsset(asset);setError("");setPlaying(false);setCurrentTime(0);
  }catch{setError(t.failed);}
 }
 async function upload(file?:File){
  if(!file)return;
  if(!["video/mp4","video/webm"].includes(file.type)){setError(t.invalid);return;}
  if(!projectId){setError(t.chooseProject);return;}
  setUploading(true);setError("");
  try{
   const form=new FormData();form.append("file",file);
   const response=await fetch(`/api/projects/${projectId}/media`,{method:"POST",headers:{Authorization:`Bearer ${token}`},body:form});
   if(!response.ok)throw new Error();
   const asset:Asset=await response.json();
   setAssets(current=>[asset,...current.filter(item=>item.id!==asset.id)]);
   await openAsset(asset);
  }catch{setError(t.failed);}
  finally{setUploading(false);}
 }
 async function togglePlay(){
  const video=videoRef.current;if(!video)return;
  if(video.paused){try{await video.play();setPlaying(true);}catch{setError(t.failed);}}
  else{video.pause();setPlaying(false);}
 }
 function changeTime(value:number){const video=videoRef.current;if(video){video.currentTime=value;setCurrentTime(value);}}
 function handleTimeUpdate(video:HTMLVideoElement){
  if(trimEnd>trimStart&&video.currentTime>=trimEnd){video.pause();video.currentTime=trimStart;setCurrentTime(trimStart);setPlaying(false);return;}
  setCurrentTime(video.currentTime);
 }
 async function saveTrim(){
  if(!projectId||trimSaving)return;
  setTrimSaving(true);setTrimMessage("");
  try{
   const response=await fetch(`/api/projects/${projectId}/video-settings`,{method:"PUT",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},body:JSON.stringify({start_seconds:trimStart,end_seconds:trimEnd})});
   if(!response.ok)throw new Error();
   setTrimMessage(t.trimSaved);
  }catch{setTrimMessage(t.trimError);}
  finally{setTrimSaving(false);}
 }

 function changeMute(){const video=videoRef.current;if(video){video.muted=!video.muted;setMuted(video.muted);}}

 useEffect(()=>{
  const container=host.current;
  const video=videoRef.current;
  if(!container||!videoUrl||!video)return;
  const mount:HTMLDivElement=container;
  const media:HTMLVideoElement=video;
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  mount.appendChild(renderer.domElement);
  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(75,1,0.1,1200);
  const geometry=new THREE.SphereGeometry(500,64,48);
  geometry.scale(-1,1,1);
  const texture=new THREE.VideoTexture(media);
  texture.colorSpace=THREE.SRGBColorSpace;
  const material=new THREE.MeshBasicMaterial({map:texture});
  scene.add(new THREE.Mesh(geometry,material));
  let longitude=0,latitude=0,dragging=false,lastX=0,lastY=0,frame=0;
  const canvas=renderer.domElement;
  canvas.style.width="100%";canvas.style.height="100%";canvas.style.display="block";canvas.style.cursor="grab";canvas.style.touchAction="none";
  function resize(){
   const width=mount.clientWidth||640,height=mount.clientHeight||360;
   renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();
  }
  function down(event:PointerEvent){dragging=true;lastX=event.clientX;lastY=event.clientY;canvas.setPointerCapture(event.pointerId);canvas.style.cursor="grabbing";}
  function move(event:PointerEvent){if(!dragging)return;longitude-=(event.clientX-lastX)*0.12;latitude+=(event.clientY-lastY)*0.12;latitude=Math.max(-85,Math.min(85,latitude));lastX=event.clientX;lastY=event.clientY;}
  function up(){dragging=false;canvas.style.cursor="grab";}
  function wheel(event:WheelEvent){event.preventDefault();camera.fov=Math.max(35,Math.min(100,camera.fov+event.deltaY*0.035));camera.updateProjectionMatrix();}
  function animate(){
   frame=requestAnimationFrame(animate);
   const phi=THREE.MathUtils.degToRad(90-latitude);
   const theta=THREE.MathUtils.degToRad(longitude);
   camera.lookAt(500*Math.sin(phi)*Math.cos(theta),500*Math.cos(phi),500*Math.sin(phi)*Math.sin(theta));
   texture.needsUpdate=media.readyState>=2;
   renderer.render(scene,camera);
  }
  resize();window.addEventListener("resize",resize);
  canvas.addEventListener("pointerdown",down);canvas.addEventListener("pointermove",move);canvas.addEventListener("pointerup",up);canvas.addEventListener("pointercancel",up);canvas.addEventListener("wheel",wheel,{passive:false});
  animate();
  return()=>{
   cancelAnimationFrame(frame);window.removeEventListener("resize",resize);
   canvas.removeEventListener("pointerdown",down);canvas.removeEventListener("pointermove",move);canvas.removeEventListener("pointerup",up);canvas.removeEventListener("pointercancel",up);canvas.removeEventListener("wheel",wheel);
   texture.dispose();material.dispose();geometry.dispose();renderer.dispose();renderer.domElement.remove();
  };
 },[videoUrl]);

 const ratio=dimensions.height?dimensions.width/dimensions.height:0;
 const validRatio=!!ratio&&Math.abs(ratio-2)<0.02;
 return <section className="video-studio">
  <div className="media-head"><div><div className="eyebrow muted">360° VIDEO WORKSPACE · {projectName||"PROJECT"}</div><h2>{t.title}</h2></div><button className="secondary" onClick={onBack}>{t.back}</button></div>
  {!projectId?<div className="media-empty"><strong>{t.chooseProject}</strong><select className="project-picker" defaultValue="" onChange={e=>{const p=projects.find(item=>item.id===e.target.value);if(p)onSelectProject(p);}}><option value="">{t.project}</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></div>:<>
   <div className="media-toolbar"><label className="primary upload-button">＋ {uploading?t.uploading:t.upload}<input type="file" accept="video/mp4,video/webm" onChange={e=>upload(e.target.files?.[0])}/></label><span>{t.hint}</span></div>
   {error&&<div className="media-alert">{error}</div>}
   {videoUrl?<><div className="video-360-stage"><video ref={videoRef} src={videoUrl} playsInline muted={muted} onLoadedMetadata={e=>setDimensions({width:e.currentTarget.videoWidth,height:e.currentTarget.videoHeight})} onDurationChange={e=>setDuration(e.currentTarget.duration||0)} onTimeUpdate={e=>handleTimeUpdate(e.currentTarget)} onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onEnded={()=>setPlaying(false)} /><div className="video-360-canvas" ref={host}/></div><div className="video-controls"><button className="secondary" onClick={()=>void togglePlay()}>{playing?t.pause:t.play}</button><input aria-label="Video progress" type="range" min="0" max={duration||0} step="0.1" value={Math.min(currentTime,duration||0)} onChange={e=>changeTime(Number(e.target.value))}/><span>{Math.floor(currentTime/60)}:{String(Math.floor(currentTime%60)).padStart(2,"0")} / {Math.floor(duration/60)}:{String(Math.floor(duration%60)).padStart(2,"0")}</span><button className="secondary" onClick={changeMute}>{muted?t.unmute:t.mute}</button></div><div className="video-trim-panel"><h3>{t.trim}</h3><label>{t.trimStart} · {trimStart.toFixed(1)}s<input type="range" min="0" max={duration||0} step="0.1" value={Math.min(trimStart,duration||0)} onChange={e=>{const value=Number(e.target.value);setTrimStart(value);if(trimEnd&&trimEnd<=value)setTrimEnd(Math.min(duration,value+0.1));setTrimMessage("");}}/></label><label>{t.trimEnd} · {(trimEnd||duration).toFixed(1)}s<input type="range" min={Math.min(trimStart,duration||0)} max={duration||0} step="0.1" value={Math.min(trimEnd||duration,duration||0)} onChange={e=>{setTrimEnd(Number(e.target.value));setTrimMessage("");}}/></label><div className="video-trim-actions"><button className="primary" disabled={trimSaving||!duration} onClick={()=>void saveTrim()}>{trimSaving?"…":t.saveTrim}</button>{trimMessage&&<span>{trimMessage}</span>}</div><small>Original video remains unchanged. Playback range is saved with this project.</small></div><div className="media-report"><div><span>{t.resolution}</span><strong>{dimensions.width} × {dimensions.height}</strong></div><div><span>{t.ratio}</span><strong>{ratio?ratio.toFixed(2)+":1":"—"}</strong></div><div><span>{t.quality}</span><strong className={validRatio?"good":"warning"}>{validRatio?t.good:t.warn}</strong></div></div><p className="media-success">✓ {t.saved} · {activeAsset?.name}</p></>:<div className="media-empty"><div>360°</div><strong>{t.noVideo}</strong><span>{t.hint}</span></div>}
   <div className="saved-media"><h3>{t.files}</h3>{assets.length===0?<p>{t.empty}</p>:<div className="saved-media-list">{assets.map(asset=><button key={asset.id} className="saved-media-item" onClick={()=>void openAsset(asset)}><span>▶</span><strong>{asset.name}</strong><small>{(asset.sizeBytes/1024/1024).toFixed(1)} MB · {t.saved}</small></button>)}</div>}</div>
  </>}
 </section>;
}
