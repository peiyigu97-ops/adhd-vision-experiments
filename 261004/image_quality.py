"""
STEP 6: Image quality analysis on captured raw frames.

Computes, per frame and averaged across all 10 static frames:
- resolution
- mean brightness
- standard deviation
- min / max pixel value
- contrast (max-min, and std-based)
- percentage of saturated pixels (==0 or ==255)
- histogram

Outputs a composite figure (original + grayscale histogram) per frame-of-interest
to data/processed/, and a summary CSV to data/results/.

Goal: assess whether OV9281 (no IR-cut filter, no dedicated IR illuminator yet)
produces usable eye-region image quality under current ambient lighting.
"""
import os
import csv
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE, "data", "raw")
PROCESSED_DIR = os.path.join(BASE, "data", "processed")
RESULTS_DIR = os.path.join(BASE, "data", "results")
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

def analyze(img):
    mean = float(np.mean(img))
    std = float(np.std(img))
    vmin = int(np.min(img))
    vmax = int(np.max(img))
    contrast_range = vmax - vmin
    total_px = img.size
    saturated_low = int(np.sum(img == 0))
    saturated_high = int(np.sum(img == 255))
    saturated_pct = 100.0 * (saturated_low + saturated_high) / total_px
    return {
        "mean_brightness": round(mean, 2),
        "std_dev": round(std, 2),
        "min_pixel": vmin,
        "max_pixel": vmax,
        "contrast_range": contrast_range,
        "saturated_low_px": saturated_low,
        "saturated_high_px": saturated_high,
        "saturated_pct": round(saturated_pct, 3),
    }

def main():
    files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".png"))
    if not files:
        print(f"No PNG frames found in {RAW_DIR}")
        return

    rows = []
    for fname in files:
        path = os.path.join(RAW_DIR, fname)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  Failed to read {fname}")
            continue
        stats = analyze(img)
        stats["filename"] = fname
        stats["width"] = img.shape[1]
        stats["height"] = img.shape[0]
        rows.append(stats)
        print(f"  {fname}: mean={stats['mean_brightness']} std={stats['std_dev']} "
              f"range=[{stats['min_pixel']},{stats['max_pixel']}] "
              f"saturated={stats['saturated_pct']}%")

    # composite figure (image + histogram) for the first frame only
    first_path = os.path.join(RAW_DIR, files[0])
    img0 = cv2.imread(first_path, cv2.IMREAD_GRAYSCALE)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].imshow(img0, cmap="gray", vmin=0, vmax=255)
    axes[0].set_title(f"Raw frame: {files[0]}")
    axes[0].axis("off")

    axes[1].hist(img0.ravel(), bins=256, range=(0, 255), color="black")
    axes[1].set_title("Grayscale histogram")
    axes[1].set_xlabel("Pixel value")
    axes[1].set_ylabel("Count")

    fig.tight_layout()
    out_fig = os.path.join(PROCESSED_DIR, "image_quality_frame00.png")
    fig.savefig(out_fig, dpi=120)
    plt.close(fig)
    print(f"\nSaved composite figure to {out_fig}")

    # summary CSV
    csv_path = os.path.join(RESULTS_DIR, "image_quality.csv")
    fieldnames = ["filename", "width", "height", "mean_brightness", "std_dev",
                  "min_pixel", "max_pixel", "contrast_range",
                  "saturated_low_px", "saturated_high_px", "saturated_pct"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Saved per-frame stats to {csv_path}")

    # averaged summary
    avg_mean = np.mean([r["mean_brightness"] for r in rows])
    avg_std = np.mean([r["std_dev"] for r in rows])
    avg_sat = np.mean([r["saturated_pct"] for r in rows])
    print("\n--- Averaged across all frames ---")
    print(f"  mean brightness: {avg_mean:.2f} (0-255 scale)")
    print(f"  mean std dev (contrast proxy): {avg_std:.2f}")
    print(f"  mean saturated pixel pct: {avg_sat:.3f}%")

    if avg_mean < 60:
        print("\n  ASSESSMENT: Average brightness is low. Without IR illumination,")
        print("  ambient-light-only capture may produce underexposed eye regions.")
    elif avg_sat > 5:
        print("\n  ASSESSMENT: Significant saturated pixel percentage -- possible")
        print("  overexposure/glare, which can interfere with pupil detection.")
    else:
        print("\n  ASSESSMENT: Brightness and saturation levels are within a")
        print("  reasonable range for further ROI/pupil-detection experiments,")
        print("  but this does NOT guarantee stable pupil segmentation -- eye")
        print("  region occupies a small fraction of the 105 deg FOV frame.")

if __name__ == "__main__":
    main()
