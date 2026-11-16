import { useEffect, useRef, useState } from "react";

type Language = "uz" | "ru" | "en";
type Props = { imageUrl: string; language: Language; patchCanvasRef: { current: HTMLCanvasElement | null } };

const labels = {
 uz: { title:"Qo‘lda nuqsonni tuzatish", source:"Namuna manbasini belgilash", sourceReady:"Namuna belgilandi", brush:"Cho‘tka o‘lchami", undo:"Ortga", redo:"Qaytarish", clear:"Tuzatishlarni tozalash", hint:"Avval “Namuna manbasini belgilash”ni bosing va rasmdagi toza joyni tanlang. Keyin nuqson ustidan chizing. Chap/o‘ng chetga yaqin chizish 360° bo‘ylab davom etadi.", needSource:"Avval namuna manbasini belgilang.", noSource:"Namuna tanlanmagan", disclaimer:"Bu oddiy clone brush: tanlangan joydagi piksellarni ko‘chiradi. U yo‘qolgan detallarni AI orqali qayta yaratmaydi. Asl rasm o‘zgarmaydi; natija eksportda yangi nusxa bo‘ladi." },
 ru: { title:"Ручное исправление дефектов", source:"Выбрать источник образца", sourceReady:"Источник выбран", brush:"Размер кисти", undo:"Отменить", redo:"Повторить", clear:"Очистить исправления", hint:"Сначала нажмите «Выбрать источник образца» и выберите чистую область. Затем закрасьте дефект. Рисование у левого/правого края продолжается через границу 360°.", needSource:"Сначала выберите источник образца.", noSource:"Источник не выбран", disclaimer:"Это простой инструмент клонирования пикселей. Он не восстанавливает отсутствующие детали с помощью ИИ. Оригинал не изменяется; результат экспортируется отдельной копией." },
 en: { title:"Manual defect repair", source:"Choose clone source", sourceReady:"Source selected", brush:"Brush size", undo:"Undo", redo:"Redo", clear:"Clear repairs", hint:"Choose “Choose clone source”, click a clean area, then paint over the defect. Painting near the left/right edge wraps across the 360° boundary.", needSource:"Choose a clone source first.", noSource:"No source selected", disclaimer:"This is a basic clone brush that copies existing pixels. It does not use AI to invent missing details. The original remains unchanged; export creates a separate copy." }
};

export default function PanoramaRepairCanvas({ imageUrl, language, patchCanvasRef }: Props) {
 const t=labels[language];
 const imageRef=useRef<HTMLImageElement|null>(null);
 const sourceRef=useRef<{x:number;y:number}|null>(null);
 const drawingRef=useRef(false);
 const lastPointRef=useRef<{x:number;y:number}|null>(null);
 const undoRef=useRef<ImageData[]>([]);
 const redoRef=useRef<ImageData[]>([]);
 const [sourceMode,setSourceMode]=useState(false);
 const [sourceLabel,setSourceLabel]=useState(t.noSource);
 const [brushSize,setBrushSize]=useState(48);
 const [undoCount,setUndoCount]=useState(0);
 const [redoCount,setRedoCount]=useState(0);
 const [notice,setNotice]=useState("");

 useEffect(()=>{
  sourceRef.current=null;undoRef.current=[];redoRef.current=[];setSourceMode(false);setSourceLabel(t.noSource);setUndoCount(0);setRedoCount(0);setNotice("");
  const canvas=patchCanvasRef.current;const image=imageRef.current;
  if(canvas&&image&&image.complete&&image.naturalWidth){canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;canvas.getContext("2d")?.clearRect(0,0,canvas.width,canvas.height);}
 },[imageUrl,patchCanvasRef,t.noSource]);

 function snapshot(){
  const canvas=patchCanvasRef.current;const context=canvas?.getContext("2d");
  if(!canvas||!context)return;
  try{undoRef.current=[...undoRef.current.slice(-11),context.getImageData(0,0,canvas.width,canvas.height)];redoRef.current=[];setUndoCount(undoRef.current.length);setRedoCount(0);}catch{setNotice("Canvas snapshot unavailable");}
 }
 function point(event:React.PointerEvent<HTMLCanvasElement>){
  const canvas=patchCanvasRef.current;if(!canvas)return null;
  const rect=canvas.getBoundingClientRect();
  return {x:Math.max(0,Math.min(canvas.width-1,(event.clientX-rect.left)*canvas.width/rect.width)),y:Math.max(0,Math.min(canvas.height-1,(event.clientY-rect.top)*canvas.height/rect.height))};
 }
 function stamp(target:{x:number;y:number}){
  const canvas=patchCanvasRef.current;const image=imageRef.current;const context=canvas?.getContext("2d");
  const source=sourceRef.current;if(!canvas||!image||!context||!source)return;
  const radius=Math.max(2,Math.min(brushSize,Math.floor(Math.min(canvas.width,canvas.height)/4)));
  const sx=Math.max(radius,Math.min(canvas.width-radius,source.x));
  const sy=Math.max(radius,Math.min(canvas.height-radius,source.y));
  const stampCanvas=document.createElement("canvas");stampCanvas.width=radius*2;stampCanvas.height=radius*2;
  const stampContext=stampCanvas.getContext("2d");if(!stampContext)return;
  stampContext.drawImage(image,sx-radius,sy-radius,radius*2,radius*2,0,0,radius*2,radius*2);
  stampContext.globalCompositeOperation="destination-in";
  const gradient=stampContext.createRadialGradient(radius,radius,radius*0.55,radius,radius,radius);
  gradient.addColorStop(0,"rgba(0,0,0,1)");gradient.addColorStop(1,"rgba(0,0,0,0)");
  stampContext.fillStyle=gradient;stampContext.fillRect(0,0,radius*2,radius*2);
  for(const wrap of [-canvas.width,0,canvas.width]){
   const x=target.x-radius+wrap;
   if(x+radius*2<0||x>canvas.width)continue;
   context.drawImage(stampCanvas,x,target.y-radius);
  }
 }
 function onPointerDown(event:React.PointerEvent<HTMLCanvasElement>){
  const p=point(event);if(!p)return;
  if(sourceMode){
   const canvas=patchCanvasRef.current;if(!canvas)return;
   const radius=Math.max(2,Math.min(brushSize,Math.floor(Math.min(canvas.width,canvas.height)/4)));
   sourceRef.current={x:Math.max(radius,Math.min(canvas.width-radius,p.x)),y:Math.max(radius,Math.min(canvas.height-radius,p.y))};
   setSourceLabel(Math.round(sourceRef.current.x)+", "+Math.round(sourceRef.current.y));setSourceMode(false);setNotice("");return;
  }
  if(!sourceRef.current){setNotice(t.needSource);return;}
  snapshot();drawingRef.current=true;lastPointRef.current=p;event.currentTarget.setPointerCapture(event.pointerId);stamp(p);
 }
 function onPointerMove(event:React.PointerEvent<HTMLCanvasElement>){
  if(!drawingRef.current)return;const p=point(event);if(!p)return;
  const last=lastPointRef.current||p;const dx=p.x-last.x;const dy=p.y-last.y;const distance=Math.hypot(dx,dy);const step=Math.max(2,brushSize*0.22);
  const steps=Math.max(1,Math.ceil(distance/step));
  for(let i=1;i<=steps;i++)stamp({x:last.x+dx*i/steps,y:last.y+dy*i/steps});
  lastPointRef.current=p;
 }
 function onPointerUp(){drawingRef.current=false;lastPointRef.current=null;}
 function restore(from:ImageData[],to:ImageData[],setFrom:(n:number)=>void,setTo:(n:number)=>void){
  const canvas=patchCanvasRef.current;const context=canvas?.getContext("2d");if(!canvas||!context||!from.length)return;
  try{to.push(context.getImageData(0,0,canvas.width,canvas.height));const next=from.pop();if(next)context.putImageData(next,0,0);setFrom(from.length);setTo(to.length);}catch{setNotice("History unavailable");}
 }
 function clear(){
  const canvas=patchCanvasRef.current;const context=canvas?.getContext("2d");if(!canvas||!context)return;
  snapshot();context.clearRect(0,0,canvas.width,canvas.height);setNotice("");
 }
 return <section className="panorama-repair-panel">
  <div className="panorama-repair-heading"><h3>{t.title}</h3><div className="panorama-repair-actions">
   <button type="button" className={sourceMode?"primary":"secondary"} onClick={()=>{setSourceMode(true);setNotice("");}}>{sourceMode?t.source+"…":t.source}</button>
   <button type="button" className="secondary" disabled={!undoCount} onClick={()=>restore(undoRef.current,redoRef.current,setUndoCount,setRedoCount)}>{t.undo}</button>
   <button type="button" className="secondary" disabled={!redoCount} onClick={()=>restore(redoRef.current,undoRef.current,setRedoCount,setUndoCount)}>{t.redo}</button>
   <button type="button" className="secondary" disabled={!undoCount} onClick={clear}>{t.clear}</button>
  </div></div>
  <label className="panorama-brush-control">{t.brush}<input type="range" min="8" max="160" step="4" value={brushSize} onChange={e=>setBrushSize(Number(e.target.value))}/><span>{brushSize}px</span></label>
  <div className="panorama-repair-image" style={{touchAction:"none"}}>
   <img ref={imageRef} src={imageUrl} alt="Panorama repair source" onLoad={e=>{const canvas=patchCanvasRef.current;if(canvas){canvas.width=e.currentTarget.naturalWidth;canvas.height=e.currentTarget.naturalHeight;}}}/>
   <canvas ref={patchCanvasRef} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} aria-label={t.title}/>
  </div>
  <div className="panorama-repair-status">{sourceMode?t.source+"…":sourceRef.current?t.sourceReady+": "+sourceLabel:t.noSource}{notice&&" · "+notice}</div>
  <p>{t.hint}</p><small>{t.disclaimer}</small>
 </section>;
}
