"""
signal_processor.py — Pure DSP functions for SignalLab.
No side-effects, no Django imports.

Improvements over original:
  - apply_equalization   : Hann-windowed smooth frequency mask (no ringing)
  - analyze_signal       : Logarithmic band spacing (matches human hearing)
  - apply_wavelet_equalization : Fixed overlapping-band gain accumulation bug
"""

import io
import numpy as np
from scipy.fft import rfft, irfft, rfftfreq
from scipy.signal import spectrogram as scipy_spectrogram
from scipy.signal.windows import hann


# ── helpers ──────────────────────────────────────────


def _to_list(arr):
    """Convert numpy array to Python list for JSON serialisation."""
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return list(arr)


# ── CSV / MP3 parsing ───────────────────────────────


def parse_csv(text: str):
    """
    Parse a CSV (1 or 2 columns).
    If 1 column: assume it's the Y-value, generate X-axis (0, 1, 2...).
    If 2 columns: assume it's (Time, Value).
    Returns (times_np, values_np, sample_rate_hz).
    """
    import re
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    detected_cols = 0
    all_rows = []

    for line in lines:
        parts = [p.strip() for p in re.split(r'[,;\t]|\s{2,}', line.replace('"', '')) if p.strip()]
        if not parts:
            if ' ' in line:
                parts = [p.strip() for p in line.split() if p.strip()]

        row_vals = []
        for p in parts:
            try:
                row_vals.append(float(p))
            except ValueError:
                pass

        if row_vals:
            all_rows.append(row_vals)
            detected_cols = max(detected_cols, len(row_vals))

    if not all_rows:
        sample = text[:50].replace('\n', '\\n')
        raise ValueError(f"No numeric data found in CSV. Sample: [{sample}]")

    times, values = [], []
    if detected_cols >= 2:
        for row in all_rows:
            if len(row) >= 2:
                times.append(row[0])
                values.append(row[1])
    else:
        for i, row in enumerate(all_rows):
            times.append(float(i))
            values.append(row[0])

    if len(values) < 2:
        raise ValueError("CSV must contain at least 2 numeric rows.")

    times_np  = np.array(times,  dtype=np.float64)
    values_np = np.array(values, dtype=np.float64)

    dt = np.median(np.diff(times_np)) if len(times_np) > 1 else 1.0
    if dt <= 0:
        dt = 1.0

    return times_np, values_np, 1000.0 / dt


def parse_mp3(file_bytes: bytes):
    """
    Decode MP3 (or any pydub-supported format) to mono float64 in [-1, 1].
    Returns (times_np, values_np, sample_rate_hz).
    """
    from pydub import AudioSegment

    seg = AudioSegment.from_file(io.BytesIO(file_bytes))
    seg = seg.set_channels(1)
    sample_rate = seg.frame_rate
    samples = np.array(seg.get_array_of_samples(), dtype=np.float64)
    max_val = float(2 ** (seg.sample_width * 8 - 1))
    if max_val > 0:
        samples /= max_val
    times_np = np.arange(len(samples)) / sample_rate  # seconds (audio)
    return times_np, samples, float(sample_rate)


# ── FFT ──────────────────────────────────────────────


def compute_fft(values, sample_rate):
    """
    Real FFT.  Returns (freqs, magnitudes, phases) as numpy arrays.
    """
    N  = len(values)
    yf = rfft(values)
    xf = rfftfreq(N, d=1.0 / sample_rate)
    magnitudes = np.abs(yf) * 2.0 / N
    phases     = np.angle(yf)
    return xf, magnitudes, phases


# ── Smooth frequency mask ────────────────────────────


def _smooth_mask(xf: np.ndarray, fmin: float, fmax: float,
                 transition_ratio: float = 0.10) -> np.ndarray:
    """
    Build a smooth 0-to-1 mask over [fmin, fmax] using a Hann-window
    transition band on each edge.

    Using a hard rectangular mask (the original approach) causes Gibbs
    ringing in the time domain.  A smooth transition eliminates this.

    transition_ratio : fraction of the band-width used for each edge;
                       0.10 = 10 % on each side (default, safe value).
    """
    mask = np.zeros(len(xf), dtype=np.float64)
    bw   = fmax - fmin
    if bw <= 0:
        return mask

    t = bw * transition_ratio  # transition band width in Hz

    # ── Rising edge  [fmin-t … fmin] ──
    if t > 0:
        rise_mask = (xf >= fmin - t) & (xf < fmin)
        if rise_mask.any():
            mask[rise_mask] = 0.5 * (
                1.0 - np.cos(np.pi * (xf[rise_mask] - (fmin - t)) / t)
            )

    # ── Flat top  [fmin … fmax] ──
    mask[(xf >= fmin) & (xf <= fmax)] = 1.0

    # ── Falling edge  [fmax … fmax+t] ──
    if t > 0:
        fall_mask = (xf > fmax) & (xf <= fmax + t)
        if fall_mask.any():
            mask[fall_mask] = 0.5 * (
                1.0 + np.cos(np.pi * (xf[fall_mask] - fmax) / t)
            )

    return mask


# ── Fourier equalization ─────────────────────────────


def apply_equalization(values, sample_rate, bands):
    """
    FFT → smooth-mask multiply per band → IFFT.

    bands: list of {"freq_min": float, "freq_max": float, "gain": float 0-2}

    The gain is blended using a Hann-windowed smooth mask so that band
    edges do not introduce ringing artefacts (Gibbs phenomenon).
    """
    N  = len(values)
    yf = rfft(values)
    xf = rfftfreq(N, d=1.0 / sample_rate)

    # Accumulate a composite gain array (start at 1.0 everywhere)
    composite = np.ones(len(xf), dtype=np.float64)

    for band in bands:
        gain = float(band.get("gain", 1.0))
        if gain == 1.0:
            continue  # nothing to do — skip for performance

        fmin = float(band["freq_min"])
        fmax = float(band["freq_max"])

        smooth = _smooth_mask(xf, fmin, fmax)
        # Blend: composite = 1 outside band, = gain inside band
        composite += (gain - 1.0) * smooth

    yf = yf * composite
    return irfft(yf, n=N)


# ── Wavelet equalization ─────────────────────────────


WAVELET_RECOMMENDATIONS = {
    "generic":             "db4",
    "musical_instruments": "db8",
    "animal_sounds":       "coif3",
    "human_voices":        "sym5",
    "ecg":                 "db4",
}


def apply_wavelet_equalization(values, sample_rate, bands, wavelet="db4"):
    """
    pywt.wavedec → scale coefficient levels → pywt.waverec.

    Level j maps to approx freq range [sr/2^(j+1), sr/2^j].

    FIX (v2): the original code multiplied gains from all overlapping bands
    together, causing unintended gain accumulation.  We now take the
    *weighted mean* of the overlapping bands' gains instead.
    """
    import pywt

    max_level = pywt.dwt_max_level(len(values), pywt.Wavelet(wavelet).dec_len)
    coeffs    = pywt.wavedec(values, wavelet, level=max_level)

    for i, c in enumerate(coeffs):
        if i == 0:
            level_fmin = 0.0
            level_fmax = sample_rate / (2 ** max_level)
        else:
            j = max_level - i + 1
            level_fmin = sample_rate / (2 ** (j + 1))
            level_fmax = sample_rate / (2 **  j)

        level_width = level_fmax - level_fmin if level_fmax > level_fmin else 1.0

        # ── Collect gains from all bands that overlap this level ──
        # Weight each band by how much it overlaps the level.
        # This replaces the old gain *= ... loop that accumulated incorrectly.
        weighted_sum   = 0.0
        total_weight   = 0.0

        for band in bands:
            bmin = float(band["freq_min"])
            bmax = float(band["freq_max"])

            overlap = min(level_fmax, bmax) - max(level_fmin, bmin)
            if overlap <= 0:
                continue

            overlap_ratio = overlap / level_width
            if overlap_ratio < 0.05:          # < 5 % overlap → ignore
                continue

            weighted_sum  += float(band.get("gain", 1.0)) * overlap_ratio
            total_weight  += overlap_ratio

        # Weighted mean; fall back to 1.0 (unity) if no band overlaps
        gain = (weighted_sum / total_weight) if total_weight > 0 else 1.0

        coeffs[i] = c * gain

    out = pywt.waverec(coeffs, wavelet)
    return out[: len(values)]   # waverec may return 1 extra sample


# ── Forward-only transforms (no inverse) ─────────────


def compute_fourier_domain(values, sample_rate, bands, n_out=2000):
    """
    Apply gain to FFT coefficients and return the *magnitude spectrum*
    (not the reconstructed time-domain signal).

    Returns:
        dict with keys:
          "type"        : "fourier"
          "frequencies" : list[float]  – frequency axis (Hz)
          "magnitudes"  : list[float]  – |Y(f)| after gain
          "phases"      : list[float]  – angle(Y(f)) in radians
    """
    N  = len(values)
    yf = rfft(values)
    xf = rfftfreq(N, d=1.0 / sample_rate)

    composite = np.ones(len(xf), dtype=np.float64)
    for band in bands:
        gain = float(band.get("gain", 1.0))
        if gain == 1.0:
            continue
        smooth = _smooth_mask(xf, float(band["freq_min"]), float(band["freq_max"]))
        composite += (gain - 1.0) * smooth

    yf_eq = yf * composite
    mags  = np.abs(yf_eq)
    phases = np.angle(yf_eq)

    # Downsample to n_out points for JSON transfer
    if len(xf) > n_out:
        idx    = np.linspace(0, len(xf) - 1, n_out, dtype=int)
        xf     = xf[idx]
        mags   = mags[idx]
        phases = phases[idx]

    return {
        "type":        "fourier",
        "frequencies": _to_list(xf),
        "magnitudes":  _to_list(mags),
        "phases":      _to_list(phases),
    }


def compute_wavelet_domain(values, sample_rate, bands, wavelet="db4", n_out=400):
    """
    Apply gain to wavelet coefficients and return each level's data separately
    so the frontend can draw an independent FFT-style spectrum for every level.

    Returns:
        dict with keys:
          "type"    : "wavelet"
          "wavelet" : str
          "levels"  : list[dict]  – one entry per decomposition level
            Each dict:
              "level"       : int
              "label"       : str   e.g. "A5" (approx) or "D4" (detail)
              "freq_min"    : float (Hz)
              "freq_max"    : float (Hz)
              "gain"        : float
              "color_idx"   : int   – index into frontend COLORS array
              "coefficients": list[float]  – raw scaled coefficients (≤ n_out pts)
              "magnitudes"  : list[float]  – |FFT| of the coefficients (≤ n_out pts)
              "frequencies" : list[float]  – freq axis for the level FFT (Hz)
              "energy_pct"  : float        – % of total energy in this level
    """
    import pywt

    max_level = pywt.dwt_max_level(len(values), pywt.Wavelet(wavelet).dec_len)
    coeffs    = pywt.wavedec(values, wavelet, level=max_level)

    # ── Compute total energy for % ───────────────────
    total_energy = sum(float(np.sum(c ** 2)) for c in coeffs) or 1.0

    levels_out = []
    for i, c in enumerate(coeffs):
        # Frequency range for this level
        if i == 0:
            lf_min, lf_max = 0.0, sample_rate / (2 ** max_level)
            label = f"A{max_level}"   # approximation (lowest freq)
        else:
            j = max_level - i + 1
            lf_min = sample_rate / (2 ** (j + 1))
            lf_max = sample_rate / (2 **  j)
            label  = f"D{j}"          # detail level j

        # Weighted gain from overlapping EQ bands
        level_width  = lf_max - lf_min if lf_max > lf_min else 1.0
        weighted_sum = total_weight = 0.0
        for band in bands:
            bmin, bmax = float(band["freq_min"]), float(band["freq_max"])
            overlap = min(lf_max, bmax) - max(lf_min, bmin)
            if overlap <= 0:
                continue
            ratio = overlap / level_width
            if ratio < 0.05:
                continue
            weighted_sum += float(band.get("gain", 1.0)) * ratio
            total_weight += ratio

        gain      = (weighted_sum / total_weight) if total_weight > 0 else 1.0
        c_scaled  = np.array(c, dtype=np.float64) * gain

        # Energy percentage
        energy_pct = float(np.sum(c_scaled ** 2)) / total_energy * 100.0

        # ── Downsample raw coefficients ──────────────
        c_ds = c_scaled
        if len(c_ds) > n_out:
            idx  = np.linspace(0, len(c_ds) - 1, n_out, dtype=int)
            c_ds = c_ds[idx]
        # Normalise to [-1, 1]
        peak = np.max(np.abs(c_ds)) or 1.0
        c_ds = c_ds / peak

        # ── FFT of this level's coefficients ─────────
        # Use the effective sample rate for this level: sr / 2^level
        level_sr  = sample_rate / (2 ** (i if i > 0 else max_level))
        level_sr  = max(level_sr, 1.0)
        lf        = rfft(c_scaled)
        lxf       = rfftfreq(len(c_scaled), d=1.0 / level_sr)
        lmags     = np.abs(lf)

        if len(lxf) > n_out:
            idx2  = np.linspace(0, len(lxf) - 1, n_out, dtype=int)
            lxf   = lxf[idx2]
            lmags = lmags[idx2]

        # Normalise magnitudes to [0, 1]
        mag_peak = np.max(lmags) or 1.0
        lmags    = lmags / mag_peak

        levels_out.append({
            "level":        i,
            "label":        label,
            "freq_min":     lf_min,
            "freq_max":     lf_max,
            "gain":         gain,
            "color_idx":    i % 16,
            "coefficients": _to_list(c_ds),
            "magnitudes":   _to_list(lmags),
            "frequencies":  _to_list(lxf),
            "energy_pct":   round(energy_pct, 2),
        })

    return {
        "type":    "wavelet",
        "wavelet": wavelet,
        "levels":  levels_out,
    }


def compute_stft_domain(values, sample_rate, bands, n_out=2000):
    """
    Compute the Short-Time Fourier Transform and return the
    magnitude spectrogram — not an inverse STFT.

    Returns:
        dict with keys:
          "type"        : "stft"
          "times"       : list[float]   – time axis (s)
          "frequencies" : list[float]   – frequency axis (Hz)
          "magnitudes"  : list[list[float]]  – |STFT|, shape [n_freq, n_time]
    """
    from scipy.signal import stft as scipy_stft

    nperseg = min(256, len(values) // 4 or 16)
    f, t, Zxx = scipy_stft(values, fs=sample_rate, nperseg=nperseg)

    # Apply gain bands to each frequency bin
    for band in bands:
        gain = float(band.get("gain", 1.0))
        if gain == 1.0:
            continue
        mask = (f >= float(band["freq_min"])) & (f <= float(band["freq_max"]))
        Zxx[mask] *= gain

    mags = np.abs(Zxx)

    # Downsample time axis
    if mags.shape[1] > n_out:
        t_idx = np.linspace(0, mags.shape[1] - 1, n_out, dtype=int)
        mags  = mags[:, t_idx]
        t     = t[t_idx]

    return {
        "type":        "stft",
        "times":       _to_list(t),
        "frequencies": _to_list(f),
        "magnitudes":  [_to_list(row) for row in mags],
    }


def compute_dct_domain(values, sample_rate, bands, n_out=2000):
    """
    Compute the Discrete Cosine Transform and return the coefficient
    spectrum — not an inverse DCT.

    Returns:
        dict with keys:
          "type"         : "dct"
          "frequencies"  : list[float]  – equivalent frequency axis (Hz)
          "coefficients" : list[float]  – DCT coefficients (normalised)
    """
    from scipy.fft import dct

    N    = len(values)
    c    = dct(values, type=2, norm="ortho")
    freq = np.arange(N) * (sample_rate / (2.0 * N))   # DCT bin → Hz

    # Apply gain bands by frequency
    for band in bands:
        mask = (freq >= float(band["freq_min"])) & (freq <= float(band["freq_max"]))
        c[mask] *= float(band.get("gain", 1.0))

    # Downsample
    if N > n_out:
        idx  = np.linspace(0, N - 1, n_out, dtype=int)
        freq = freq[idx]
        c    = c[idx]

    # Normalise
    peak = np.max(np.abs(c)) or 1.0
    c    = c / peak

    return {
        "type":         "dct",
        "frequencies":  _to_list(freq),
        "coefficients": _to_list(c),
    }


# ── Spectrogram ──────────────────────────────────────

AUDIOGRAM_FREQS = [125, 250, 500, 1000, 2000, 4000, 8000]


def compute_spectrogram(values, sample_rate, audiogram_scale=False, max_points=200):
    """
    scipy.signal.spectrogram → dB → optional audiogram re-sampling.
    Returns dict ready for JSON.
    """
    nperseg = min(256, len(values))
    f, t, Sxx = scipy_spectrogram(
        values,
        fs=sample_rate,
        window=hann(nperseg),
        nperseg=nperseg,
        noverlap=nperseg // 2,
    )

    Sxx_db = 10 * np.log10(Sxx + 1e-20)

    if len(t) > max_points:
        idx    = np.linspace(0, len(t) - 1, max_points, dtype=int)
        t      = t[idx]
        Sxx_db = Sxx_db[:, idx]

    if len(f) > max_points:
        idx    = np.linspace(0, len(f) - 1, max_points, dtype=int)
        f      = f[idx]
        Sxx_db = Sxx_db[idx, :]

    scale = "linear"
    if audiogram_scale and sample_rate >= 16000:
        new_Sxx = np.zeros((len(AUDIOGRAM_FREQS), Sxx_db.shape[1]))
        for i, af in enumerate(AUDIOGRAM_FREQS):
            closest      = np.argmin(np.abs(f - af))
            new_Sxx[i,:] = Sxx_db[closest, :]
        f      = np.array(AUDIOGRAM_FREQS, dtype=np.float64)
        Sxx_db = new_Sxx
        scale  = "audiogram"

    return {
        "t":     _to_list(t),
        "f":     _to_list(f),
        "Sxx":   _to_list(Sxx_db),
        "scale": scale,
    }


# ── Downsampling ─────────────────────────────────────


def downsample_signal(times, values, target_points=4000):
    """
    Max-min decimation — preserves peaks.
    Returns (times_list, values_list) as plain Python lists.
    """
    n = len(values)
    if n <= target_points:
        return _to_list(times), _to_list(values)

    chunk = max(1, n // (target_points // 2))
    t_out, v_out = [], []
    for start in range(0, n, chunk):
        end   = min(start + chunk, n)
        seg   = values[start:end]
        i_min = start + int(np.argmin(seg))
        i_max = start + int(np.argmax(seg))
        if i_min < i_max:
            t_out.extend([float(times[i_min]), float(times[i_max])])
            v_out.extend([float(values[i_min]), float(values[i_max])])
        else:
            t_out.extend([float(times[i_max]), float(times[i_min])])
            v_out.extend([float(values[i_max]), float(values[i_min])])

    return t_out[:target_points], v_out[:target_points]


# ── Signal analysis ──────────────────────────────────


def analyze_signal(values, sample_rate, n_components=8):
    """
    Find major frequency components using LOGARITHMIC band spacing.

    Logarithmic spacing matches the mel/bark scale of human hearing:
    the ear resolves low frequencies much finer than high ones.
    Equal-width linear bands devote too many bands to high frequencies
    that carry little perceptual information.

    Returns (components_list, total_energy, dominant_freq, signal_type).
    """
    N  = len(values)
    xf, magnitudes, _ = compute_fft(values, sample_rate)
    total_energy = float(np.sum(magnitudes))

    nyquist = sample_rate / 2.0

    # Determine the lowest meaningful frequency bin (skip DC)
    f_low  = max(20.0, float(xf[1]) if len(xf) > 1 else 20.0)
    f_high = min(nyquist, 20000.0)

    # ── Logarithmic band edges ──────────────────────
    log_edges = np.logspace(
        np.log10(f_low),
        np.log10(f_high),
        n_components + 1
    )

    colors = [
        '#00e5ff', '#10b981', '#f59e0b', '#a78bfa',
        '#f43f5e', '#3b82f6', '#fb923c', '#22d3ee',
        '#e879f9', '#84cc16', '#f97316', '#38bdf8',
        '#a3e635', '#fb7185', '#34d399', '#818cf8',
    ]

    components = []
    for i in range(n_components):
        fmin   = float(log_edges[i])
        fmax   = float(log_edges[i + 1])
        center = float(np.sqrt(fmin * fmax))   # geometric mean

        mask        = (xf >= fmin) & (xf <= fmax)
        comp_energy = float(np.sum(magnitudes[mask]))
        energy_pct  = (comp_energy / total_energy * 100) if total_energy > 0 else 0.0

        components.append({
            "id":          i,
            "label":       f"Comp {i + 1}",
            "freq_center": center,
            "freq_min":    fmin,
            "freq_max":    fmax,
            "energy_pct":  energy_pct,
            "gain":        1.0,
            "color":       colors[i % len(colors)],
            "windows":     [{"freq_min": fmin, "freq_max": fmax}],
        })

    # ── Dominant frequency & signal type ───────────
    dominant_idx = int(np.argmax(magnitudes))
    dom_freq     = float(xf[dominant_idx])

    if dom_freq < 250:
        sig_type = "Low Frequency / Bass"
    elif dom_freq < 2000:
        sig_type = "Mid Range / Voice"
    else:
        sig_type = "High Frequency"

    return components, total_energy, dom_freq, sig_type


# ── Signal decomposition ─────────────────────────────


def decompose_signal(values, sample_rate, components):
    """
    Extract each component's time-series via band-pass FFT filtering.
    Returns a list of {id, label, values, color}.
    """
    N  = len(values)
    yf = rfft(values)
    xf = rfftfreq(N, d=1.0 / sample_rate)

    decomposed = []
    for comp in components:
        mask = np.zeros(len(xf), dtype=bool)
        for win in comp.get("windows", []):
            mask |= (xf >= win["freq_min"]) & (xf <= win["freq_max"])

        yf_comp        = np.zeros_like(yf)
        yf_comp[mask]  = yf[mask]
        comp_values    = irfft(yf_comp, n=N)

        _, v_small = downsample_signal(
            np.arange(len(comp_values)), comp_values, 1000
        )

        decomposed.append({
            "id":     comp["id"],
            "label":  comp["label"],
            "values": v_small,
            "color":  comp.get("color", "#ffffff"),
        })

    return decomposed