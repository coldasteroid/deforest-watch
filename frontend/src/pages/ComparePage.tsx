import { AlertTriangle, CheckCircle2, ImagePlus, ScanSearch } from 'lucide-react';
import { useEffect, useState } from 'react';
import { compareImages, type ComparisonResult } from '../api/client';
import { Card, PageHeader } from '../components/shared/State';

function FilePicker({ label, file, onChange }: { label: string; file: File | null; onChange: (file: File | null) => void }) {
  const [preview, setPreview] = useState<string>();
  useEffect(() => {
    if (!file) { setPreview(undefined); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  return (
    <label className="block cursor-pointer rounded-md border-2 border-dashed border-border bg-slate-50 p-4 hover:border-slate-400">
      <span className="flex items-center gap-2 text-sm font-semibold"><ImagePlus size={16} /> {label}</span>
      <span className="mt-1 block text-xs text-muted">RGB image or 4-band GeoTIFF</span>
      {preview ? <img src={preview} alt={`${label} preview`} className="mt-3 h-44 w-full rounded object-cover" /> : file?.name.match(/\.tiff?$/i) ? <span className="mt-3 flex h-44 flex-col items-center justify-center rounded border border-border bg-white text-sm text-muted"><span className="font-semibold text-slate-700">GeoTIFF selected</span><span className="mt-1 text-xs">Preview unavailable in the browser</span></span> : <span className="mt-3 flex h-44 items-center justify-center rounded border border-border bg-white text-sm text-muted">Choose image</span>}
      <input className="sr-only" type="file" accept="image/*,.tif,.tiff" onChange={(event) => onChange(event.target.files?.[0] ?? null)} />
      {file && <span className="mt-2 block truncate text-xs text-slate-600">{file.name}</span>}
    </label>
  );
}

export function ComparePage() {
  const [before, setBefore] = useState<File | null>(null);
  const [after, setAfter] = useState<File | null>(null);
  const [threshold, setThreshold] = useState(0.2);
  const [pixelSizeM, setPixelSizeM] = useState(10);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!before || !after) { setError('Select both a before and an after image.'); return; }
    setLoading(true); setError(''); setResult(null);
    try { setResult(await compareImages(before, after, threshold, 25, pixelSizeM)); }
    catch (err) { setError((err as { detail?: string }).detail ?? 'Comparison failed. Check that both images have matching dimensions.'); }
    finally { setLoading(false); }
  }

  const apiUrl = import.meta.env.VITE_API_URL ?? '/api';
  const imageUrl = (path: string) => path.startsWith('http') ? path : `${apiUrl.replace(/\/$/, '')}${path.replace(/^\/api/, '')}`;

  return <div>
    <PageHeader title="Compare imagery" meta="Upload before and after images to detect vegetation loss" />
    <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-4">
        <Card className="p-4">
          <form onSubmit={submit}>
            <div className="mb-4 flex items-start gap-3"><div className="rounded-md bg-slate-900 p-2 text-white"><ScanSearch size={18} /></div><div><h2 className="font-semibold">Image comparison</h2><p className="text-sm text-muted">The detector computes NDVI for satellite imagery and an excess-green index for ordinary RGB photos.</p></div></div>
            <div className="grid gap-4 md:grid-cols-2"><FilePicker label="Before image" file={before} onChange={setBefore} /><FilePicker label="After image" file={after} onChange={setAfter} /></div>
            <div className="mt-4 flex flex-wrap items-end gap-4 border-t border-border pt-4">
              <label className="text-sm">Vegetation drop threshold <input className="ml-2 w-24 rounded border border-border px-2 py-1" type="number" min="0.01" max="2" step="0.01" value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} /></label>
              <label className="text-sm">Pixel size <input className="ml-2 w-20 rounded border border-border px-2 py-1" type="number" min="1" step="1" value={pixelSizeM} onChange={(event) => setPixelSizeM(Number(event.target.value))} /> <span className="text-muted">m</span></label>
              <button disabled={loading} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" type="submit">{loading ? 'Comparing…' : 'Detect deforestation'}</button>
            </div>
          </form>
          {error && <div className="mt-4 flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertTriangle size={16} /> {error}</div>}
        </Card>
        {result && <Card className="p-4"><div className="mb-3 flex items-center gap-2 font-semibold"><CheckCircle2 size={18} className="text-green-700" /> Detection overlay</div><img src={imageUrl(result.overlay_url)} alt="Detected deforestation overlay" className="max-h-[560px] w-full rounded border border-border object-contain" /></Card>}
      </div>
      {result ? <aside className="space-y-4"><Card className="p-4"><h2 className="mb-3 font-semibold">Comparison result</h2><div className="grid grid-cols-2 gap-3 text-sm"><Metric label="Detected area" value={`${result.loss_area_ha.toFixed(2)} ha`} /><Metric label="Regions" value={String(result.detections.features.length)} /><Metric label="Mean vegetation drop" value={result.mean_drop.toFixed(3)} /><Metric label="Pixels changed" value={result.loss_pixels.toLocaleString()} /><Metric label="Before index" value={result.before_index.toFixed(3)} /><Metric label="After index" value={result.after_index.toFixed(3)} /></div></Card><Card className="p-4"><h2 className="mb-3 font-semibold">Change map</h2><img src={imageUrl(result.change_url)} alt="Vegetation change map" className="w-full rounded border border-border" /><p className="mt-2 text-xs text-muted">Red indicates vegetation loss; green indicates vegetation gain.</p></Card></aside> : <aside><Card className="p-4 text-sm text-muted"><h2 className="mb-2 font-semibold text-text">How it works</h2><p>Regions are counted only when vegetation drops beyond the threshold and the changed pixels form a connected patch. Small isolated noise is ignored.</p></Card></aside>}
    </div>
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-muted">{label}</div><div className="mt-1 font-semibold">{value}</div></div>; }
