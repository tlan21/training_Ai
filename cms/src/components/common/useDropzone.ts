import { useCallback, useState } from "react";
export function useDropzone(opts: { accept?: string; maxSize?: number }) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragActive, setDrag] = useState(false);
  const onDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); }, []);
  const getRootProps = () => ({
    onDragOver: (e: React.DragEvent) => { e.preventDefault(); setDrag(true); },
    onDragLeave: () => setDrag(false),
    onDrop,
    onClick: () => document.getElementById("dz-input")?.click(),
  });
  const getInputProps = () => ({
    id: "dz-input",
    type: "file" as const,
    accept: opts.accept,
    style: { display: "none" as const },
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) setFile(f); },
  });
  return { getRootProps, getInputProps, isDragActive, file };
}
