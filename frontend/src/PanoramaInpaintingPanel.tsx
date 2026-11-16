import { useEffect, useRef, useState } from "react";

type Language = "uz" | "ru" | "en";
type Props = {
  imageUrl: string;
  token: string;
  language: Language;
  onAccept: (image: Blob) => void;
};

const labels = {
  uz: {
    title: "AI yordamida nuqsonni tiklash",
    intro: "Tiklanishi kerak bo‘lgan joyni oq rangda bo‘yab belgilang. AI faqat belgilangan hududni qayta yaratishga urinadi.",
    brush: "Cho‘tka o‘lchami",
    clear: "Belgini tozalash",
    generate: "AI bilan tiklash",
    working: "AI ishlamoqda…",
    before: "Asl rasm",
    after: "AI natijasi — ko‘rib chiqing",
    accept: "Natijani qabul qilish",
    reject: "Rad etish",
    confirm: "Tanlangan panorama va oq maska serveringizda sozlangan AI tiklash xizmatiga yuboriladi. Davom etasizmi?",
    noMask: "Avval tiklanadigan joyni belgilang.",
    unavailable: "AI tiklash xizmati hozircha sozlanmagan yoki ishlamayapti.",
    privacy: "AI xizmati sozlanmaguncha bu vosita ishlamaydi. Asl rasm qabul qilmaguningizcha o‘zgarmaydi.",
  },
  ru: {
    title: "Восстановление дефекта с помощью ИИ",
    intro: "Закрасьте белым область, которую нужно восстановить. ИИ попытается изменить только отмеченную область.",
    brush: "Размер кисти",
    clear: "Очистить маску",
    generate: "Восстановить с ИИ",
    working: "ИИ обрабатывает…",
    before: "Оригинал",
    after: "Результат ИИ — проверьте",
    accept: "Принять результат",
    reject: "Отклонить",
    confirm: "Выбранная панорама и белая маска будут отправлены в настроенный на вашем сервере сервис ИИ. Продолжить?",
    noMask: "Сначала отметьте область для восстановления.",
    unavailable: "Сервис ИИ-восстановления пока не настроен или недоступен.",
    privacy: "Инструмент недоступен, пока сервис ИИ не настроен. Оригинал не изменится без вашего подтверждения.",
  },
  en: {
    title: "AI defect repair",
    intro: "Paint the area to repair in white. The AI will attempt to regenerate only the masked region.",
    brush: "Brush size",
    clear: "Clear mask",
    generate: "Repair with AI",
    working: "AI is processing…",
    before: "Original",
    after: "AI result — review it",
    accept: "Accept result",
    reject: "Reject",
    confirm: "The selected panorama and white mask will be sent to the AI repair service configured on your server. Continue?",
    noMask: "Mark an area to repair first.",
    unavailable: "The AI inpainting service is not configured or is unavailable.",
    privacy: "This tool remains unavailable until an AI service is configured. The original will not change unless you accept the result.",
  },
};

export default function PanoramaInpaintingPanel({ imageUrl, token, language, onAccept }: Props) {
  const t = labels[language];
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const requestVersion = useRef(0);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [brush, setBrush] = useState(36);
  const [working, setWorking] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [hasMask, setHasMask] = useState(false);
  const [configured, setConfigured] = useState(false);

  useEffect(() => {
    let active = true;
    requestVersion.current += 1;
    const image = new Image();
    image.onload = () => {
      if (!active) return;
      setDimensions({ width: image.naturalWidth, height: image.naturalHeight });
      const canvas = canvasRef.current;
      if (canvas) {
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        const context = canvas.getContext("2d");
        context?.clearRect(0, 0, canvas.width, canvas.height);
      }
    };
    image.onerror = () => {
      if (active) setMessage(t.unavailable);
    };
    image.src = imageUrl;
    void fetch("/api/ai/capabilities", { headers: { Authorization: "Bearer " + token } })
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (active) setConfigured(Boolean(data?.panorama_inpainting?.enabled));
      })
      .catch(() => {
        if (active) setConfigured(false);
      });
    drawing.current = false;
    setWorking(false);
    setHasMask(false);
    setResultUrl(current => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    setMessage("");
    return () => { active = false; requestVersion.current += 1; };
  }, [imageUrl, token, t.unavailable]);

  useEffect(() => () => {
    if (resultUrl) URL.revokeObjectURL(resultUrl);
  }, [resultUrl]);

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const canvas = event.currentTarget;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * canvas.width / rect.width,
      y: (event.clientY - rect.top) * canvas.height / rect.height,
    };
  }

  function paint(event: React.PointerEvent<HTMLCanvasElement>) {
    if (working || !drawing.current) return;
    const canvas = event.currentTarget;
    const context = canvas.getContext("2d");
    if (!context) return;
    const p = point(event);
    setHasMask(true);
    context.fillStyle = "#ffffff";
    context.beginPath();
    context.arc(p.x, p.y, brush * Math.max(1, canvas.width / 1600), 0, Math.PI * 2);
    context.fill();
  }

  async function generate() {
    const canvas = canvasRef.current;
    if (!canvas || working) return;
    if (!hasMask) { setMessage(t.noMask); return; }
    if (!window.confirm(t.confirm)) return;
    const requestId = requestVersion.current;
    const requestedImageUrl = imageUrl;
    setWorking(true);
    setMessage("");
    try {
      // Freeze the exact mask the user confirmed. Further pointer events are
      // ignored while this request is running, so the uploaded mask cannot
      // silently differ from the consent prompt.
      const binaryMask = document.createElement("canvas");
      binaryMask.width = canvas.width;
      binaryMask.height = canvas.height;
      const maskContext = binaryMask.getContext("2d");
      if (!maskContext) throw new Error("Mask canvas unavailable");
      maskContext.fillStyle = "#000000";
      maskContext.fillRect(0, 0, binaryMask.width, binaryMask.height);
      maskContext.drawImage(canvas, 0, 0);
      const maskBlob = await new Promise<Blob>((resolve, reject) =>
        binaryMask.toBlob(blob => blob ? resolve(blob) : reject(new Error("Mask encode failed")), "image/png")
      );

      const sourceResponse = await fetch(requestedImageUrl);
      if (!sourceResponse.ok) throw new Error("Source image unavailable");
      const sourceBlob = await sourceResponse.blob();
      if (requestId !== requestVersion.current) return;

      const form = new FormData();
      form.append("image", sourceBlob, "panorama.jpg");
      form.append("mask", maskBlob, "mask.png");
      form.append("prompt", "Restore the masked area naturally. Preserve the surrounding panorama, geometry, lighting and texture.");
      const response = await fetch("/api/ai/inpaint", {
        method: "POST",
        headers: { Authorization: "Bearer " + token },
        body: form,
      });
      if (!response.ok) throw new Error("Inpainting service unavailable");
      const output = await response.blob();
      if (requestId !== requestVersion.current) return;
      if (!["image/jpeg", "image/png", "image/webp"].includes(output.type)) throw new Error("Invalid AI image response");
      const nextUrl = URL.createObjectURL(output);
      setResultUrl(current => {
        if (current) URL.revokeObjectURL(current);
        return nextUrl;
      });
    } catch {
      if (requestId === requestVersion.current) setMessage(t.unavailable);
    } finally {
      if (requestId === requestVersion.current) setWorking(false);
    }
  }

  return <section className="inpainting-panel">
    <h3>{t.title}</h3>
    <p>{t.intro}</p>
    <div className="inpainting-controls">
      <label>{t.brush}: {brush}px <input type="range" min="8" max="120" step="2" value={brush} onChange={event => setBrush(Number(event.target.value))} disabled={working} /></label>
      <button className="secondary" type="button" disabled={working} onClick={() => {
        const canvas = canvasRef.current;
        canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
        setHasMask(false);
        setMessage("");
      }}>{t.clear}</button>
      <button className="primary" type="button" disabled={working || !dimensions.width || !configured} onClick={() => void generate()}>{working ? t.working : t.generate}</button>
    </div>
    <div className="inpainting-canvas-wrap" style={{ aspectRatio: dimensions.width && dimensions.height ? dimensions.width + "/" + dimensions.height : "2 / 1" }}>
      <img src={imageUrl} alt={t.before} />
      <canvas ref={canvasRef} onPointerDown={event => { if (working) return; drawing.current = true; event.currentTarget.setPointerCapture(event.pointerId); paint(event); }} onPointerMove={paint} onPointerUp={() => { drawing.current = false; }} onPointerCancel={() => { drawing.current = false; }} />
    </div>
    {resultUrl && <div className="inpainting-result">
      <h4>{t.after}</h4>
      <div className="inpainting-preview"><div><strong>{t.before}</strong><img src={imageUrl} alt={t.before} /></div><div><strong>{t.after}</strong><img src={resultUrl} alt={t.after} /></div></div>
      <div className="editor-actions">
        <button className="primary" type="button" onClick={async () => { const response = await fetch(resultUrl); onAccept(await response.blob()); setResultUrl(current => { if (current) URL.revokeObjectURL(current); return null; }); }}>{t.accept}</button>
        <button className="secondary" type="button" onClick={() => setResultUrl(current => { if (current) URL.revokeObjectURL(current); return null; })}>{t.reject}</button>
      </div>
    </div>}
    {message && <p className="media-warning">{message}</p>}
    <small>{t.privacy}</small>
  </section>;
}
