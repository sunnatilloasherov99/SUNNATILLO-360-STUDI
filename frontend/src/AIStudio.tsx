import { useEffect, useState } from "react";
import type { Language } from "./i18n";

type Role = "panorama_quality" | "tour_planner" | "tour_description" | "stitching_advisor";
type Asset={id:string;name:string;contentType:string};
type Props = { token: string; language: Language; projectId?: string; onBack: () => void };

const labels = {
 uz: {
  title:"AI mutaxassislar jamoasi",subtitle:"Mahalliy AI yordamchilari — ixtiyoriy va maxfiy",
  roles:"Mutaxassisni tanlang",prompt:"Vazifangiz yoki savolingiz",context:"Qo‘shimcha matnli ma’lumot (ixtiyoriy)",
  run:"AI dan javob olish",working:"AI ishlamoqda…",result:"AI javobi",back:"Orqaga",
  noProvider:"Mahalliy AI ulanmagan. Bepul Ollama dasturini serverga o‘rnating va OLLAMA_BASE_URL sozlamasini kiriting.",
  textOnly:"Maxfiylik: faqat shu oynada yozgan matningiz va ixtiyoriy tanlagan rasmingiz yuboriladi. Hech narsa avtomatik tanlanmaydi.",imageOptional:"Tahlil uchun panorama tanlang (ixtiyoriy)",imageConsent:"Rasm faqat «AI dan javob olish» tugmasini bosganingizda mahalliy Ollama modeliga yuboriladi. Rasm tahlili uchun vision model kerak.",
  provider:"Mahalliy Ollama modeli",ready:"Ulangan",offline:"Sozlanmagan",
  panorama_quality:["360° sifat tahlilchisi","Panorama sifati, o‘lcham va tikuv muammolari bo‘yicha maslahat."],
  tour_planner:["Virtual tur rejissyori","Sahnalar ketma-ketligi va qulay navigatsiya rejasini tuzish."],
  tour_description:["Tavsif yozuvchi","Virtual tur sahnalari uchun professional tavsif tayyorlash."],
  stitching_advisor:["Stitching mutaxassisi","Choklar, parallaks va yorug‘lik farqlarini tuzatish bo‘yicha maslahat."]
 },
 ru: {
  title:"Команда AI-специалистов",subtitle:"Локальные AI-помощники — по желанию и конфиденциально",
  roles:"Выберите специалиста",prompt:"Задача или вопрос",context:"Дополнительный текстовый контекст (необязательно)",
  run:"Получить ответ AI",working:"AI работает…",result:"Ответ AI",back:"Назад",
  noProvider:"Локальный AI не подключён. Установите бесплатный Ollama на сервер и задайте OLLAMA_BASE_URL.",
  textOnly:"Конфиденциальность: отправляется только введённый текст и выбранное вами изображение. Ничего не выбирается автоматически.",imageOptional:"Выберите панораму для анализа (необязательно)",imageConsent:"Изображение отправляется локальной модели Ollama только после нажатия кнопки. Для анализа нужен vision-модель.",
  provider:"Локальная модель Ollama",ready:"Подключено",offline:"Не настроено",
  panorama_quality:["Аналитик качества 360°","Советы по качеству панорамы, разрешению и дефектам."],
  tour_planner:["Режиссёр виртуального тура","Порядок сцен и удобная навигация для посетителей."],
  tour_description:["Автор описаний","Профессиональные описания для сцен виртуального тура."],
  stitching_advisor:["Специалист по склейке","Советы по швам, параллаксу и разнице экспозиции."]
 },
 en: {
  title:"AI specialist team",subtitle:"Optional, private local AI assistants",
  roles:"Choose a specialist",prompt:"Your task or question",context:"Additional text context (optional)",
  run:"Ask AI",working:"AI is working…",result:"AI response",back:"Back",
  noProvider:"Local AI is not connected. Install free Ollama on the server and set OLLAMA_BASE_URL.",
  textOnly:"Privacy: only the text you enter and an image you explicitly select are sent. Nothing is selected automatically.",imageOptional:"Choose a panorama to analyze (optional)",imageConsent:"The image is sent to your local Ollama model only when you press Ask AI. A vision-capable model is required for image analysis.",
  provider:"Local Ollama model",ready:"Connected",offline:"Not configured",
  panorama_quality:["360° quality analyst","Advice on panorama quality, resolution and defects."],
  tour_planner:["Virtual tour planner","Plan scene order and visitor navigation."],
  tour_description:["Scene description writer","Create professional descriptions for tour scenes."],
  stitching_advisor:["Stitching specialist","Advice on seams, parallax and exposure mismatch."]
 }
};
const roleIds:Role[]=["panorama_quality","tour_planner","tour_description","stitching_advisor"];

export default function AIStudio({token,language,projectId,onBack}:Props){
 const t=labels[language];
 const [role,setRole]=useState<Role>("panorama_quality");
 const [prompt,setPrompt]=useState("");
 const [context,setContext]=useState("");
 const [output,setOutput]=useState("");
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 const [configured,setConfigured]=useState(false);
 const [model,setModel]=useState("llama3.2");
 const [assets,setAssets]=useState<Asset[]>([]);
 const [mediaId,setMediaId]=useState("");
 useEffect(()=>{
  let cancelled=false;
  fetch("/api/ai/capabilities",{headers:{Authorization:`Bearer ${token}`}})
   .then(r=>r.ok?r.json():Promise.reject())
   .then(data=>{if(!cancelled){const provider=data.providers?.find((item:{id:string;configured?:boolean;model?:string})=>item.id==="ollama");setConfigured(!!provider?.configured);if(provider?.model)setModel(provider.model);}})
   .catch(()=>{if(!cancelled)setConfigured(false);});
  return()=>{cancelled=true;};
 },[token]);
 useEffect(()=>{
  let cancelled=false;
  setAssets([]);setMediaId("");
  if(!projectId)return;
  fetch(`/api/projects/${projectId}/media`,{headers:{Authorization:`Bearer ${token}`}})
   .then(r=>r.ok?r.json():Promise.reject())
   .then(data=>{if(!cancelled)setAssets((Array.isArray(data)?data:[]).filter((asset:Asset)=>asset.contentType.startsWith("image/")));})
   .catch(()=>{if(!cancelled)setAssets([]);});
  return()=>{cancelled=true;};
 },[token,projectId]);
 async function ask(){
  if(!prompt.trim()||busy)return;
  setBusy(true);setError("");setOutput("");
  try{
   const response=await fetch("/api/ai/assist",{
    method:"POST",
    headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},
    body:JSON.stringify({role,prompt:prompt.trim(),context:context.trim(),language,media_id:mediaId||null})
   });
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw new Error(data.detail||t.noProvider);
   setOutput(data.output||"");
  }catch(e){setError(e instanceof Error?e.message:t.noProvider);}
  finally{setBusy(false);}
 }
 return <section className="ai-studio">
  <div className="media-head"><div><div className="eyebrow muted">SUNNATILLO 360° STUDIO · AI TEAM</div><h2>{t.title}</h2><p>{t.subtitle}</p></div><button className="secondary" onClick={onBack}>{t.back}</button></div>
  <div className="ai-provider-row"><span>{t.provider}: <strong>{model}</strong></span><span className={configured?"quality-pass":"quality-warning"}>{configured?t.ready:t.offline}</span></div>
  {!configured&&<div className="media-warning">{t.noProvider}</div>}
  <div className="ai-role-grid">{roleIds.map(id=><button key={id} className={`ai-role-card ${role===id?"selected":""}`} onClick={()=>setRole(id)}><strong>{t[id][0]}</strong><span>{t[id][1]}</span></button>)}</div>
  <div className="ai-prompt-panel">
   <label className="field-label">{t.prompt}<textarea rows={3} value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder={language==="uz"?"Masalan: 360° turim uchun 5 ta sahna tartibini tavsiya qil…":language==="ru"?"Например: предложи порядок из 5 сцен для моего тура…":"For example: suggest a 5-scene order for my virtual tour…"}/></label>
   {projectId&&<label className="field-label">{t.imageOptional}<select value={mediaId} onChange={e=>setMediaId(e.target.value)}><option value="">{language==="uz"?"Rasm yubormaslik":language==="ru"?"Не отправлять изображение":"Do not send an image"}</option>{assets.map(asset=><option key={asset.id} value={asset.id}>{asset.name}</option>)}</select><small>{t.imageConsent}</small></label>}
   <label className="field-label">{t.context}<textarea rows={3} value={context} onChange={e=>setContext(e.target.value)} placeholder={language==="uz"?"Faqat yuborishga rozilik bergan matnni kiriting…":language==="ru"?"Введите только тот текст, которым готовы поделиться…":"Enter only text you explicitly want to share…"}/></label>
   <p className="privacy-inline">{t.textOnly}</p>
   <button className="primary" disabled={!prompt.trim()||busy||!configured} onClick={()=>void ask()}>{busy?t.working:t.run}</button>
  </div>
  {error&&<div className="media-alert">{error}</div>}
  {output&&<div className="ai-output"><h3>{t.result}</h3><div>{output}</div></div>}
 </section>;
}
