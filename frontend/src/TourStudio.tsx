import { useEffect, useMemo, useRef, useState } from "react";
import { Viewer } from "@photo-sphere-viewer/core";
import { MarkersPlugin } from "@photo-sphere-viewer/markers-plugin";
import "@photo-sphere-viewer/core/index.css";
import "@photo-sphere-viewer/markers-plugin/index.css";

type Language = "uz" | "ru" | "en";
type Asset = { id: string; name: string; sizeBytes: number; url: string };
type Hotspot = { target_scene_id: string; title: string; yaw: number; pitch: number };
type Scene = { id: string; media_id: string; title: string; description: string; hotspots: Hotspot[] };
type Tour = { title: string; description: string; scenes: Scene[] };
type Props = { token: string; language: Language; projectId: string; projectName: string; onBack: () => void };

const copy = {
 uz: {
  title:"Interaktiv virtual tur", back:"Orqaga", tourTitle:"Tur nomi", description:"Tur tavsifi",
  addScene:"Panoramadan sahna qo‘shish", chooseMedia:"Panorama tanlang", noMedia:"Avval Media Studio bo‘limiga panorama yuklang.",
  scenes:"Tur sahnalari", noScenes:"Hali sahna qo‘shilmagan", sceneTitle:"Sahna nomi", sceneDesc:"Sahna tavsifi",
  up:"Yuqoriga", down:"Pastga", remove:"O‘chirish", hotspots:"Interaktiv nuqtalar", hotspotTitle:"Nuqta nomi",
  target:"O‘tish sahnasi", yaw:"Gorizontal burchak (°)", pitch:"Vertikal burchak (°)", addHotspot:"Nuqta qo‘shish",
  save:"Turni saqlash", saving:"Saqlanmoqda…", saved:"Tur saqlandi", export:"Loyihani ZIP shaklida eksport qilish", exporting:"Eksport qilinmoqda…", exported:"Loyiha ZIP fayli yuklab olindi", preview:"360° ko‘rib chiqish",
  chooseScene:"Ko‘rish uchun sahnani tanlang", needTwo:"Nuqta qo‘shish uchun kamida 2 ta sahna kerak.",
  loadError:"Turni yoki media fayllarni yuklab bo‘lmadi.", saveError:"Turni saqlab bo‘lmadi.",
  markerHelp:"Nuqtani panoramada kerakli tomonga qarab turgan paytingizda qo‘shing. Burchaklarni gradusda kiriting.",
  emptyHotspots:"Bu sahnada interaktiv nuqtalar yo‘q."
 },
 ru: {
  title:"Конструктор виртуального тура", back:"Назад", tourTitle:"Название тура", description:"Описание тура",
  addScene:"Добавить панораму как сцену", chooseMedia:"Выберите панораму", noMedia:"Сначала загрузите панорамы в Media Studio.",
  scenes:"Сцены тура", noScenes:"Сцены ещё не добавлены", sceneTitle:"Название сцены", sceneDesc:"Описание сцены",
  up:"Выше", down:"Ниже", remove:"Удалить", hotspots:"Интерактивные точки", hotspotTitle:"Название точки",
  target:"Сцена перехода", yaw:"Горизонтальный угол (°)", pitch:"Вертикальный угол (°)", addHotspot:"Добавить точку",
  save:"Сохранить тур", saving:"Сохранение…", saved:"Тур сохранён", export:"Экспортировать проект в ZIP", exporting:"Экспорт…", exported:"ZIP-архив проекта скачан", preview:"Просмотр 360°",
  chooseScene:"Выберите сцену для просмотра", needTwo:"Для добавления точки нужно минимум 2 сцены.",
  loadError:"Не удалось загрузить тур или медиафайлы.", saveError:"Не удалось сохранить тур.",
  markerHelp:"Добавляйте точку, когда панорама направлена в нужную сторону. Углы вводятся в градусах.",
  emptyHotspots:"В этой сцене пока нет интерактивных точек."
 },
 en: {
  title:"Interactive virtual tour builder", back:"Back", tourTitle:"Tour title", description:"Tour description",
  addScene:"Add panorama as a scene", chooseMedia:"Choose a panorama", noMedia:"Upload panoramas in Media Studio first.",
  scenes:"Tour scenes", noScenes:"No scenes added yet", sceneTitle:"Scene title", sceneDesc:"Scene description",
  up:"Move up", down:"Move down", remove:"Remove", hotspots:"Interactive hotspots", hotspotTitle:"Hotspot label",
  target:"Destination scene", yaw:"Horizontal angle (°)", pitch:"Vertical angle (°)", addHotspot:"Add hotspot",
  save:"Save tour", saving:"Saving…", saved:"Tour saved", export:"Export project as ZIP", exporting:"Exporting…", exported:"Project ZIP downloaded", preview:"360° preview",
  chooseScene:"Choose a scene to preview", needTwo:"At least 2 scenes are needed to add a hotspot.",
  loadError:"Could not load the tour or media files.", saveError:"Could not save the tour.",
  markerHelp:"Add a hotspot while the panorama is facing the desired direction. Enter angles in degrees.",
  emptyHotspots:"This scene has no interactive hotspots yet."
 }
};

function escapeHtml(value: string) {
 return value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;");
}

export default function TourStudio({ token, language, projectId, projectName, onBack }: Props) {
 const t=copy[language];
 const host=useRef<HTMLDivElement>(null);
 const [assets,setAssets]=useState<Asset[]>([]);
 const [tour,setTour]=useState<Tour>({title:projectName,description:"",scenes:[]});
 const [activeSceneId,setActiveSceneId]=useState("");
 const [selectedMediaId,setSelectedMediaId]=useState("");
 const [hotspotTitle,setHotspotTitle]=useState("");
 const [targetSceneId,setTargetSceneId]=useState("");
 const [yaw,setYaw]=useState("0");
 const [pitch,setPitch]=useState("0");
 const [panoramaUrl,setPanoramaUrl]=useState<string|null>(null);
 const [loading,setLoading]=useState(true);
 const [saving,setSaving]=useState(false);\n const [exporting,setExporting]=useState(false);
 const [error,setError]=useState("");
 const [message,setMessage]=useState("");
 const activeScene=useMemo(()=>tour.scenes.find(scene=>scene.id===activeSceneId)??tour.scenes[0]??null,[tour.scenes,activeSceneId]);

 useEffect(()=>{
  let cancelled=false;
  async function load(){
   setLoading(true);setError("");
   try{
    const headers={Authorization:`Bearer ${token}`};
    const [mediaResponse,tourResponse]=await Promise.all([
     fetch(`/api/projects/${projectId}/media`,{headers}),
     fetch(`/api/projects/${projectId}/tour`,{headers})
    ]);
    if(!mediaResponse.ok||!tourResponse.ok)throw new Error();
    const media=await mediaResponse.json();
    const stored=await tourResponse.json();
    if(cancelled)return;
    setAssets(Array.isArray(media)?media:[]);
    const scenes=Array.isArray(stored.scenes)?stored.scenes:[];
    setTour({title:stored.title||projectName,description:stored.description||"",scenes});
    setActiveSceneId(scenes[0]?.id||"");
    setSelectedMediaId((Array.isArray(media)?media:[]).find((asset:Asset)=>!scenes.some((scene:Scene)=>scene.media_id===asset.id))?.id||"");
   }catch{if(!cancelled)setError(t.loadError);}
   finally{if(!cancelled)setLoading(false);}
  }
  if(projectId)void load();
  return()=>{cancelled=true;};
 },[projectId,token]);

 useEffect(()=>{
  let cancelled=false;
  let objectUrl:string|undefined;
  setPanoramaUrl(null);
  if(!activeScene)return;
  fetch(`/api/media/${activeScene.media_id}/file`,{headers:{Authorization:`Bearer ${token}`}})
   .then(response=>{if(!response.ok)throw new Error();return response.blob();})
   .then(blob=>{if(cancelled)return;objectUrl=URL.createObjectURL(blob);setPanoramaUrl(objectUrl);})
   .catch(()=>{if(!cancelled)setError(t.loadError);});
  return()=>{cancelled=true;if(objectUrl)URL.revokeObjectURL(objectUrl);};
 },[activeScene?.media_id,token]);

 useEffect(()=>{
  if(!host.current||!panoramaUrl||!activeScene)return;
  const viewer=new Viewer({
   container:host.current,
   panorama:panoramaUrl,
   navbar:["zoom","move","fullscreen"],
   plugins:[[MarkersPlugin,{markers:activeScene.hotspots.map((hotspot,index)=>({
    id:`hotspot-${index}`,
    position:{yaw:hotspot.yaw,pitch:hotspot.pitch},
    html:`<button class="tour-hotspot-marker" type="button">${escapeHtml(hotspot.title)}</button>`,
    tooltip:hotspot.title,
    data:{targetSceneId:hotspot.target_scene_id}
   }))}]]
  });
  const markers=viewer.getPlugin(MarkersPlugin);
  markers.addEventListener("select-marker",({marker})=>{
   const data=marker.data as {targetSceneId?:string}|undefined;
   if(data?.targetSceneId)setActiveSceneId(data.targetSceneId);
  });
  return()=>viewer.destroy();
 },[panoramaUrl,activeScene?.id,activeScene?.hotspots]);

 function updateScene(id:string,patch:Partial<Scene>){
  setTour(current=>({...current,scenes:current.scenes.map(scene=>scene.id===id?{...scene,...patch}:scene)}));
  setMessage("");
 }
 function addScene(){
  const asset=assets.find(item=>item.id===selectedMediaId);
  if(!asset||tour.scenes.some(scene=>scene.media_id===asset.id))return;
  const scene:Scene={id:crypto.randomUUID(),media_id:asset.id,title:asset.name.replace(/\.[^.]+$/,""),description:"",hotspots:[]};
  setTour(current=>({...current,scenes:[...current.scenes,scene]}));
  setActiveSceneId(scene.id);
  setSelectedMediaId(assets.find(item=>item.id!==asset.id&&!tour.scenes.some(scene=>scene.media_id===item.id))?.id||"");
  setMessage("");
 }
 function moveScene(id:string,direction:-1|1){
  setTour(current=>{
   const index=current.scenes.findIndex(scene=>scene.id===id);
   const target=index+direction;
   if(index<0||target<0||target>=current.scenes.length)return current;
   const scenes=[...current.scenes];[scenes[index],scenes[target]]=[scenes[target],scenes[index]];
   return {...current,scenes};
  });
 }
 function removeScene(id:string){
  setTour(current=>({...current,scenes:current.scenes.filter(scene=>scene.id!==id).map(scene=>({...scene,hotspots:scene.hotspots.filter(hotspot=>hotspot.target_scene_id!==id)}))}));
  if(activeSceneId===id)setActiveSceneId(tour.scenes.find(scene=>scene.id!==id)?.id||"");
 }
 function addHotspot(){
  if(!activeScene||!targetSceneId||!hotspotTitle.trim()||targetSceneId===activeScene.id)return;
  const hotspot:Hotspot={target_scene_id:targetSceneId,title:hotspotTitle.trim(),yaw:Number(yaw)*Math.PI/180,pitch:Number(pitch)*Math.PI/180};
  updateScene(activeScene.id,{hotspots:[...activeScene.hotspots,hotspot]});
  setHotspotTitle("");
 }
 function removeHotspot(index:number){
  if(!activeScene)return;
  updateScene(activeScene.id,{hotspots:activeScene.hotspots.filter((_,i)=>i!==index)});
 }
 async function saveTour(){
  if(saving)return;
  setSaving(true);setError("");setMessage("");
  try{
   const response=await fetch(`/api/projects/${projectId}/tour`,{
    method:"PUT",
    headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},
    body:JSON.stringify(tour)
   });
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw new Error(data.detail||t.saveError);
   setMessage(t.saved);
  }catch(error){setError(error instanceof Error?error.message:t.saveError);}
  finally{setSaving(false);}
 }

 return <section className="tour-studio">
  <div className="media-head"><div><div className="eyebrow muted">360° TOUR WORKSPACE · {projectName}</div><h2>{t.title}</h2></div><div className="editor-actions"><button className="secondary" disabled={exporting||saving} onClick={()=>void exportProject()}>{exporting?t.exporting:t.export}</button><button className="secondary" onClick={onBack}>{t.back}</button></div></div>
  {loading?<div className="media-empty">…</div>:<>
   <div className="tour-meta">
    <label className="field-label">{t.tourTitle}<input value={tour.title} onChange={e=>setTour(current=>({...current,title:e.target.value}))}/></label>
    <label className="field-label">{t.description}<textarea rows={2} value={tour.description} onChange={e=>setTour(current=>({...current,description:e.target.value}))}/></label>
   </div>
   <div className="tour-add-scene">
    <select value={selectedMediaId} onChange={e=>setSelectedMediaId(e.target.value)}>
     <option value="">{t.chooseMedia}</option>
     {assets.filter(asset=>!tour.scenes.some(scene=>scene.media_id===asset.id)).map(asset=><option key={asset.id} value={asset.id}>{asset.name}</option>)}
    </select>
    <button className="primary" disabled={!selectedMediaId} onClick={addScene}>{t.addScene}</button>
   </div>
   {assets.length===0&&<div className="media-empty">{t.noMedia}</div>}
   <div className="tour-layout">
    <div className="tour-scenes-panel"><h3>{t.scenes}</h3>
     {tour.scenes.length===0?<p>{t.noScenes}</p>:tour.scenes.map((scene,index)=><div className={`tour-scene-card ${activeScene?.id===scene.id?"selected":""}`} key={scene.id}>
      <button className="tour-scene-select" onClick={()=>setActiveSceneId(scene.id)}><span>{String(index+1).padStart(2,"0")}</span><strong>{scene.title||t.sceneTitle}</strong></button>
      <div className="tour-scene-actions"><button onClick={()=>moveScene(scene.id,-1)} disabled={index===0} title={t.up}>↑</button><button onClick={()=>moveScene(scene.id,1)} disabled={index===tour.scenes.length-1} title={t.down}>↓</button><button onClick={()=>removeScene(scene.id)} title={t.remove}>×</button></div>
     </div>)}
    </div>
    <div className="tour-editor-panel">
     {activeScene?<>
      <div className="tour-scene-fields">
       <label className="field-label">{t.sceneTitle}<input value={activeScene.title} onChange={e=>updateScene(activeScene.id,{title:e.target.value})}/></label>
       <label className="field-label">{t.sceneDesc}<textarea rows={2} value={activeScene.description} onChange={e=>updateScene(activeScene.id,{description:e.target.value})}/></label>
      </div>
      <h3>{t.preview}</h3>
      {panoramaUrl?<div className="tour-viewer" ref={host}/>:<div className="media-empty">{t.chooseScene}</div>}
      <div className="tour-hotspots"><h3>{t.hotspots}</h3><p>{t.markerHelp}</p>
       {activeScene.hotspots.length===0?<small>{t.emptyHotspots}</small>:activeScene.hotspots.map((hotspot,index)=><div className="tour-hotspot-row" key={index}><span>{hotspot.title} → {tour.scenes.find(scene=>scene.id===hotspot.target_scene_id)?.title}</span><small>{(hotspot.yaw*180/Math.PI).toFixed(0)}°, {(hotspot.pitch*180/Math.PI).toFixed(0)}°</small><button onClick={()=>removeHotspot(index)}>×</button></div>)}
       {tour.scenes.length<2?<p>{t.needTwo}</p>:<div className="hotspot-form">
        <input value={hotspotTitle} onChange={e=>setHotspotTitle(e.target.value)} placeholder={t.hotspotTitle}/>
        <select value={targetSceneId} onChange={e=>setTargetSceneId(e.target.value)}><option value="">{t.target}</option>{tour.scenes.filter(scene=>scene.id!==activeScene.id).map(scene=><option key={scene.id} value={scene.id}>{scene.title}</option>)}</select>
        <div className="hotspot-coordinates"><label>{t.yaw}<input type="number" min="-360" max="360" step="1" value={yaw} onChange={e=>setYaw(e.target.value)}/></label><label>{t.pitch}<input type="number" min="-90" max="90" step="1" value={pitch} onChange={e=>setPitch(e.target.value)}/></label></div>
        <button className="secondary" disabled={!hotspotTitle.trim()||!targetSceneId||Number(yaw)<-360||Number(yaw)>360||Number(pitch)<-90||Number(pitch)>90} onClick={addHotspot}>{t.addHotspot}</button>
       </div>}
      </div>
     </>:<div className="media-empty">{t.chooseScene}</div>}
    </div>
   </div>
   {error&&<div className="media-alert">{error}</div>}
   {message&&<div className="media-success">✓ {message}</div>}
   <div className="tour-save-row"><button className="primary" onClick={()=>void saveTour()} disabled={saving||!tour.title.trim()}>{saving?t.saving:t.save}</button></div>
  </>}
 </section>;
}
