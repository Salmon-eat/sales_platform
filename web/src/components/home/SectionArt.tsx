/**
 * Small "3D" illustrations for the home page section cards: shaded faces, a highlight and a shadow on
 * the ground. Drawn in code (no image files), so they stay sharp at any size and cost nothing to load.
 * Section key -> its picture and hue; an unknown section gets the box.
 */

type Art = { hue: string; draw: (id: string) => React.ReactNode };

const shadow = <ellipse cx="32" cy="56" rx="19" ry="3.2" fill="#16181d" opacity="0.13" />;

/** A top-to-bottom gradient: light upper face, darker lower part. */
function Grad({ id, from, to }: { id: string; from: string; to: string }) {
  return (
    <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stopColor={from} />
      <stop offset="1" stopColor={to} />
    </linearGradient>
  );
}

const ARTS: Record<string, Art> = {
  // work: a briefcase
  empleo: {
    hue: "#ff6a1a",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#ffa15f" to="#ff6a1a" />
        </defs>
        {shadow}
        <path d="M24 22v-4a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v4" fill="none" stroke="#b84812" strokeWidth="4" />
        <rect x="9" y="25" width="46" height="28" rx="7" fill="#c2521a" />
        <rect x="9" y="21" width="46" height="29" rx="7" fill={`url(#${id}a)`} />
        <rect x="9" y="32" width="46" height="3" fill="#e0561a" opacity="0.7" />
        <rect x="27.5" y="29" width="9" height="8" rx="2" fill="#ffe1cc" />
        <rect x="14" y="24.5" width="20" height="3" rx="1.5" fill="#fff" opacity="0.4" />
      </>
    ),
  },
  // real estate: a house
  inmobiliaria: {
    hue: "#3f7fcf",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#8dbaec" to="#4f89cc" />
          <Grad id={`${id}b`} from="#3d73b8" to="#2a5790" />
        </defs>
        {shadow}
        <rect x="41" y="14" width="6" height="12" rx="1" fill="#2a5790" />
        <rect x="15" y="30" width="34" height="23" rx="2" fill={`url(#${id}a)`} />
        <rect x="15" y="50" width="34" height="3.5" rx="1.5" fill="#3a6eab" />
        <path d="M7 33 32 11l25 22-4 3.5L32 18 11 36.5z" fill={`url(#${id}b)`} />
        <rect x="28" y="38" width="8" height="15" rx="1.5" fill="#2a5790" />
        <rect x="19" y="36" width="6.5" height="6.5" rx="1" fill="#e3eefb" />
        <rect x="38.5" y="36" width="6.5" height="6.5" rx="1" fill="#e3eefb" />
        <path d="M14 33.5 32 17.5" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" opacity="0.35" />
      </>
    ),
  },
  // transport: a van
  motor: {
    hue: "#7057d8",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#a595f3" to="#6f56d6" />
        </defs>
        {shadow}
        <rect x="7" y="17" width="31" height="26" rx="3.5" fill={`url(#${id}a)`} />
        <path d="M38 25h9.5l7.5 8.5V43H38z" fill={`url(#${id}a)`} />
        <path d="M41 28.5h5.2l4.8 5.5H41z" fill="#e8e3fc" />
        <rect x="7" y="41" width="48" height="5" rx="2.5" fill="#4b3aa8" />
        <rect x="11" y="20.5" width="20" height="3" rx="1.5" fill="#fff" opacity="0.35" />
        <circle cx="18" cy="47" r="5.5" fill="#2a2a35" />
        <circle cx="18" cy="47" r="2.2" fill="#cfc9ee" />
        <circle cx="45" cy="47" r="5.5" fill="#2a2a35" />
        <circle cx="45" cy="47" r="2.2" fill="#cfc9ee" />
      </>
    ),
  },
  // services: a toolbox
  "servicios-sec": {
    hue: "#1e9c86",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#4fd0b6" to="#1f957f" />
        </defs>
        {shadow}
        <path d="M25 23v-5a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v5" fill="none" stroke="#156e5e" strokeWidth="3.5" />
        <rect x="9" y="27" width="46" height="26" rx="4.5" fill={`url(#${id}a)`} />
        <rect x="8" y="22" width="48" height="9" rx="3.5" fill="#17806e" />
        <rect x="27" y="28" width="10" height="7" rx="2" fill="#f5c451" />
        <rect x="13" y="24.5" width="18" height="2.5" rx="1.25" fill="#fff" opacity="0.3" />
        <rect x="13" y="42" width="38" height="2.5" rx="1.25" fill="#157565" opacity="0.5" />
      </>
    ),
  },
  // the agency's services: a shield with a check
  servicios: {
    hue: "#3b9e35",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#7ed871" to="#3b9e35" />
        </defs>
        {shadow}
        <path d="M32 12l19 6.5V32c0 12-8.5 19.5-19 23.5C21.5 51.5 13 44 13 32V18.5z" fill="#2c7a27" />
        <path d="M32 9l19 6.5V29c0 12-8.5 19.5-19 23.5C21.5 48.5 13 41 13 29V15.5z" fill={`url(#${id}a)`} />
        <path d="M23.5 30.5l6 6 11-12" fill="none" stroke="#fff" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M18 18.5 32 13.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
      </>
    ),
  },
  // things: a parcel, drawn as a cube
  articulos: {
    hue: "#d8912f",
    draw: () => (
      <>
        {shadow}
        <path d="M32 11l21 10.5L32 32 11 21.5z" fill="#f7d08e" />
        <path d="M11 21.5 32 32v23L11 44.5z" fill="#e3a84c" />
        <path d="M53 21.5 32 32v23l21-10.5z" fill="#c68a2f" />
        <path d="M21.5 16.3 42.5 26.8v8" fill="none" stroke="#fff6e4" strokeWidth="4" strokeLinejoin="round" opacity="0.75" />
      </>
    ),
  },
  // animals: a paw
  animales: {
    hue: "#e8577e",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#ffa3b9" to="#e0507a" />
        </defs>
        {shadow}
        <path d="M32 31c7.5 0 13 7.5 13 13.5 0 5-4 7.5-8 7.5-2.5 0-3.5-1.5-5-1.5s-2.5 1.5-5 1.5c-4 0-8-2.5-8-7.5C19 38.5 24.5 31 32 31z" fill={`url(#${id}a)`} />
        <ellipse cx="16" cy="29" rx="5" ry="6.5" transform="rotate(-20 16 29)" fill={`url(#${id}a)`} />
        <ellipse cx="25.5" cy="18.5" rx="5" ry="6.5" transform="rotate(-8 25.5 18.5)" fill={`url(#${id}a)`} />
        <ellipse cx="38.5" cy="18.5" rx="5" ry="6.5" transform="rotate(8 38.5 18.5)" fill={`url(#${id}a)`} />
        <ellipse cx="48" cy="29" rx="5" ry="6.5" transform="rotate(20 48 29)" fill={`url(#${id}a)`} />
        <ellipse cx="28" cy="37" rx="4" ry="2" fill="#fff" opacity="0.4" />
        <ellipse cx="24" cy="15.5" rx="1.8" ry="1.2" fill="#fff" opacity="0.5" />
        <ellipse cx="37" cy="15.5" rx="1.8" ry="1.2" fill="#fff" opacity="0.5" />
      </>
    ),
  },
  // business: an office tower
  negocios: {
    hue: "#5f7394",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#9aabc6" to="#5f7394" />
        </defs>
        {shadow}
        <path d="M16 16l10-5h22l-10 5z" fill="#c3cfe0" />
        <path d="M38 16l10-5v37l-10 6z" fill="#4a5c7a" />
        <rect x="16" y="16" width="22" height="38" fill={`url(#${id}a)`} />
        {[0, 1, 2, 3, 4].map((row) =>
          [0, 1, 2].map((col) => (
            <rect key={`${row}${col}`} x={19.5 + col * 5.5} y={20 + row * 5.8} width="3.8" height="3.6" rx="0.6" fill="#e2eaf5" opacity={row === 1 && col === 2 ? 0.55 : 0.92} />
          )),
        )}
        <rect x="24" y="48" width="6" height="6" fill="#3e4e69" />
      </>
    ),
  },
  // training: a graduation cap
  "formacion-sec": {
    hue: "#4a52c4",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#8a92ee" to="#4c54c6" />
        </defs>
        {shadow}
        <path d="M18 29v10c0 4.5 6.5 8 14 8s14-3.5 14-8V29l-14 6.5z" fill="#353c9c" />
        <path d="M32 13l25 11-25 11L7 24z" fill={`url(#${id}a)`} />
        <path d="M15 24 32 16.5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" opacity="0.35" />
        <path d="M32 24l17 3v12" fill="none" stroke="#f5b83d" strokeWidth="2" strokeLinecap="round" />
        <circle cx="49" cy="41" r="2.8" fill="#f5b83d" />
      </>
    ),
  },
  // community: a megaphone
  comunidad: {
    hue: "#e5484d",
    draw: (id) => (
      <>
        <defs>
          <Grad id={`${id}a`} from="#ff8f80" to="#e0434b" />
        </defs>
        {shadow}
        <path d="M21 38l3.5 12h6l-2.5-10z" fill="#9e2c33" />
        <rect x="8" y="26" width="9" height="13" rx="2.5" fill="#c23a42" />
        <path d="M15 26 40 14v37L15 39z" fill={`url(#${id}a)`} />
        <ellipse cx="40" cy="32.5" rx="4.5" ry="18.5" fill="#b8323a" />
        <path d="M19 27 36 18.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
        <path d="M49 25c2 2 3 4.5 3 7.5s-1 5.5-3 7.5M54 20.5c3 3.3 4.5 7.3 4.5 12s-1.5 8.7-4.5 12" fill="none" stroke="#ff8a3d" strokeWidth="2.5" strokeLinecap="round" />
      </>
    ),
  },
};

export function sectionHue(key: string) {
  return (ARTS[key] ?? ARTS.articulos).hue;
}

export function SectionArt({ sectionKey }: { sectionKey: string }) {
  const art = ARTS[sectionKey] ?? ARTS.articulos;
  // gradient ids live in the page's global id space, so each picture gets its own prefix
  const id = `art-${sectionKey}-`;
  return (
    <svg viewBox="0 0 64 64" width="52" height="52" aria-hidden>
      {art.draw(id)}
    </svg>
  );
}
