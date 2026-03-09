import { Component, ElementRef, ViewChild, OnDestroy, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface SignalSample {
  time: number;   // ms (CSV) or seconds (audio)
  value: number;  // mV (CSV) or amplitude -1..1 (audio)
}

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.scss']
})
export class UploadComponent implements OnDestroy {

  @ViewChild('cineCanvas')   canvasRef!:       ElementRef<HTMLCanvasElement>;
  @ViewChild('outputCanvas') outputCanvasRef!: ElementRef<HTMLCanvasElement>;

  selectedFile: File | null = null;
  isDragOver = false;
  analyseError: string | null = null;

  // ── Cine viewer state ─────────────────────────────
  showCine = false;
  isPlaying = false;

  // ── File-type flag — drives axis labels & x formatting ──
  isAudioFile = false;

  private signal: SignalSample[] = [];
  private outputSignal: SignalSample[] = [];
  private outputHistory: SignalSample[] = [];
  private outputIndex = 0;
  private rafId: number | null = null;

  // Canvas dimensions
  readonly CANVAS_W = 800;
  readonly CANVAS_H = 260;
  readonly PAD_LEFT = 52;
  readonly PAD_RIGHT = 16;
  readonly PAD_TOP = 28;
  readonly PAD_BOTTOM = 36;

  // ── Y-axis limits ─────────────────────────────────
  private yMinBase = -1;
  private yMaxBase = 1;
  private yMin = -1;
  private yMax = 1;

  // ── Output Y-axis limits ──────────────────────────
  private outYMin = -1;
  private outYMax = 1;

  // ── Playhead ──────────────────────────────────────
  // Index of NEXT sample to consume from signal[]
  private signalIndex = 0;

  // ── Zoom ──────────────────────────────────────────
  // pixelsPerSample: how many canvas pixels one sample occupies
  // higher = zoomed in (fewer samples visible)
  // lower  = zoomed out (more samples visible)
  private pixelsPerSample = 1;
  private readonly DEFAULT_PPS = 1;

  // ── Speed ─────────────────────────────────────────
  // How many signal samples are consumed per animation frame
  private samplesPerFrame = 1;
  private readonly DEFAULT_SPF = 1;

  // ── Pan ───────────────────────────────────────────
  // panOffset: how many samples behind the live head the viewport is
  // 0 = following live head; >0 = showing older data
  private panOffset = 0;

  // Full history of all consumed samples (enables pan & zoom into past)
  private history: SignalSample[] = [];

  // ── Mouse / touch panning ─────────────────────────
  isPanning = false;
  private panStartX = 0;
  private panOffsetAtStart = 0;

  // Bound event handlers (stored so we can removeEventListener)
  private _onMouseDown!: (e: MouseEvent) => void;
  private _onMouseMove!: (e: MouseEvent) => void;
  private _onMouseUp!:   (e: MouseEvent) => void;
  private _onTouchStart!: (e: TouchEvent) => void;
  private _onTouchMove!:  (e: TouchEvent) => void;
  private _onTouchEnd!:   (e: TouchEvent) => void;

  constructor(private router: Router, private ngZone: NgZone, private http: HttpClient) {}

  ngOnDestroy(): void { this.stopAnimation(); }

  onBackClick(): void {
    this.stopAnimation();
    this.router.navigate(['/']);
  }

  // ── Drag & drop ───────────────────────────────────

  onDragOver(e: DragEvent): void { e.preventDefault(); e.stopPropagation(); this.isDragOver = true; }
  onDragLeave(e: DragEvent): void { e.preventDefault(); e.stopPropagation(); this.isDragOver = false; }

  onDrop(e: DragEvent): void {
    e.preventDefault(); e.stopPropagation(); this.isDragOver = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) { this.selectedFile = file; this.analyseError = null; this.resetCine(); }
  }

  onFileSelected(e: Event): void {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) { this.selectedFile = file; this.analyseError = null; this.resetCine(); }
  }

  // ── Analyse ───────────────────────────────────────

  onAnalyse(): void {
    if (!this.selectedFile) return;
    const formData = new FormData();
    formData.append('file', this.selectedFile, this.selectedFile.name);
    this.http.post<any>(`${environment.apiBaseUrl}/upload/`, formData).subscribe({
      next: (res) => this.ngZone.run(() => {
        this.isAudioFile = res.file_type === 'audio';
        const times: number[]  = res.signal?.times  ?? [];
        const values: number[] = res.signal?.values ?? [];
        const samples: SignalSample[] = times.map((t, i) => ({ time: t, value: values[i] ?? 0 }));
        this.loadSignal(samples);

        // Call equalize with unity gain to get the backend-processed output signal
        const bands = (res.components ?? []).map((c: any) => ({
          freq_min: c.freq_min, freq_max: c.freq_max, gain: 1.0
        }));
        this.http.post<any>(`${environment.apiBaseUrl}/equalize/`, {
          signal: res.signal,
          sample_rate: res.sample_rate,
          components: bands.length ? bands : [{ freq_min: 0, freq_max: res.sample_rate / 2, gain: 1.0 }],
          method: 'fourier'
        }).subscribe({
          next: (eqRes) => this.ngZone.run(() => {
            const ot: number[]  = eqRes.output_signal?.times  ?? [];
            const ov: number[]  = eqRes.output_signal?.values ?? [];
            this.outputSignal = ot.map((t, i) => ({ time: t, value: ov[i] ?? 0 }));
            // Compute output Y bounds
            let dMin = Infinity, dMax = -Infinity;
            for (let i = 0; i < this.outputSignal.length; i++) {
              const v = this.outputSignal[i].value;
              if (v < dMin) dMin = v; if (v > dMax) dMax = v;
            }
            const pad = (dMax - dMin || 1) * 0.1;
            this.outYMin = dMin - pad; this.outYMax = dMax + pad;
          }),
          error: (err) => this.ngZone.run(() => {
            console.error('Equalize error:', err);
            this.analyseError = 'Output processing failed: ' + (err?.error?.error ?? err?.message ?? 'Unknown error');
          })
        });
      }),
      error: (err) => this.ngZone.run(() => {
        console.error('Upload error:', err);
        this.analyseError = 'Upload failed: ' + (err?.error?.error ?? err?.message ?? 'Unknown error');
      })
    });
  }

  private loadSignal(samples: SignalSample[]): void {
    this.signal = samples;

    // Safe min/max loop — spread operator crashes on large arrays (stack overflow)
    let dMin = Infinity, dMax = -Infinity;
    for (let i = 0; i < samples.length; i++) {
      const v = samples[i].value;
      if (v < dMin) dMin = v;
      if (v > dMax) dMax = v;
    }
    const pad = (dMax - dMin || 1) * 0.1;
    this.yMinBase = dMin - pad; this.yMaxBase = dMax + pad;
    this.yMin = this.yMinBase; this.yMax = this.yMaxBase;

    // Reset view state
    this.signalIndex = 0;
    this.history = [];
    this.pixelsPerSample = this.DEFAULT_PPS;
    this.samplesPerFrame = this.DEFAULT_SPF;
    this.panOffset = 0;

    this.showCine = true;
    this.isPlaying = true;
    setTimeout(() => this.startAnimation(), 0);
  }

  // ── Animation ─────────────────────────────────────

  private startAnimation(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;
    this.bindCanvasEvents(canvas);

    const outCanvas = this.outputCanvasRef?.nativeElement;
    if (outCanvas) this.bindCanvasEvents(outCanvas);

    const ctx    = canvas.getContext('2d')!;
    const outCtx = outCanvas ? outCanvas.getContext('2d')! : null;
    this.scheduleFrame(ctx, outCtx);
  }

  private scheduleFrame(ctx: CanvasRenderingContext2D, outCtx: CanvasRenderingContext2D | null): void {
    if (!this.isPlaying) return;
    this.rafId = requestAnimationFrame(() => this.drawFrame(ctx, outCtx));
  }

  private drawFrame(ctx: CanvasRenderingContext2D, outCtx: CanvasRenderingContext2D | null): void {
    if (!this.isPlaying) return;

    const advance = Math.max(1, Math.round(this.samplesPerFrame));
    for (let s = 0; s < advance && this.signalIndex < this.signal.length; s++) {
      this.history.push(this.signal[this.signalIndex++]);
    }
    for (let s = 0; s < advance && this.outputIndex < this.outputSignal.length; s++) {
      this.outputHistory.push(this.outputSignal[this.outputIndex++]);
    }

    this.renderCanvas(ctx, this.history, this.yMin, this.yMax);
    if (outCtx) this.renderCanvas(outCtx, this.outputHistory, this.outYMin, this.outYMax);

    if (this.signalIndex < this.signal.length) {
      this.scheduleFrame(ctx, outCtx);
    } else {
      this.isPlaying = false;
      this.rafId = null;
    }
  }

  // ── Render ────────────────────────────────────────

  private renderCanvas(ctx: CanvasRenderingContext2D, history = this.history, yMin = this.yMin, yMax = this.yMax): void {
    const W = this.CANVAS_W, H = this.CANVAS_H;
    const pl = this.PAD_LEFT, pr = this.PAD_RIGHT;
    const pt = this.PAD_TOP,  pb = this.PAD_BOTTOM;
    const plotW = W - pl - pr;
    const plotH = H - pt - pb;

    // How many samples fit in the visible window at current zoom
    const samplesVisible = Math.max(2, Math.round(plotW / this.pixelsPerSample));

    // Head = last history index visible (honoring pan)
    const headIdx    = Math.max(0, history.length - 1 - this.panOffset);
    const tailIdx    = Math.max(0, headIdx - samplesVisible + 1);
    const windowSlice = history.slice(tailIdx, headIdx + 1);

    // ── Axis meta (driven by file type) ───────────────
    const xUnit     = this.isAudioFile ? 's'         : 'ms';
    const yUnit     = this.isAudioFile ? 'Amplitude' : 'mV';
    const xDecimals = this.isAudioFile ? 2            : 0;
    const yDecimals = this.isAudioFile ? 2            : 2;

    // Background
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#0d0d0d'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#111111'; ctx.fillRect(pl, pt, plotW, plotH);

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = pt + (plotH / 4) * i;
      ctx.beginPath(); ctx.moveTo(pl, y); ctx.lineTo(pl + plotW, y); ctx.stroke();
    }
    for (let i = 0; i <= 4; i++) {
      const x = pl + (plotW / 4) * i;
      ctx.beginPath(); ctx.moveTo(x, pt); ctx.lineTo(x, pt + plotH); ctx.stroke();
    }

    // Y labels
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.font = '10px DM Sans, sans-serif';
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (let i = 0; i <= 4; i++) {
      const val = yMin + (1 - i / 4) * (yMax - yMin);
      ctx.fillText(val.toFixed(yDecimals), pl - 6, pt + (plotH / 4) * i);
    }

    // Y title
    ctx.save();
    ctx.translate(12, pt + plotH / 2); ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.font = '11px DM Sans, sans-serif';
    ctx.fillText(yUnit, 0, 0); ctx.restore();

    // X labels
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    ctx.fillStyle = 'rgba(255,255,255,0.5)'; ctx.font = '10px DM Sans, sans-serif';
    for (let i = 0; i <= 4; i++) {
      const idx = Math.round((windowSlice.length - 1) * (i / 4));
      const t   = windowSlice[idx]?.time ?? 0;
      ctx.fillText(t.toFixed(xDecimals), pl + (plotW / 4) * i, pt + plotH + 5);
    }

    // X title
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.font = '11px DM Sans, sans-serif';
    ctx.fillText(xUnit, pl + plotW / 2, H - 2);

    // ── Waveform ──────────────────────────────────────
    if (windowSlice.length > 1) {
      const toY = (v: number) =>
        pt + plotH * (1 - (v - yMin) / (yMax - yMin));

      if (this.isAudioFile) {
        // Audio: filled mirror waveform (envelope style)
        const zeroY  = toY(0);
        const xScale = plotW / (windowSlice.length - 1);

        // Filled area above zero
        ctx.fillStyle = 'rgba(123,110,224,0.35)';
        ctx.beginPath();
        ctx.moveTo(pl, zeroY);
        for (let i = 0; i < windowSlice.length; i++) {
          const x = pl + i * xScale;
          const y = toY(Math.max(0, windowSlice[i].value));
          ctx.lineTo(x, y);
        }
        ctx.lineTo(pl + (windowSlice.length - 1) * xScale, zeroY);
        ctx.closePath(); ctx.fill();

        // Filled area below zero (mirrored)
        ctx.fillStyle = 'rgba(123,110,224,0.35)';
        ctx.beginPath();
        ctx.moveTo(pl, zeroY);
        for (let i = 0; i < windowSlice.length; i++) {
          const x = pl + i * xScale;
          const y = toY(Math.min(0, windowSlice[i].value));
          ctx.lineTo(x, y);
        }
        ctx.lineTo(pl + (windowSlice.length - 1) * xScale, zeroY);
        ctx.closePath(); ctx.fill();

        // Centre zero line
        ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(pl, zeroY); ctx.lineTo(pl + plotW, zeroY); ctx.stroke();

        // Top outline stroke
        ctx.shadowColor = '#7b6ee0'; ctx.shadowBlur = 4;
        ctx.strokeStyle = '#7b6ee0'; ctx.lineWidth = 1.2;
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(pl, toY(windowSlice[0].value));
        for (let i = 1; i < windowSlice.length; i++) {
          ctx.lineTo(pl + i * xScale, toY(windowSlice[i].value));
        }
        ctx.stroke(); ctx.shadowBlur = 0;

      } else {
        // CSV / ECG: classic line waveform
        const xScale = plotW / (windowSlice.length - 1);
        ctx.shadowColor = '#7b6ee0'; ctx.shadowBlur = 6;
        ctx.strokeStyle = '#7b6ee0'; ctx.lineWidth = 1.8;
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(pl, toY(windowSlice[0].value));
        for (let i = 1; i < windowSlice.length; i++) {
          ctx.lineTo(pl + i * xScale, toY(windowSlice[i].value));
        }
        ctx.stroke(); ctx.shadowBlur = 0;
      }
    }

    // Border
    ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 1;
    ctx.strokeRect(pl, pt, plotW, plotH);
  }

  // ── Canvas event binding (pan) ────────────────────

  private bindCanvasEvents(canvas: HTMLCanvasElement): void {
    this._onMouseDown  = (e) => this.panStart(e.offsetX);
    this._onMouseMove  = (e) => { if (this.isPanning) this.panMove(e.offsetX, canvas); };
    this._onMouseUp    = ()  => this.panEnd();
    this._onTouchStart = (e) => { e.preventDefault(); this.panStart(e.touches[0].clientX); };
    this._onTouchMove  = (e) => { e.preventDefault(); if (this.isPanning) this.panMove(e.touches[0].clientX, canvas); };
    this._onTouchEnd   = ()  => this.panEnd();

    canvas.style.cursor = 'grab';
    canvas.addEventListener('mousedown',  this._onMouseDown);
    canvas.addEventListener('mousemove',  this._onMouseMove);
    canvas.addEventListener('mouseup',    this._onMouseUp);
    canvas.addEventListener('mouseleave', this._onMouseUp);
    canvas.addEventListener('touchstart', this._onTouchStart, { passive: false });
    canvas.addEventListener('touchmove',  this._onTouchMove,  { passive: false });
    canvas.addEventListener('touchend',   this._onTouchEnd);
  }

  private panStart(x: number): void {
    this.isPanning = true;
    this.panStartX = x;
    this.panOffsetAtStart = this.panOffset;
    const canvas = this.canvasRef?.nativeElement;
    if (canvas) canvas.style.cursor = 'grabbing';
  }

  private panMove(x: number, canvas: HTMLCanvasElement): void {
    const plotW = this.CANVAS_W - this.PAD_LEFT - this.PAD_RIGHT;
    const samplesVisible = plotW / this.pixelsPerSample;
    const pixelDelta = x - this.panStartX;
    // drag right → move forward in time (reduce offset), drag left → go back (increase offset)
    const sampleDelta = Math.round((pixelDelta / plotW) * samplesVisible);
    this.panOffset = Math.max(0, Math.min(
      this.panOffsetAtStart + sampleDelta,
      this.history.length - 1
    ));
    if (!this.isPlaying) this.renderCanvas(canvas.getContext('2d')!, this.history, this.yMin, this.yMax);
  }

  private panEnd(): void {
    this.isPanning = false;
    const canvas = this.canvasRef?.nativeElement;
    if (canvas) canvas.style.cursor = 'grab';
  }

  // ── Controls ──────────────────────────────────────

  onStop(): void {
    this.isPlaying = false;
    if (this.rafId !== null) { cancelAnimationFrame(this.rafId); this.rafId = null; }
  }

  onResume(): void {
    if (this.isPlaying || this.signalIndex >= this.signal.length) return;
    this.isPlaying = true;
    const canvas    = this.canvasRef?.nativeElement;
    const outCanvas = this.outputCanvasRef?.nativeElement;
    if (canvas) this.scheduleFrame(canvas.getContext('2d')!, outCanvas ? outCanvas.getContext('2d')! : null);
  }

  onRestart(): void {
    this.stopAnimation();
    this.signalIndex = 0;
    this.history = [];
    this.outputIndex = 0;
    this.outputHistory = [];
    this.panOffset = 0;
    this.isPlaying = true;
    setTimeout(() => this.startAnimation(), 0);
  }

  onZoomIn(): void {
    // fewer ms visible — increase pixels per sample
    this.pixelsPerSample = Math.min(this.pixelsPerSample * 1.1, 50);
    this.redrawIfPaused();
  }

  onZoomOut(): void {
    // more ms visible — decrease pixels per sample
    this.pixelsPerSample = Math.max(this.pixelsPerSample / 1.1, 0.05);
    this.redrawIfPaused();
  }

  onSpeedUp(): void {
    this.samplesPerFrame = Math.min(this.samplesPerFrame * 1.1, 200);
  }

  onSpeedDown(): void {
    this.samplesPerFrame = Math.max(this.samplesPerFrame / 1.1, 0.01);
  }

  onReset(): void {
    this.pixelsPerSample = this.DEFAULT_PPS;
    this.samplesPerFrame = this.DEFAULT_SPF;
    this.panOffset = 0;
    this.yMin = this.yMinBase;
    this.yMax = this.yMaxBase;
    this.redrawIfPaused();
  }

  private redrawIfPaused(): void {
    if (this.isPlaying) return;
    const canvas    = this.canvasRef?.nativeElement;
    const outCanvas = this.outputCanvasRef?.nativeElement;
    if (canvas)    this.renderCanvas(canvas.getContext('2d')!, this.history, this.yMin, this.yMax);
    if (outCanvas) this.renderCanvas(outCanvas.getContext('2d')!, this.outputHistory, this.outYMin, this.outYMax);
  }

  private stopAnimation(): void {
    this.isPlaying = false;
    if (this.rafId !== null) { cancelAnimationFrame(this.rafId); this.rafId = null; }
  }

  private resetCine(): void {
    this.stopAnimation();
    this.showCine = false;
    this.isAudioFile = false;
    this.signal = []; this.history = [];
    this.outputSignal = []; this.outputHistory = [];
    this.signalIndex = 0; this.outputIndex = 0; this.panOffset = 0;
    this.pixelsPerSample = this.DEFAULT_PPS;
    this.samplesPerFrame = this.DEFAULT_SPF;
  }

  // ── Template helpers ──────────────────────────────

  get signalFinished(): boolean { return this.signalIndex >= this.signal.length; }

  get speedLabel(): string {
    return `${(this.samplesPerFrame / this.DEFAULT_SPF).toFixed(1)}×`;
  }

  get fileSizeLabel(): string {
    if (!this.selectedFile) return '';
    const b = this.selectedFile.size;
    if (b < 1024) return `${b} B`;
    if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / 1048576).toFixed(1)} MB`;
  }
}
