import { useEffect, useRef, useState } from "react";
import PanoramaRepairCanvas from "./PanoramaRepairCanvas";
import { Viewer } from "@photo-sphere-viewer/core";
import "@photo-sphere-viewer/core/index.css";

type Language = "uz" | "ru" | "en";
type Project = { id: string; name: string; mode: "ai" | "manual" | "collab"; updatedAt: string };
type EditSettings = { brightness: number; contrast: number; saturation: number; seamOffset: number; seamBlend: number };
type Asset = { id: string; projectId: string; name: string; contentType: string; sizeBytes: number; createdAt: string; url: string };
type SeamReport = { score: number; level: "low" | "medium" | "high" };
type Props = { token: string; language: Language; projectId: string; projectName: string; projects: Project[]; onBack: () => void; onSelectProject: (project: Project) => void };
const copy = {
 uz:{title:"360° panorama ko‘ruvchi",invalid:"Faqat JPG, PNG yoki WebP rasmlarini tanlang.",readError:"Tanlangan rasmni o‘qib bo‘lmadi.",back:"Orqaga",import:"Panorama rasmini tanlash",hint:"JPG, PNG yoki WebP. To‘liq sferik panorama uchun 2:1 nisbat tavsiya etiladi.",empty:"Hozircha panorama tanlanmagan",ratio:"Rasm nisbati",resolution:"O‘lchami",status:"Tekshiruv",pass:"360° ko‘rish uchun mos",warn:"Nisbat 2:1 emas — panorama noto‘g‘ri ko‘rinishi mumkin",low:"Aniqlik past — yuqori sifatli manba tavsiya etiladi",ready:"Panorama serverga saqlandi. Asl fayl o‘zgartirilmaydi.",replace:"Boshqa rasm tanlash",uploading:"Yuklanmoqda…",failed:"Faylni serverga yuklab bo‘lmadi.",chooseProject:"Avval loyiha tanlang",project:"Loyiha",files:"Saqlangan panoramalar",noFiles:"Bu loyihada hali panorama yo‘q",saved:"Serverda saqlangan",uploadHint:"Fayl loyiha bilan bog‘lanadi va serverda saqlanadi.",adjustments:"Rang va yorug‘lik sozlamalari",brightness:"Yorqinlik",contrast:"Kontrast",saturation:"To‘yinganlik",saveEdits:"Sozlamalarni saqlash",resetEdits:"Asliga qaytarish",savingEdits:"Saqlanmoqda…",savedEdits:"Sozlamalar saqlandi",exportImage:"Tahrirlangan rasmni eksport qilish",exporting:"Eksport qilinmoqda…",exported:"Tahrirlangan rasm yuklab olindi",exportFailed:"Rasmni eksport qilib bo‘lmadi",seamOffset:"Chok joylashuvi (°)",seamHint:"Panoramadagi chap/o‘ng chokni boshqa tomonga ko‘chiradi; chokni avtomatik yamamaydi.",seamAnalysis:"Chok uzluksizligi (taxminiy)",seamLow:"Chegaradagi rang farqi past.",seamMedium:"Chegarada sezilarli rang farqi bor.",seamHigh:"Chegarada katta rang farqi bor.",seamDisclaimer:"Bu avtomatik taxmin faqat rasmning chap va o‘ng chetlarini solishtiradi. Ichki choklar, parallaks va obyektlarning qo‘shilib ketishini aniqlamaydi.",seamBlendPercent:"Chokni yumshatish (%)",seamBlendHint:"Chegaradagi rang farqini chetlar bo‘ylab asta aralashtiradi. Juda katta qiymat ayrim obyektlarni xiralashtirishi mumkin.",autoSeam:"Eng sokin chok joyini topish",findingSeam:"Tahlil qilinmoqda…",autoSeamHint:"Rasm bo‘ylab vertikal chiziqlarni solishtirib, rang o‘zgarishi eng kam joyni tanlaydi. Bu taxminiy joylashuv.",autoSeamFailed:"Chok uchun mos joy topilmadi.",aiAnalyze:"AI yordamida panoramani tahlil qilish",aiAnalyzing:"AI tahlil qilmoqda…",aiTitle:"AI tahlil xulosasi",aiFailed:"AI tahlilini bajarib bo‘lmadi. Mahalliy Ollama xizmati sozlanganini tekshiring.",aiPrivacy:"Tahlil uchun faqat tanlangan panorama serveringizdagi mahalliy Ollama modeliga yuboriladi.",showOriginal:"Asl rasmni ko‘rish",showEdited:"Tahrirlangan rasmga qaytish",saveCopy:"Tahrirlangan nusxani loyihaga saqlash",savingCopy:"Loyihaga saqlanmoqda…",savedCopy:"Tahrirlangan nusxa loyiha kutubxonasiga saqlandi",saveCopyFailed:"Tahrirlangan nusxani loyihaga saqlab bo‘lmadi."},
 ru:{title:"Просмотр панорамы 360°",invalid:"Выберите изображение JPG, PNG или WebP.",readError:"Не удалось прочитать выбранное изображение.",back:"Назад",import:"Выбрать панорамное изображение",hint:"JPG, PNG или WebP. Для сферической панорамы рекомендуется соотношение 2:1.",empty:"Панорама ещё не выбрана",ratio:"Соотношение сторон",resolution:"Разрешение",status:"Проверка",pass:"Подходит для просмотра 360°",warn:"Соотношение не 2:1 — панорама может отображаться некорректно",low:"Низкое разрешение — рекомендуется исходник более высокого качества",ready:"Панорама сохранена на сервере. Исходный файл не изменяется.",replace:"Выбрать другое изображение",uploading:"Загрузка…",failed:"Не удалось загрузить файл на сервер.",chooseProject:"Сначала выберите проект",project:"Проект",files:"Сохранённые панорамы",noFiles:"В этом проекте пока нет панорам",saved:"Сохранено на сервере",uploadHint:"Файл будет привязан к проекту и сохранён на сервере.",adjustments:"Настройки изображения",brightness:"Яркость",contrast:"Контраст",saturation:"Насыщенность",saveEdits:"Сохранить настройки",resetEdits:"Сбросить",savingEdits:"Сохранение…",savedEdits:"Настройки сохранены",exportImage:"Экспортировать изображение",exporting:"Экспорт…",exported:"Изображение скачано",exportFailed:"Не удалось экспортировать изображение",seamOffset:"Положение шва (°)",seamHint:"Перемещает шов панорамы в другое место; не выполняет автоматическое восстановление шва.",seamAnalysis:"Непрерывность шва (оценка)",seamLow:"Небольшая разница цветов на границе.",seamMedium:"Заметная разница цветов на границе.",seamHigh:"Большая разница цветов на границе.",seamDisclaimer:"Автоматическая оценка сравнивает только левый и правый края изображения. Она не обнаруживает внутренние швы, параллакс и дублирование объектов.",seamBlendPercent:"Смягчение шва (%)",seamBlendHint:"Плавно смешивает цвета у границы. Слишком большое значение может размыть объекты.",autoSeam:"Найти наиболее спокойное место шва",findingSeam:"Анализ…",autoSeamHint:"Сравнивает вертикальные линии изображения и выбирает место с наименьшим изменением цвета. Это приблизительная оценка.",autoSeamFailed:"Не удалось найти подходящее место шва.",aiAnalyze:"Анализировать панораму с помощью ИИ",aiAnalyzing:"ИИ анализирует…",aiTitle:"Результат анализа ИИ",aiFailed:"Не удалось выполнить анализ ИИ. Проверьте настройку локального сервиса Ollama.",aiPrivacy:"Для анализа выбранная панорама отправляется только в локальную модель Ollama на вашем сервере.",showOriginal:"Показать оригинал",showEdited:"Вернуться к обработанной версии",saveCopy:"Сохранить копию в проект",savingCopy:"Сохранение в проект…",savedCopy:"Изменённая копия сохранена в библиотеку проекта",saveCopyFailed:"Не удалось сохранить копию в проект."},
 en:{title:"360° panorama viewer",invalid:"Please select a JPG, PNG or WebP image.",readError:"The selected image could not be read.",back:"Back",import:"Choose panorama image",hint:"JPG, PNG or WebP. A 2:1 ratio is recommended for a full spherical panorama.",empty:"No panorama selected yet",ratio:"Aspect ratio",resolution:"Resolution",status:"Validation",pass:"Suitable for 360° viewing",warn:"Not a 2:1 ratio — the panorama may display incorrectly",low:"Low resolution — a higher-quality source is recommended",ready:"Panorama saved to the server. The original file remains unchanged.",replace:"Choose another image",uploading:"Uploading…",failed:"Could not upload the file to the server.",chooseProject:"Select a project first",project:"Project",files:"Saved panoramas",noFiles:"This project has no panoramas yet",saved:"Saved on server",uploadHint:"The file will be linked to this project and stored on the server.",adjustments:"Image adjustments",brightness:"Brightness",contrast:"Contrast",saturation:"Saturation",saveEdits:"Save adjustments",resetEdits:"Reset",savingEdits:"Saving…",savedEdits:"Adjustments saved",exportImage:"Export edited image",exporting:"Exporting…",exported:"Edited image downloaded",exportFailed:"Could not export the image",seamOffset:"Seam position (°)",seamHint:"Moves the panorama seam to another direction; it does not automatically repair stitching defects.",seamAnalysis:"Seam continuity (estimate)",seamLow:"Low color difference at the boundary.",seamMedium:"Noticeable color difference at the boundary.",seamHigh:"Large color difference at the boundary.",seamDisclaimer:"This automatic estimate compares only the left and right image edges. It does not detect internal seams, parallax, or ghosted objects.",seamBlendPercent:"Seam feather (%)",seamBlendHint:"Gradually blends colours across the outer edge. A high value may soften objects near the seam.",autoSeam:"Find lowest-contrast seam",findingSeam:"Analyzing…",autoSeamHint:"Compares vertical image lines and selects the position with the smallest colour change. This is an estimate.",autoSeamFailed:"Could not find a suitable seam position.",aiAnalyze:"Analyze panorama with AI",aiAnalyzing:"AI is analyzing…",aiTitle:"AI analysis",aiFailed:"AI analysis failed. Check that the local Ollama service is configured.",aiPrivacy:"Only the selected panorama is sent to the local Ollama model configured on your server.",showOriginal:"Show original",showEdited:"Back to edited preview",saveCopy:"Save edited copy to project",savingCopy:"Saving to project…",savedCopy:"Edited copy saved to the project library",saveCopyFailed:"Could not save the edited copy to the project."}
};
async function findLowContrastSeam(source:string):Promise<number|null>{
 return new Promise(resolve=>{
  const image=new Image();
  image.onload=()=>{
   try{
    if(Math.abs(image.naturalWidth/image.naturalHeight-2)>=0.02){resolve(null);return;}
    const scale=Math.min(1,1024/image.naturalWidth,512/image.naturalHeight);
    const width=Math.max(2,Math.round(image.naturalWidth*scale));
    const height=Math.max(2,Math.round(image.naturalHeight*scale));
    const canvas=document.createElement("canvas");canvas.width=width;canvas.height=height;
    const context=canvas.getContext("2d",{willReadFrequently:true});if(!context){resolve(null);return;}
    context.drawImage(image,0,0,width,height);const pixels=context.getImageData(0,0,width,height).data;
    const firstRow=Math.floor(height*0.08),lastRow=Math.max(firstRow+1,Math.ceil(height*0.92));
    let bestCost=Infinity,bestX=0;
    for(let x=0;x<width;x++){
     const leftX=(x+width-1)%width;let total=0,count=0;
     for(let y=firstRow;y<Math.min(lastRow,height);y++){
      const left=(y*width+leftX)*4,right=(y*width+x)*4;
      total+=(Math.abs(pixels[left]-pixels[right])+Math.abs(pixels[left+1]-pixels[right+1])+Math.abs(pixels[left+2]-pixels[right+2]))/3;count++;
     }
     const cost=count?total/count:Infinity;if(cost<bestCost){bestCost=cost;bestX=x;}
    }
    resolve(Math.min(359,Math.round(bestX/width*360)));
   }catch{resolve(null);}
  };
  image.onerror=()=>resolve(null);image.src=source;
 });
}

function featherPanoramaSeam(canvas:HTMLCanvasElement,percent:number){
 const band=Math.min(Math.floor(canvas.width/2),Math.round(canvas.width*Math.min(5,Math.max(0,percent))/100));
 if(band<1)return;
 const context=canvas.getContext("2d");if(!context)return;
 const leftFrame=context.getImageData(0,0,band,canvas.height);
 const rightFrame=context.getImageData(canvas.width-band,0,band,canvas.height);
 const leftPixels=leftFrame.data;const rightPixels=rightFrame.data;
 for(let y=0;y<canvas.height;y++){
  for(let x=0;x<band;x++){
   const alpha=0.5*(1-x/band);
   const left=(y*band+x)*4;const right=(y*band+(band-1-x))*4;
   for(let channel=0;channel<3;channel++){
    const leftValue=leftPixels[left+channel];const rightValue=rightPixels[right+channel];
    leftPixels[left+channel]=Math.round(leftValue*(1-alpha)+rightValue*alpha);
    rightPixels[right+channel]=Math.round(rightValue*(1-alpha)+leftValue*alpha);
   }
  }
 }
 context.putImageData(leftFrame,0,0);
 context.putImageData(rightFrame,canvas.width-band,0);
}

export default function MediaStudio({ token, language, projectId, projectName, projects, onBack, onSelectProject }: Props) {
 const t=copy[language]; const host=useRef<HTMLDivElement>(null); const patchCanvasRef=useRef<HTMLCanvasElement|null>(null);
 const [url,setUrl]=useState<string|null>(null); const [meta,setMeta]=useState<{width:number;height:number;name:string}|null>(null);
 const [assets,setAssets]=useState<Asset[]>([]); const [error,setError]=useState(""); const [uploading,setUploading]=useState(false); const [saved,setSaved]=useState(false); const [settings,setSettings]=useState<EditSettings>({brightness:1,contrast:1,saturation:1,seamOffset:0,seamBlend:0}); const [previewUrl,setPreviewUrl]=useState<string|null>(null); const [savingSettings,setSavingSettings]=useState(false); const [settingsMessage,setSettingsMessage]=useState(""); const [exporting,setExporting]=useState(false); const [exportMessage,setExportMessage]=useState(""); const [seamReport,setSeamReport]=useState<SeamReport|null>(null); const [findingSeam,setFindingSeam]=useState(false); const [savingCopy,setSavingCopy]=useState(false); const [showOriginal,setShowOriginal]=useState(false); const [selectedMediaId,setSelectedMediaId]=useState<string|null>(null); const [analyzingAI,setAnalyzingAI]=useState(false); const [aiAnalysis,setAiAnalysis]=useState("");
 async function analyzeSeam(source:string):Promise<SeamReport|null>{return new Promise(resolve=>{const image=new Image();image.onload=()=>{try{if(Math.abs(image.naturalWidth/image.naturalHeight-2)>=0.02){resolve(null);return;}const scale=Math.min(1,2048/image.naturalWidth,1024/image.naturalHeight);const width=Math.max(2,Math.round(image.naturalWidth*scale));const height=Math.max(2,Math.round(image.naturalHeight*scale));const canvas=document.createElement("canvas");canvas.width=width;canvas.height=height;const context=canvas.getContext("2d",{willReadFrequently:true});if(!context){resolve(null);return;}context.drawImage(image,0,0,width,height);const pixels=context.getImageData(0,0,width,height).data;let total=0,count=0;const firstRow=Math.floor(height*0.08),lastRow=Math.ceil(height*0.92);for(let y=firstRow;y<lastRow;y++){const left=y*width*4,right=(y*width+width-1)*4;total+=(Math.abs(pixels[left]-pixels[right])+Math.abs(pixels[left+1]-pixels[right+1])+Math.abs(pixels[left+2]-pixels[right+2]))/3;count++;}const score=count?total/count:0;resolve({score,level:score<20?"low":score<45?"medium":"high"});}catch{resolve(null);}};image.onerror=()=>resolve(null);image.src=source;});}
 async function analyzeWithAI(){if(!selectedMediaId||analyzingAI)return;setAnalyzingAI(true);setAiAnalysis("");setError("");try{const response=await fetch("/api/ai/assist",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token},body:JSON.stringify({role:"panorama_quality",prompt:language==="uz"?"Ushbu 360° panoramani tahlil qil. Ko‘rinadigan chok, rang va yorug‘lik nomutanosibligi, buzilishlar va sifat muammolarini aniqlab, xavfsiz tahrir tavsiyalarini ber.":language==="ru"?"Проанализируй эту панораму 360°: видимые швы, различия цвета и экспозиции, искажения и проблемы качества. Дай безопасные рекомендации по редактированию.":"Analyze this 360° panorama for visible seams, colour and exposure mismatch, distortions and quality issues. Give safe editing recommendations.",context:meta?("Image dimensions: "+meta.width+"x"+meta.height+". Current edge seam estimate: "+(seamReport?seamReport.score.toFixed(1)+"/255":"not available")+"; do not assume this measures internal seams."):"",language,media_id:selectedMediaId})});const data=await response.json();if(!response.ok)throw new Error(data.detail||t.aiFailed);setAiAnalysis(data.output||t.aiFailed);}catch{setError(t.aiFailed);}finally{setAnalyzingAI(false);}}
 async function autoLocateSeam(){if(!url||findingSeam)return;setFindingSeam(true);setError("");try{const angle=await findLowContrastSeam(url);if(angle===null)throw new Error();setSettings(current=>({...current,seamOffset:angle}));}catch{setError(t.autoSeamFailed);}finally{setFindingSeam(false);}}
 async function loadAssets(id:string){try{const r=await fetch(`/api/projects/${id}/media`, { headers: { Authorization: `Bearer ${token}` } });if(!r.ok)throw new Error();setAssets((await r.json()).filter((asset:Asset)=>asset.contentType.startsWith("image/")));setError("");}catch{setError(t.failed);}}
 async function loadEditorSettings(id:string){try{const r=await fetch(`/api/projects/${id}/editor-settings`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw new Error();const data=await r.json();setSettings({brightness:data.brightness??1,contrast:data.contrast??1,saturation:data.saturation??1,seamOffset:data.seam_offset??0,seamBlend:data.seam_blend_percent??0});}catch{setSettings({brightness:1,contrast:1,saturation:1,seamOffset:0,seamBlend:0});}}
 async function saveEditorSettings(){if(!projectId||savingSettings)return;setSavingSettings(true);setSettingsMessage("");try{const r=await fetch(`/api/projects/${projectId}/editor-settings`,{method:"PUT",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},body:JSON.stringify({...settings,seam_offset:settings.seamOffset,seam_blend_percent:settings.seamBlend})});if(!r.ok)throw new Error();setSettingsMessage(t.savedEdits);}catch{setError(t.failed);}finally{setSavingSettings(false);}}
 async function renderEditedBlob():Promise<Blob>{
  if(!url)throw new Error("No panorama selected");
  const response=await fetch(url);if(!response.ok)throw new Error("Could not read panorama");
  const source=await createImageBitmap(await response.blob());
  const canvas=document.createElement("canvas");canvas.width=source.width;canvas.height=source.height;
  const context=canvas.getContext("2d");if(!context)throw new Error("Canvas unavailable");
  context.filter="brightness("+settings.brightness+") contrast("+settings.contrast+") saturate("+settings.saturation+")";
  context.drawImage(source,0,0);
  const repairLayer=patchCanvasRef.current;if(repairLayer&&repairLayer.width===source.width&&repairLayer.height===source.height)context.drawImage(repairLayer,0,0);
  source.close();
  let outputCanvas:HTMLCanvasElement=canvas;
  if(settings.seamOffset>0){
   const shift=Math.round(canvas.width*settings.seamOffset/360);
   const shifted=document.createElement("canvas");shifted.width=canvas.width;shifted.height=canvas.height;
   const shiftedContext=shifted.getContext("2d");if(!shiftedContext)throw new Error("Canvas unavailable");
   shiftedContext.drawImage(canvas,-shift,0);shiftedContext.drawImage(canvas,canvas.width-shift,0);outputCanvas=shifted;
  }
  featherPanoramaSeam(outputCanvas,settings.seamBlend);
  const output=await new Promise<Blob|null>(resolve=>outputCanvas.toBlob(resolve,"image/jpeg",0.95));
  if(!output)throw new Error("Could not encode panorama");
  return output;
 }
 async function exportEditedImage(){if(!url||!meta||exporting)return;setExporting(true);setExportMessage("");try{const output=await renderEditedBlob();const outputUrl=URL.createObjectURL(output);const link=document.createElement("a");link.href=outputUrl;link.download=meta.name.replace(/\.[^.]+$/,"") + "-edited.jpg";document.body.appendChild(link);link.click();link.remove();window.setTimeout(()=>URL.revokeObjectURL(outputUrl),1000);setExportMessage(t.exported);}catch{setError(t.exportFailed);}finally{setExporting(false);}}
 async function saveEditedCopy(){if(!url||!meta||!projectId||savingCopy)return;setSavingCopy(true);setExportMessage("");try{const output=await renderEditedBlob();const fileName=meta.name.replace(/\.[^.]+$/,"") + "-edited.jpg";const body=new FormData();body.append("file",output,fileName);const response=await fetch("/api/projects/"+projectId+"/media",{method:"POST",headers:{Authorization:"Bearer "+token},body});if(!response.ok)throw new Error();const asset:Asset=await response.json();setAssets(current=>[asset,...current.filter(item=>item.id!==asset.id)]);setExportMessage(t.savedCopy);}catch{setError(t.saveCopyFailed);}finally{setSavingCopy(false);}}
 useEffect(()=>{setUrl(null);setMeta(null);setAssets([]);setSeamReport(null);setSelectedMediaId(null);setAiAnalysis("");setSettingsMessage("");if(projectId){void loadAssets(projectId);void loadEditorSettings(projectId);}},[projectId]);
 useEffect(()=>()=>{if(url?.startsWith("blob:"))URL.revokeObjectURL(url);},[url]);
 useEffect(()=>{setShowOriginal(false);},[url]);
 useEffect(()=>{setShowOriginal(false);},[settings]);
 useEffect(()=>{
  let cancelled=false;let generatedUrl:string|null=null;
  setPreviewUrl(null);
  if(!url||(settings.seamOffset===0&&settings.seamBlend===0))return;
  const image=new Image();
  image.onload=()=>{
   const canvas=document.createElement("canvas");canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
   const context=canvas.getContext("2d");if(!context)return;
   if(settings.seamOffset>0){const shift=Math.round(canvas.width*settings.seamOffset/360);context.drawImage(image,-shift,0);context.drawImage(image,canvas.width-shift,0);}else{context.drawImage(image,0,0);}
   featherPanoramaSeam(canvas,settings.seamBlend);
   canvas.toBlob(blob=>{
    if(cancelled||!blob)return;
    generatedUrl=URL.createObjectURL(blob);setPreviewUrl(generatedUrl);
   },"image/jpeg",0.95);
  };
  image.onerror=()=>{if(!cancelled)setError(t.readError);};
  image.src=url;
  return()=>{cancelled=true;if(generatedUrl)URL.revokeObjectURL(generatedUrl);};
 },[url,settings.seamOffset,settings.seamBlend]);
 useEffect(()=>{if(!url||!host.current)return;const viewer=new Viewer({container:host.current,panorama:showOriginal?url:(previewUrl||url),navbar:["zoom","move","fullscreen"]});return()=>viewer.destroy();},[url,previewUrl,showOriginal]);
 useEffect(()=>{if(host.current)host.current.style.filter=showOriginal?"none":`brightness(${settings.brightness}) contrast(${settings.contrast}) saturate(${settings.saturation})`;},[settings,url,showOriginal]);
 async function showAsset(asset:Asset){try{const response=await fetch(asset.url,{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error();const blob=await response.blob();const fileUrl=URL.createObjectURL(blob);const image=new Image();image.onload=()=>{setMeta({width:image.naturalWidth,height:image.naturalHeight,name:asset.name});setUrl(fileUrl);setSaved(true);setSelectedMediaId(asset.id);setAiAnalysis("");setError("");void analyzeSeam(fileUrl).then(setSeamReport);};image.onerror=()=>{URL.revokeObjectURL(fileUrl);setError(t.readError);};image.src=fileUrl;}catch{setError(t.failed);}}
 async function choose(file?:File){
  if(!file)return;
  if(!["image/jpeg","image/png","image/webp"].includes(file.type)){setError(t.invalid);return;}
  if(!projectId){setError(t.chooseProject);return;}
  const localUrl=URL.createObjectURL(file);const image=new Image();
  image.onload=async()=>{
   setMeta({width:image.naturalWidth,height:image.naturalHeight,name:file.name});setUrl(localUrl);setSaved(false);setUploading(true);setError("");setSeamReport(null);setSeamReport(await analyzeSeam(localUrl));
   try{const body=new FormData();body.append("file",file);const response=await fetch(`/api/projects/${projectId}/media`,{method:"POST",headers:{Authorization:`Bearer ${token}`},body});if(!response.ok)throw new Error();const asset:Asset=await response.json();setSelectedMediaId(asset.id);setAiAnalysis("");const protectedFile=await fetch(asset.url,{headers:{Authorization:`Bearer ${token}`}});if(!protectedFile.ok)throw new Error();const storedBlob=await protectedFile.blob();URL.revokeObjectURL(localUrl);setAssets(current=>[asset,...current.filter(a=>a.id!==asset.id)]);setUrl(URL.createObjectURL(storedBlob));setMeta({width:image.naturalWidth,height:image.naturalHeight,name:asset.name});setSaved(true);}
   catch{setError(t.failed);}
   finally{setUploading(false);}
  };
  image.onerror=()=>{URL.revokeObjectURL(localUrl);setError(t.readError);};image.src=localUrl;
 }
 const valid=!!meta&&Math.abs(meta.width/meta.height-2)<.02; const hasEdits=settings.brightness!==1||settings.contrast!==1||settings.saturation!==1||settings.seamOffset!==0||settings.seamBlend!==0;
 return <section className="media-studio">
  <div className="media-head"><div><div className="eyebrow muted">MEDIA WORKSPACE · SERVER STORAGE</div><h2>{t.title}</h2></div><button className="secondary" onClick={onBack}>{t.back}</button></div>
  {!projectId?<div className="media-empty"><strong>{t.chooseProject}</strong><select className="project-picker" defaultValue="" onChange={e=>{const p=projects.find(x=>x.id===e.target.value);if(p)onSelectProject(p);}}><option value="" disabled>{t.project}</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></div>:<>
   <div className="media-project-label">{t.project}: <strong>{projectName}</strong></div>
   <div className="media-toolbar"><label className="primary upload-button">＋ {url?t.replace:t.import}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>choose(e.target.files?.[0])}/></label><span>{t.hint}</span></div>
   <div className="media-upload-note">{uploading?t.uploading:t.uploadHint}</div>
   {url&&meta&&<div className="editor-controls"><h3>{t.adjustments}</h3><label>{t.brightness}<input type="range" min="0.5" max="1.5" step="0.05" value={settings.brightness} onChange={e=>setSettings(v=>({...v,brightness:Number(e.target.value)}))}/><span>{settings.brightness.toFixed(2)}</span></label><label>{t.contrast}<input type="range" min="0.5" max="1.5" step="0.05" value={settings.contrast} onChange={e=>setSettings(v=>({...v,contrast:Number(e.target.value)}))}/><span>{settings.contrast.toFixed(2)}</span></label><label>{t.saturation}<input type="range" min="0" max="2" step="0.05" value={settings.saturation} onChange={e=>setSettings(v=>({...v,saturation:Number(e.target.value)}))}/><span>{settings.saturation.toFixed(2)}</span></label><label>{t.seamOffset}<input type="range" min="0" max="359" step="1" value={settings.seamOffset} disabled={!valid} onChange={e=>setSettings(v=>({...v,seamOffset:Number(e.target.value)}))}/><span>{settings.seamOffset}°</span></label><small>{t.seamHint}</small><button className="secondary" disabled={!valid||findingSeam} onClick={()=>void autoLocateSeam()}>{findingSeam?t.findingSeam:t.autoSeam}</button><small>{t.autoSeamHint}</small><label>{t.seamBlendPercent}<input type="range" min="0" max="5" step="0.5" value={settings.seamBlend} disabled={!valid} onChange={e=>setSettings(v=>({...v,seamBlend:Number(e.target.value)}))}/><span>{settings.seamBlend.toFixed(1)}%</span></label><small>{t.seamBlendHint}</small><div className="editor-actions"><button className="secondary" disabled={!selectedMediaId||analyzingAI} onClick={()=>void analyzeWithAI()}>{analyzingAI?t.aiAnalyzing:t.aiAnalyze}</button></div><small>{t.aiPrivacy}</small>{aiAnalysis&&<div className="media-ai-report"><h3>{t.aiTitle}</h3><p>{aiAnalysis}</p></div>}<div className="editor-actions"><button className="primary" disabled={savingSettings} onClick={()=>void saveEditorSettings()}>{savingSettings?t.savingEdits:t.saveEdits}</button><button className="secondary" onClick={()=>{setSettings({brightness:1,contrast:1,saturation:1,seamOffset:0,seamBlend:0});setShowOriginal(false);setSettingsMessage("");}}>{t.resetEdits}</button><button className="secondary" disabled={savingCopy||exporting} onClick={()=>void saveEditedCopy()}>{savingCopy?t.savingCopy:t.saveCopy}</button><button className="secondary" disabled={exporting||savingCopy} onClick={()=>void exportEditedImage()}>{exporting?t.exporting:t.exportImage}</button></div>{settingsMessage&&<p className="media-success">✓ {settingsMessage}</p>}{exportMessage&&<p className="media-success">✓ {exportMessage}</p>}</div>}
   {error&&<div className="media-alert">{error}</div>}
   {url&&meta?<><div className="panorama-viewer" ref={host}/><PanoramaRepairCanvas imageUrl={url} language={language} patchCanvasRef={patchCanvasRef}/>{hasEdits&&<div className="editor-actions"><button className="secondary" onClick={()=>setShowOriginal(value=>!value)}>{showOriginal?t.showEdited:t.showOriginal}</button></div>}<div className="media-report"><div><span>{t.resolution}</span><strong>{meta.width} × {meta.height}</strong></div><div><span>{t.ratio}</span><strong>{(meta.width/meta.height).toFixed(2)}:1</strong></div><div><span>{t.status}</span><strong className={valid?"good":"warning"}>{valid?t.pass:t.warn}</strong></div></div>{seamReport&&<div className="media-seam-report"><strong>{t.seamAnalysis}: {seamReport.score.toFixed(1)}/255</strong><p className={seamReport.level==="low"?"media-success":"media-warning"}>{seamReport.level==="low"?t.seamLow:seamReport.level==="medium"?t.seamMedium:t.seamHigh}</p><small>{t.seamDisclaimer}</small></div>}{meta.width<4000&&<p className="media-warning">{t.low}</p>}{saved&&<p className="media-success">✓ {t.ready} <span>· {meta.name}</span></p>}{!saved&&!uploading&&<p className="media-warning">{language==="uz"?"Hozircha faqat ko‘rish uchun ochildi, serverga saqlanmadi.":language==="ru"?"Пока открыто только для просмотра и не сохранено на сервере.":"Preview only; this file has not been saved to the server."}</p>}</>:<div className="media-empty"><div>360°</div><strong>{t.empty}</strong><span>{t.hint}</span></div>}
   <div className="saved-media"><h3>{t.files}</h3>{assets.length===0?<p>{t.noFiles}</p>:<div className="saved-media-list">{assets.map(asset=><button key={asset.id} className="saved-media-item" onClick={()=>showAsset(asset)}><span>360°</span><strong>{asset.name}</strong><small>{(asset.sizeBytes/1024/1024).toFixed(1)} MB · {t.saved}</small></button>)}</div>}</div>
  </>}
 </section>;
}
