import { useRef, useState } from "react";
export function useDropzone(opts: { accept?: string; maxSize?: number }) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragActive, setDrag] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const selectFile = (candidate?: File) => {
    if (!candidate) return;
    const extension = "." + candidate.name.split(".").pop()?.toLowerCase();
    const message = opts.accept && !opts.accept.split(",").includes(extension) ? "Chỉ hỗ trợ video MP4 hoặc MKV." : opts.maxSize && candidate.size > opts.maxSize ? "Video vượt quá giới hạn 2 GB." : "";
    setError(message);
    setFile(message ? null : candidate);
  };
  const onDrop = (e: React.DragEvent) => { e.preventDefault(); setDrag(false); selectFile(e.dataTransfer.files[0]); };
  const getRootProps = () => ({
    onDragOver: (e: React.DragEvent) => { e.preventDefault(); setDrag(true); },
    onDragLeave: () => setDrag(false),
    onDrop,
    onClick: () => input.current?.click(),
    onKeyDown: (e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.current?.click(); } },
    tabIndex: 0,
    role: "button",
    "aria-label": "Chọn hoặc kéo thả video",
  });
  const getInputProps = () => ({
    id: "dz-input",
    ref: input,
    type: "file" as const,
    accept: opts.accept,
    style: { display: "none" as const },
    onClick: (e: React.MouseEvent) => e.stopPropagation(),
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => selectFile(e.target.files?.[0]),
  });
  return { getRootProps, getInputProps, isDragActive, file, error, resetFile: () => { setFile(null); setError(""); if (input.current) input.current.value = ""; } };
}
