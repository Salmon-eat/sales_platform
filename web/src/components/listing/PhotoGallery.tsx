"use client";

import { useState } from "react";

import type { ListingPhoto } from "@/lib/types";

/** The photos of an ad: one big, the rest as thumbnails under it. */
export function PhotoGallery({ photos, alt }: { photos: ListingPhoto[]; alt: string }) {
  const [current, setCurrent] = useState(0);
  if (!photos.length) return null;
  const shown = photos[Math.min(current, photos.length - 1)];

  return (
    <div className="gallery">
      <div className="gallery__main">
        <img src={shown.path} alt={alt} width={shown.width} height={shown.height} />
      </div>
      {photos.length > 1 && (
        <ul className="gallery__thumbs">
          {photos.map((photo, index) => (
            <li key={photo.path}>
              <button
                type="button"
                className={index === current ? "gallery__thumb gallery__thumb--on" : "gallery__thumb"}
                onClick={() => setCurrent(index)}
                aria-label={`${index + 1}/${photos.length}`}
              >
                <img src={photo.thumb} alt="" loading="lazy" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
