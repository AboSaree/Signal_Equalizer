"""
views.py — DRF API views for SignalLab.

Changes over original:
  - AnalyzeView.post()  : now returns dominant_freq + signal_type
    (they were computed but silently dropped in the original response).
  - EqualizeView.post() : gain clamped via dB scale (0 dB = unity gain),
    accepts optional gain_db field alongside the legacy linear gain field.
  - Everything else     : unchanged.
"""

import io
import struct
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

from . import signal_processor as sp
from . import mode_settings as ms


# ── Helpers ──────────────────────────────────────────


def _fft_ds(freqs, mags, n=2000):
    """Downsample FFT arrays to *n* points for JSON transfer."""
    if len(freqs) <= n:
        return sp._to_list(freqs), sp._to_list(mags)
    idx = np.linspace(0, len(freqs) - 1, n, dtype=int)
    return sp._to_list(freqs[idx]), sp._to_list(mags[idx])


def _db_to_linear(db: float) -> float:
    """Convert dB value to linear gain, clamped to [0, 4]."""
    return float(np.clip(10 ** (db / 20.0), 0.0, 4.0))


def _resolve_gain(comp: dict) -> float:
    """
    Resolve the effective linear gain from a component dict.

    Priority:
      1. gain_db  (dB value sent by the new frontend)
      2. gain     (legacy linear 0-2 value)
      3. 1.0      (unity — safe default)

    Linear gain is clamped to [0.0, 2.0] to match the slider range.
    dB gain is accepted in the range [-40, +6] dB.
    """
    if "gain_db" in comp:
        db = float(comp["gain_db"])
        db = max(-40.0, min(6.0, db))
        return _db_to_linear(db)

    raw = float(comp.get("gain", 1.0))
    return max(0.0, min(2.0, raw))


# ── Upload ───────────────────────────────────────────


class UploadView(APIView):
    """POST /api/upload/  — accepts CSV or MP3 multipart upload."""

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response(
                {"error": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        raw  = f.read()
        name = f.name.lower()

        try:
            if name.endswith(".csv") or name.endswith(".txt"):
                text = raw.decode("utf-8", errors="replace")
                times, values, sr = sp.parse_csv(text)
                file_type = "csv"
            else:
                times, values, sr = sp.parse_mp3(raw)
                file_type = "audio"
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        freqs, mags, _ = sp.compute_fft(values, sr)
        ds_t, ds_v     = sp.downsample_signal(times, values, target_points=4000)
        fft_f, fft_m   = _fft_ds(freqs, mags)

        components, total_energy, dom_freq, sig_type = sp.analyze_signal(values, sr)

        data = {
            "signal":       {"times": ds_t, "values": ds_v},
            "fft":          {"frequencies": fft_f, "magnitudes": fft_m},
            "sample_rate":  sr,
            "duration":     float(times[-1] - times[0]) if len(times) else 0,
            "file_type":    file_type,
            "n_samples":    len(values),
            "dominant_freq": dom_freq,
            "signal_type":   sig_type,
            "total_energy":  total_energy,
            "components":    components,
        }

        mode_name = request.data.get("mode")
        if mode_name:
            try:
                data["mode_config"] = ms.load_mode(mode_name)
            except KeyError:
                pass

        return Response(data)


# ── Analyze ──────────────────────────────────────────


class AnalyzeView(APIView):
    """POST /api/analyze/ — returns component detection + signal metrics."""

    def post(self, request):
        sig    = request.data.get("signal")
        sr     = float(request.data.get("sample_rate", 1000))
        n_comp = int(request.data.get("n_components", 8))

        if not sig or "values" not in sig:
            return Response(
                {"error": "Missing signal values"},
                status=status.HTTP_400_BAD_REQUEST
            )

        values = np.array(sig["values"], dtype=np.float64)
        components, total_energy, dom_freq, sig_type = sp.analyze_signal(
            values, sr, n_comp
        )

        # ── FIX: original response was missing dominant_freq & signal_type ──
        return Response({
            "components":    components,
            "total_energy":  total_energy,
            "dominant_freq": dom_freq,    # was missing in original
            "signal_type":   sig_type,    # was missing in original
        })


# ── Decompose ────────────────────────────────────────


class DecomposeView(APIView):
    """POST /api/decompose/ — returns full time-series for each component."""

    def post(self, request):
        sig        = request.data.get("signal")
        sr         = request.data.get("sample_rate")
        components = request.data.get("components")

        if not sig or not components:
            return Response(
                {"error": "Missing signal or components"},
                status=status.HTTP_400_BAD_REQUEST
            )

        values     = np.array(sig["values"], dtype=np.float64)
        decomposed = sp.decompose_signal(values, sr, components)

        return Response({"decomposed": decomposed})


# ── Equalize ─────────────────────────────────────────


class EqualizeView(APIView):
    """
    POST /api/equalize/

    Returns the signal **in the transform domain** (no inverse transform).

    Response shape:
      {
        "transform_domain": { "type": "fourier"|"wavelet"|"stft"|"dct", ...data },
        "input_fft":  { "frequencies": [...], "magnitudes": [...] },
      }

    The frontend is responsible for rendering the domain data directly.
    An inverse transform is intentionally NOT applied.
    """

    def post(self, request):
        sig      = request.data.get("signal")
        sr       = float(request.data.get("sample_rate", 1000))
        comps    = request.data.get("components", [])
        method   = request.data.get("method", "fourier")
        wavelet  = request.data.get("wavelet", "db4")

        if not sig:
            return Response(
                {"error": "signal required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        values = np.array(sig["values"], dtype=np.float64)

        # ── Build bands ─────────────────────────────
        bands = []
        for comp in comps:
            gain = _resolve_gain(comp)
            if "windows" in comp and comp["windows"]:
                for w in comp["windows"]:
                    bands.append({
                        "freq_min": float(w["freq_min"]),
                        "freq_max": float(w["freq_max"]),
                        "gain":     gain,
                    })
            elif "freq_min" in comp and "freq_max" in comp:
                bands.append({
                    "freq_min": float(comp["freq_min"]),
                    "freq_max": float(comp["freq_max"]),
                    "gain":     gain,
                })

        # ── Forward transform only (no inverse) ─────
        if method == "stft":
            domain = sp.compute_stft_domain(values, sr, bands)
        elif method == "dct":
            domain = sp.compute_dct_domain(values, sr, bands)
        elif method.startswith("wavelet"):
            wv     = wavelet if wavelet else "db4"
            domain = sp.compute_wavelet_domain(values, sr, bands, wavelet=wv)
        else:
            # fourier (default)
            domain = sp.compute_fourier_domain(values, sr, bands)

        # ── Time-domain output (equalized, for "return to time" view) ──
        if method.startswith("wavelet"):
            wv_td     = wavelet if wavelet else "db4"
            out_time  = sp.apply_wavelet_equalization(values, sr, bands, wavelet=wv_td)
        else:
            out_time  = sp.apply_equalization(values, sr, bands)

        out_time = np.array(out_time, dtype=np.float64)
        times    = np.array(
            sig.get("times", np.arange(len(values)).tolist()),
            dtype=np.float64
        )
        ds_t, ds_v = sp.downsample_signal(times, out_time, target_points=4000)

        # ── Input FFT for the spectrum panel (unchanged) ─
        in_freqs, in_mags, _ = sp.compute_fft(values, sr)
        fft_f, fft_m = _fft_ds(in_freqs, in_mags)

        # ── Output FFT ───────────────────────────────────
        out_freqs, out_mags, _ = sp.compute_fft(out_time, sr)
        out_fft_f, out_fft_m  = _fft_ds(out_freqs, out_mags)

        return Response({
            "transform_domain": domain,
            "output_signal":    {"times": ds_t, "values": ds_v},
            "input_fft":        {"frequencies": fft_f,     "magnitudes": fft_m},
            "output_fft":       {"frequencies": out_fft_f, "magnitudes": out_fft_m},
        })


# ── Modes ────────────────────────────────────────────


class ModesListView(APIView):
    """GET /api/modes/  — list all available mode names."""

    def get(self, request):
        return Response({"modes": ms.list_modes()})


class ModeDetailView(APIView):
    """
    GET    /api/modes/<name>/  — load mode config
    POST   /api/modes/<name>/  — save custom mode
    DELETE /api/modes/<name>/  — delete custom mode
    """

    def get(self, request, mode_name):
        try:
            return Response(ms.load_mode(mode_name))
        except KeyError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request, mode_name):
        try:
            config = ms.save_mode(mode_name, request.data)
            return Response(config, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, mode_name):
        try:
            ms.delete_mode(mode_name)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except KeyError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


# ── Wavelets ─────────────────────────────────────────


class WaveletsView(APIView):
    """GET /api/wavelets/  — available wavelets & recommendations."""

    def get(self, request):
        wavelets = [
            {"name": "db4",   "family": "Daubechies", "desc": "Daubechies 4 — general purpose"},
            {"name": "db8",   "family": "Daubechies", "desc": "Daubechies 8 — smoother, musical"},
            {"name": "sym5",  "family": "Symlets",    "desc": "Symlets 5 — near-symmetric, speech"},
            {"name": "coif3", "family": "Coiflets",   "desc": "Coiflets 3 — symmetric, animal sounds"},
            {"name": "haar",  "family": "Haar",       "desc": "Haar — simplest, step-like signals"},
        ]
        return Response({
            "available_wavelets": wavelets,
            "recommendations":    sp.WAVELET_RECOMMENDATIONS,
        })


# ── Audio export ─────────────────────────────────────


class AudioExportView(APIView):
    """POST /api/audio/export/  — export values as WAV binary."""

    def post(self, request):
        values = request.data.get("values", [])
        sr     = int(float(request.data.get("sample_rate", 44100)))

        if not values:
            return Response(
                {"error": "values required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        arr  = np.array(values[:50000], dtype=np.float64)
        peak = np.max(np.abs(arr)) if np.max(np.abs(arr)) > 0 else 1.0
        arr  = (arr / peak * 32767).astype(np.int16)

        buf       = io.BytesIO()
        n_samples = len(arr)
        data_size = n_samples * 2

        # WAV header
        buf.write(b'RIFF')
        buf.write(struct.pack('<I', 36 + data_size))
        buf.write(b'WAVE')
        buf.write(b'fmt ')
        buf.write(struct.pack('<I', 16))       # chunk size
        buf.write(struct.pack('<H', 1))        # PCM
        buf.write(struct.pack('<H', 1))        # mono
        buf.write(struct.pack('<I', sr))       # sample rate
        buf.write(struct.pack('<I', sr * 2))   # byte rate
        buf.write(struct.pack('<H', 2))        # block align
        buf.write(struct.pack('<H', 16))       # bits per sample
        buf.write(b'data')
        buf.write(struct.pack('<I', data_size))
        buf.write(arr.tobytes())

        buf.seek(0)
        return HttpResponse(buf.read(), content_type="audio/wav")