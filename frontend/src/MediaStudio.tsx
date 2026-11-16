import { useEffect, useRef, useState } from "react";
import { Viewer } from "@photo-sphere-viewer/core";
import "@photo-sphere-viewer/core/index.css";

type Props = { language: "uz" | "ru" | "en"; onBack: () => void };
const copy = {
  uz: { title:"360° panorama ko‘ruvchi", invalid:"Faqat rasm fayllarini tanlang.", readError:"Tanlangan rasmni o‘qib bo‘lmadi.", back:"Loyihaga qaytish", import:"Panorama rasmini tanlash", hint:"JPG, PNG yoki WebP. To‘liq sferik panorama uchun 2:1 nisbat tavsiya etiladi.", empty:"Hozircha panorama tanlanmagan", ratio:"Rasm nisbati", resolution:"O‘lchami", status:"Tekshiruv", pass:"360° ko‘rish uchun mos", warn:"Nisbat 2:1 emas — panorama noto‘g‘ri ko‘rinishi mumkin", low:"Aniqlik past — yuqori sifatli manba tavsiya etiladi", ready:"Panorama yuklandi. Asl fayl o‘zgartirilmaydi.", replace:"Boshqa rasm tanlash" },
  ru: { title:"Просмотр панорамы 360°", invalid:"Выберите файл изображения.", readError:"Не удалось прочитать выбранное изображение.", back:"Вернуться к проекту", import:"Выбрать панорамное изображение", hint:"JPG, PNG или WebP. Для сферической панорамы рекомендуется соотношение 2:1.", empty:"Панорама ещё не выбрана", ratio:"Соотношение сторон", resolution:"Разрешение", status:"Проверка", pass:"Подходит для просмотра 360°", warn:"Соотношение не 2:1 — панорама может отображаться некорректно", low:"Низкое разрешение — рекомендуется исходник более высокого качества", ready:"Панорама загружена. Исходный файл не изменяется.", replace:"Выбрать другое изображение" },
  en: { title:"360° panorama viewer", invalid:"Please select an image file.", readError:"The selected image could not be read.", back:"Back to project", import:"Choose panorama image", hint:"JPG, PNG or WebP. A 2:1 ratio is recommended for a full spherical panorama.", empty:"No panorama selected yet", ratio:"Aspect ratio", resolution:"Resolution", status:"Validation", pass:"Suitable for 360° viewing", warn:"Not a 2:1 ratio — the panorama may display incorrectly", low:"Low resolution — a higher-quality source is recommended", ready:"Panorama loaded. The original file remains unchanged.", replace:"Choose another image" }
};
export default function MediaStudio({ language, onBack }: Props) {
  const t = copy[language];
  const host = useRef<HTMLDivElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [meta, setMeta] = useState<{width:number;height:number;name:string}|null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!url || !host.current) return;
    const viewer = new Viewer({ container: host.current, panorama: url, navbar: ["zoom", "move", "fullscreen"] });
    return () => viewer.destroy();
  }, [url]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  function choose(file?: File) {
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError(t.invalid); return; }
    const nextUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      setMeta({ width:image.naturalWidth, height:image.naturalHeight, name:file.name });
      setError("");
      setUrl(previous => { if (previous) URL.revokeObjectURL(previous); return nextUrl; });
    };
    image.onerror = () => { URL.revokeObjectURL(nextUrl); setError(t.readError); };
    image.src = nextUrl;
  }
  const isEquirectangular = !!meta && Math.abs(meta.width / meta.height - 2) < 0.02;
  return <section className="media-studio">
    <div className="media-head"><div><div className="eyebrow muted">MEDIA WORKSPACE · PHASE 1</div><h2>{t.title}</h2></div><button className="secondary" onClick={onBack}>{t.back}</button></div>
    <div className="media-toolbar"><label className="primary upload-button">＋ {url ? t.replace : t.import}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => choose(e.target.files?.[0])}/></label><span>{t.hint}</span></div>
    {error && <div className="media-alert">{error}</div>}
    {url && meta ? <><div className="panorama-viewer" ref={host}/><div className="media-report"><div><span>{t.resolution}</span><strong>{meta.width} × {meta.height}</strong></div><div><span>{t.ratio}</span><strong>{(meta.width/meta.height).toFixed(2)}:1</strong></div><div><span>{t.status}</span><strong className={isEquirectangular ? "good" : "warning"}>{isEquirectangular ? t.pass : t.warn}</strong></div></div>{meta.width < 4000 && <p className="media-warning">{t.low}</p>}<p className="media-success">✓ {t.ready} <span>· {meta.name}</span></p></> : <div className="media-empty"><div>360°</div><strong>{t.empty}</strong><span>{t.hint}</span></div>}
  </section>;
}