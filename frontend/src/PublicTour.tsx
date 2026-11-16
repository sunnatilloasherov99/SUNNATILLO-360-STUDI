import { useEffect, useMemo, useRef, useState } from "react";
import { Viewer } from "@photo-sphere-viewer/core";
import { MarkersPlugin } from "@photo-sphere-viewer/markers-plugin";
import "@photo-sphere-viewer/core/index.css";
import "@photo-sphere-viewer/markers-plugin/index.css";
import type { Language } from "./i18n";

type Hotspot={target_scene_id:string;title:string;yaw:number;pitch:number};
type Scene={id:string;title:string;description:string;media_url:string;hotspots:Hotspot[]};
type Tour={project_name:string;title:string;description:string;scenes:Scene[]};
type Props={token:string;language:Language};

const words={
 uz:{loading:"Virtual tur yuklanmoqda…",notFound:"Bu virtual tur mavjud emas yoki havola o‘chirilgan.",scenes:"Tur sahnalari",back:"Bosh sahifa",noScenes:"Bu turda ko‘rsatish uchun sahnalar yo‘q.",made:"SUNNATILLO 360° STUDIO orqali yaratildi"},
 ru:{loading:"Загрузка виртуального тура…",notFound:"Этот виртуальный тур недоступен или ссылка отключена.",scenes:"Сцены тура",back:"Главная",noScenes:"В этом туре нет доступных сцен.",made:"Создано в SUNNATILLO 360° STUDIO"},
 en:{loading:"Loading virtual tour…",notFound:"This virtual tour is unavailable or its link has been revoked.",scenes:"Tour scenes",back:"Home",noScenes:"There are no scenes to display in this tour.",made:"Created with SUNNATILLO 360° STUDIO"}
};

function escapeHtml(value:string){return value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;");}

export default function PublicTour({token,language}:Props){
 const t=words[language];
 const host=useRef<HTMLDivElement>(null);
 const [tour,setTour]=useState<Tour|null>(null);
 const [activeId,setActiveId]=useState("");
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 const activeScene=useMemo(()=>tour?.scenes.find(scene=>scene.id===activeId)??tour?.scenes[0]??null,[tour,activeId]);
 useEffect(()=>{
  let cancelled=false;
  fetch(`/api/public/tours/${token}`)
   .then(response=>{if(!response.ok)throw new Error();return response.json();})
   .then(data=>{if(cancelled)return;setTour(data);setActiveId(data.scenes?.[0]?.id||"");})
   .catch(()=>{if(!cancelled)setError(t.notFound);})
   .finally(()=>{if(!cancelled)setLoading(false);});
  return()=>{cancelled=true;};
 },[token]);
 useEffect(()=>{
  if(!host.current||!activeScene)return;
  const viewer=new Viewer({
   container:host.current,
   panorama:activeScene.media_url,
   navbar:["zoom","move","fullscreen"],
   plugins:[[MarkersPlugin,{markers:activeScene.hotspots.map((hotspot,index)=>({
    id:`public-hotspot-${index}`,
    position:{yaw:hotspot.yaw,pitch:hotspot.pitch},
    html:`<button class="tour-hotspot-marker" type="button">${escapeHtml(hotspot.title)}</button>`,
    tooltip:hotspot.title,
    data:{targetSceneId:hotspot.target_scene_id}
   }))}]]
  });
  const markers=viewer.getPlugin(MarkersPlugin);
  markers.addEventListener("select-marker",({marker})=>{
   const data=marker.data as {targetSceneId?:string}|undefined;
   if(data?.targetSceneId)setActiveId(data.targetSceneId);
  });
  return()=>viewer.destroy();
 },[activeScene?.id,activeScene?.media_url,activeScene?.hotspots]);
 return <main className="public-tour-page">
  <header className="public-tour-header"><div><span>SUNNATILLO 360° STUDIO</span><small>{tour?.project_name||"360° VIRTUAL TOUR"}</small></div><a href="/">{t.back}</a></header>
  {loading?<div className="public-tour-state">{t.loading}</div>:error?<div className="public-tour-state">{error}</div>:tour?<div className="public-tour-content">
   <section className="public-tour-intro"><div className="eyebrow muted">360° INTERACTIVE EXPERIENCE</div><h1>{tour.title}</h1><p>{tour.description}</p></section>
   {activeScene?<><div className="public-tour-viewer" ref={host}/><div className="public-tour-scene-info"><h2>{activeScene.title}</h2><p>{activeScene.description}</p></div><div className="public-tour-scenes"><h3>{t.scenes}</h3><div>{tour.scenes.map((scene,index)=><button key={scene.id} className={activeScene.id===scene.id?"selected":""} onClick={()=>setActiveId(scene.id)}><span>{String(index+1).padStart(2,"0")}</span>{scene.title}</button>)}</div></div></>:<div className="public-tour-state">{t.noScenes}</div>}
   <footer className="public-tour-footer">{t.made}</footer>
  </div>:null}
 </main>;
}
