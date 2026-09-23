import { ArrowRight, ChefHat, HardHat, Pointer, Truck } from "lucide-react";
import Link from "next/link";

/** Scene 3 jobs: a driver, a waiter, a builder — the platform is about all kinds of work. */
const JOB_ICONS = [Truck, ChefHat, HardHat];
/** The builder is picked: the mascot wears a hard hat, and scene 4 pays this job's salary. */
const PICKED = 2;

/**
 * Hero picture: the candidate's way in four looping scenes — a request in two minutes, the manager's
 * call, going to work, the salary and the life they wanted. Pure SVG + CSS (no JS); with "reduce
 * motion" only the last scene is shown.
 */

type Texts = {
  steps: { title: string; text: string }[];
  send: string;
  minutes: string;
  manager: string;
  bubble: [string, string];
  jobs: { title: string; salary: string }[];
  salary: string;
  amount: string;
  cta: string;
};

/**
 * Our own mascot: an orange-head (a Valencian orange with a leaf) in a sea-green suit, with bendy
 * "noodle" limbs and white cartoon gloves. Props dress it up for each scene.
 */
function Person({
  x,
  y,
  scale = 1,
  pose = "stand",
  hat = false,
  shades = false,
  walking = false,
}: {
  x: number;
  y: number;
  scale?: number;
  pose?: "stand" | "point" | "cheer";
  hat?: boolean;
  shades?: boolean;
  walking?: boolean;
}) {
  const limb = {
    stroke: "#1d5f66",
    strokeWidth: 6,
    strokeLinecap: "round" as const,
    fill: "none",
  };
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <g
        className={`person person--${pose}${walking ? " person--walking" : ""}`}
      >
        {/* legs + shoes */}
        <g className="person__leg person__leg--a">
          <path d="M-6 -32 q-3 16 -2 30" {...limb} />
          <ellipse cx="-10" cy="0" rx="7" ry="4" fill="#16181d" />
        </g>
        <g className="person__leg person__leg--b">
          <path d="M6 -32 q3 16 2 30" {...limb} />
          <ellipse cx="10" cy="0" rx="7" ry="4" fill="#16181d" />
        </g>
        {/* arms: noodles with white gloves */}
        <g className="person__arm person__arm--a">
          <path d="M-12 -58 q-12 10 -10 26" {...limb} />
          <circle
            cx="-22"
            cy="-30"
            r="5"
            fill="#ffffff"
            stroke="#16181d"
            strokeWidth="1.5"
          />
        </g>
        <g className="person__arm person__arm--b">
          <path d="M12 -58 q12 10 10 26" {...limb} />
          <circle
            cx="22"
            cy="-30"
            r="5"
            fill="#ffffff"
            stroke="#16181d"
            strokeWidth="1.5"
          />
        </g>
        {/* body: a capsule suit with a white collar */}
        <rect x="-15" y="-66" width="30" height="38" rx="15" fill="#23808a" />
        <path d="M-6 -65 l6 8 l6 -8" fill="#ffffff" />
        <circle cx="0" cy="-48" r="1.6" fill="#ffffff" />
        <circle cx="0" cy="-40" r="1.6" fill="#ffffff" />
        {/* the orange head */}
        <circle cx="0" cy="-86" r="20" fill="#ff8a1f" />
        <circle cx="0" cy="-86" r="20" fill="url(#orange-shade)" />
        {[
          [-9, -96],
          [8, -99],
          [12, -80],
          [-13, -82],
          [2, -72],
        ].map(([cx, cy]) => (
          <circle key={`${cx}${cy}`} cx={cx} cy={cy} r="0.9" fill="#e06d0c" />
        ))}
        <ellipse
          cx="-8"
          cy="-96"
          rx="5"
          ry="3"
          fill="#ffffff"
          opacity="0.35"
          transform="rotate(-30 -8 -96)"
        />
        {!hat && (
          <>
            <path
              d="M0 -106 q1 -6 -1 -9"
              stroke="#6b4a2a"
              strokeWidth="2.2"
              strokeLinecap="round"
              fill="none"
            />
            <path d="M0 -110 q9 -9 17 -3 q-8 7 -17 3 z" fill="#3fae5a" />
          </>
        )}
        {/* face */}
        {shades ? (
          <g>
            <rect
              x="-13"
              y="-92"
              width="11"
              height="8"
              rx="3.5"
              fill="#16181d"
            />
            <rect x="2" y="-92" width="11" height="8" rx="3.5" fill="#16181d" />
            <path d="M-2 -89 h4" stroke="#16181d" strokeWidth="2" />
            <path
              d="M-11 -90.5 l3 -1"
              stroke="#ffffff"
              strokeWidth="1.2"
              strokeLinecap="round"
              opacity="0.7"
            />
          </g>
        ) : (
          <g>
            <ellipse cx="-7" cy="-88" rx="2.3" ry="3.3" fill="#16181d" />
            <ellipse cx="7" cy="-88" rx="2.3" ry="3.3" fill="#16181d" />
            <circle cx="-6.2" cy="-89.3" r="0.9" fill="#ffffff" />
            <circle cx="7.8" cy="-89.3" r="0.9" fill="#ffffff" />
          </g>
        )}
        <circle cx="-12" cy="-80" r="3" fill="#ff5d7a" opacity="0.45" />
        <circle cx="12" cy="-80" r="3" fill="#ff5d7a" opacity="0.45" />
        {pose === "cheer" ? (
          <path d="M-5 -79 q5 7 10 0 z" fill="#7a2a12" />
        ) : (
          <path
            d="M-4 -79 q4 4 8 0"
            stroke="#7a2a12"
            strokeWidth="1.8"
            strokeLinecap="round"
            fill="none"
          />
        )}
        {hat && (
          <g>
            <path d="M-19 -96 a19 17 0 0 1 38 0 z" fill="#ffc23a" />
            <rect
              x="-23"
              y="-98"
              width="46"
              height="5"
              rx="2.5"
              fill="#f0a818"
            />
            <rect x="-3" y="-112" width="6" height="15" rx="3" fill="#ffd566" />
          </g>
        )}
      </g>
    </g>
  );
}

/** The manager on the call: a lemon with a headset. */
function Lemon() {
  return (
    <g>
      <path
        d="M204 122 q4 -34 36 -34 q32 0 36 34 q-4 34 -36 34 q-32 0 -36 -34 z"
        fill="#ffd23f"
      />
      <path d="M204 122 l-7 -3 l1 7 z M276 122 l7 -3 l-1 7 z" fill="#ffd23f" />
      <ellipse
        cx="226"
        cy="104"
        rx="8"
        ry="4"
        fill="#ffffff"
        opacity="0.4"
        transform="rotate(-25 226 104)"
      />
      <path d="M240 88 q10 -12 22 -6 q-10 10 -22 6 z" fill="#3fae5a" />
      <ellipse cx="230" cy="122" rx="2.6" ry="3.8" fill="#16181d" />
      <ellipse cx="250" cy="122" rx="2.6" ry="3.8" fill="#16181d" />
      <circle cx="231" cy="120.5" r="1" fill="#ffffff" />
      <circle cx="251" cy="120.5" r="1" fill="#ffffff" />
      <circle cx="222" cy="132" r="3.5" fill="#ff8a1f" opacity="0.45" />
      <circle cx="258" cy="132" r="3.5" fill="#ff8a1f" opacity="0.45" />
      <path
        d="M232 134 q8 7 16 0"
        stroke="#7a4a12"
        strokeWidth="2.4"
        fill="none"
        strokeLinecap="round"
      />
      <path
        d="M206 116 a34 34 0 0 1 68 0"
        stroke="#16181d"
        strokeWidth="3.5"
        fill="none"
      />
      <rect x="199" y="112" width="10" height="16" rx="5" fill="#16181d" />
      <rect x="271" y="112" width="10" height="16" rx="5" fill="#16181d" />
      <path
        d="M276 128 q0 16 -18 18"
        stroke="#16181d"
        strokeWidth="2.5"
        fill="none"
      />
      <circle cx="257" cy="146" r="3" fill="#16181d" />
    </g>
  );
}

function Phone({ children }: { children: React.ReactNode }) {
  return (
    <g>
      <rect
        x="170"
        y="36"
        width="140"
        height="256"
        rx="24"
        fill="#2a2d35"
        stroke="#3b3f4a"
        strokeWidth="2"
      />
      <rect x="229" y="44" width="22" height="5" rx="2.5" fill="#3b3f4a" />
      {children}
    </g>
  );
}

export function HeroStory({ texts, href }: { texts: Texts; href: string }) {
  return (
    <div className="story">
      <svg
        className="story__art"
        viewBox="0 0 480 320"
        role="img"
        aria-label={texts.steps.map((s) => s.title).join(" → ")}
      >
        <defs>
          <radialGradient id="orange-shade" cx="0.35" cy="0.3" r="0.8">
            <stop offset="0.55" stopColor="#ff8a1f" stopOpacity="0" />
            <stop offset="1" stopColor="#d9620a" stopOpacity="0.55" />
          </radialGradient>
        </defs>
        {/* soft backdrop instead of a framed tile; one group opacity, so overlapping shapes stay one tone */}
        <g className="story-blob">
          <ellipse cx="240" cy="178" rx="200" ry="140" />
          <ellipse cx="392" cy="96" rx="64" ry="54" />
        </g>
        {/* 1. request in two minutes */}
        <g className="story-scene story-s1">
          <Phone>
            <rect
              x="180"
              y="56"
              width="120"
              height="224"
              rx="14"
              fill="#ffffff"
            />
            <text x="192" y="80" className="story__brand">
              cito<tspan fill="#ff6a1a">bazar</tspan>
            </text>
            <rect x="192" y="96" width="96" height="24" rx="7" fill="#f1efe8" />
            <rect
              className="story-type story-type--1"
              x="199"
              y="106"
              width="58"
              height="4"
              rx="2"
              fill="#16181d"
            />
            <rect
              x="192"
              y="130"
              width="96"
              height="24"
              rx="7"
              fill="#f1efe8"
            />
            <rect
              className="story-type story-type--2"
              x="199"
              y="140"
              width="70"
              height="4"
              rx="2"
              fill="#16181d"
            />
            <rect
              x="192"
              y="164"
              width="44"
              height="18"
              rx="9"
              fill="#16181d"
            />
            <rect
              x="240"
              y="164"
              width="44"
              height="18"
              rx="9"
              fill="#f1efe8"
            />
            <rect
              className="story-button"
              x="192"
              y="196"
              width="96"
              height="28"
              rx="9"
              fill="#ff6a1a"
            />
            <text
              x="240"
              y="214"
              textAnchor="middle"
              className="story__button-text"
            >
              {texts.send}
            </text>
            <g transform="translate(240 252)">
              <g className="story-check">
                <circle r="15" fill="#34c759" />
                <path
                  d="M-7 0 l5 5 l9 -10"
                  stroke="#fff"
                  strokeWidth="3"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </g>
            </g>
          </Phone>
          <g className="story-badge" transform="translate(338 92)">
            <rect
              className="story-card"
              x="0"
              y="0"
              width="84"
              height="30"
              rx="15"
            />
            <circle
              cx="16"
              cy="15"
              r="7"
              fill="none"
              stroke="#ff6a1a"
              strokeWidth="2"
            />
            <path
              d="M16 11 v4 l3 2"
              stroke="#ff6a1a"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
            />
            <text x="30" y="20" className="story__small-dark">
              {texts.minutes}
            </text>
          </g>
          <Person x={100} y={290} scale={1.3} pose="point" />
        </g>

        {/* 2. the manager calls back */}
        <g className="story-scene story-s2">
          <g className="story-ring">
            <path
              d="M150 120 q-22 44 0 88"
              stroke="#ff6a1a"
              strokeWidth="4"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M130 106 q-32 58 0 116"
              stroke="#ff6a1a"
              strokeWidth="4"
              fill="none"
              strokeLinecap="round"
              opacity="0.5"
            />
          </g>
          <g className="story-shake">
            <Phone>
              <rect
                x="180"
                y="56"
                width="120"
                height="224"
                rx="14"
                fill="#1f2229"
              />
              <Lemon />
              <text
                x="240"
                y="176"
                textAnchor="middle"
                className="story__light"
              >
                {texts.manager}
              </text>
              <text
                x="240"
                y="194"
                textAnchor="middle"
                className="story__muted"
              >
                Citobazar
              </text>
              <circle
                className="story-pulse"
                cx="240"
                cy="242"
                r="20"
                fill="#34c759"
                opacity="0.35"
              />
              <circle cx="240" cy="242" r="18" fill="#34c759" />
              <path
                transform="translate(229.8 231.8) scale(0.85)"
                d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"
                fill="#fff"
              />
            </Phone>
          </g>
          <g className="story-bubble" transform="translate(300 60)">
            <rect
              className="story-card"
              x="0"
              y="0"
              width="170"
              height="58"
              rx="16"
            />
            <path d="M18 56 l-10 16 l24 -16 z" fill="#ffffff" />
            <text x="16" y="25" className="story__bubble">
              {texts.bubble[0]}
            </text>
            <text x="16" y="44" className="story__bubble story__bubble--accent">
              {texts.bubble[1]}
            </text>
          </g>
        </g>

        {/* 3. going to work */}
        <g className="story-scene story-s3">
          <rect
            className="story-ground"
            x="0"
            y="286"
            width="480"
            height="4"
            rx="2"
          />
          {/* several jobs pop up, the candidate walks to them and one is picked */}
          {texts.jobs.map((job, i) => {
            const Icon = JOB_ICONS[i];
            const y = 40 + i * 76;
            return (
              <g key={job.title} className={`story-job story-job--${i + 1}`}>
                <rect
                  className="story-card"
                  x="206"
                  y={y}
                  width="258"
                  height="62"
                  rx="14"
                />
                <circle cx="238" cy={y + 31} r="19" fill="#fff1e6" />
                <Icon
                  x={227}
                  y={y + 20}
                  width={22}
                  height={22}
                  color="#c2521a"
                  strokeWidth={2}
                />
                <text x="268" y={y + 27} className="story__job-title">
                  {job.title}
                </text>
                <text x="268" y={y + 47} className="story__job-salary">
                  {job.salary}
                </text>
                {i === PICKED && (
                  <g className="story-pick">
                    <rect
                      x="206"
                      y={y}
                      width="258"
                      height="62"
                      rx="14"
                      fill="none"
                      stroke="#ff6a1a"
                      strokeWidth="2.5"
                    />
                    <circle cx="440" cy={y + 31} r="12" fill="#34c759" />
                    <path
                      d={`M434 ${y + 31} l4 4 l8 -8`}
                      stroke="#fff"
                      strokeWidth="2.6"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </g>
                )}
              </g>
            );
          })}
          <g className="story-walk">
            <Person x={50} y={290} scale={1.35} hat walking />
          </g>
          {/* the mascot's white glove flies in and taps the chosen job */}
          <g className="story-hand">
            <Pointer
              x={390}
              y={220}
              width={32}
              height={32}
              fill="#ffffff"
              color="#16181d"
              strokeWidth={1.6}
            />
          </g>
        </g>

        {/* 4. salary and the life they wanted */}
        <g className="story-scene story-s4">
          <circle cx="420" cy="70" r="34" fill="#fde9b8" />
          <circle cx="420" cy="70" r="22" fill="#ffc23a" />
          <rect
            className="story-ground"
            x="0"
            y="286"
            width="480"
            height="4"
            rx="2"
          />
          <g>
            <path d="M52 204 l58 -44 l58 44 z" fill="#ff6a1a" />
            <rect
              className="story-card"
              x="64"
              y="204"
              width="92"
              height="82"
            />
            <rect
              x="100"
              y="240"
              width="22"
              height="46"
              rx="3"
              fill="#c2521a"
            />
            <rect x="74" y="220" width="18" height="18" rx="3" fill="#ffd37a" />
            <rect
              x="130"
              y="220"
              width="18"
              height="18"
              rx="3"
              fill="#ffd37a"
            />
            <path
              className="story-heart"
              d="M110 140 c-6 -8 -18 -4 -16 5 c2 7 16 15 16 15 c0 0 14 -8 16 -15 c2 -9 -10 -13 -16 -5 z"
              fill="#ff6a1a"
            />
          </g>
          <g>
            <path
              d="M392 286 q6 -50 -6 -96"
              stroke="#8a5a3c"
              strokeWidth="9"
              fill="none"
              strokeLinecap="round"
            />
            {/* a full crown: eleven fronds, the lowest ones drooping around the top of the trunk */}
            <g className="story-palm" transform="translate(386 190)">
              {[-168, -145, -120, -95, -70, -45, -20, 5, 30, 150, 172].map(
                (angle, i) => (
                  <path
                    key={angle}
                    transform={`rotate(${angle})`}
                    d="M0 0 q22 -12 50 -2 q4 2 6 6 q-8 -3 -14 -1 q-4 -4 -10 -3 q-5 3 -10 1 q-6 -2 -12 1 q-6 0 -10 -2 z"
                    fill={i % 2 ? "#35994d" : "#43b862"}
                  />
                ),
              )}
              <circle cx="-5" cy="6" r="5" fill="#7a4a2a" />
              <circle cx="5" cy="7" r="5" fill="#8a5a3c" />
              <circle cx="0" cy="12" r="4.5" fill="#6b3f22" />
            </g>
          </g>
          <Person x={262} y={288} scale={1.35} pose="cheer" shades />
          {[
            [226, 0],
            [300, 0.5],
            [262, 1],
          ].map(([cx, delay]) => (
            <g
              key={cx}
              className="story-coin"
              style={{ animationDelay: `${delay}s` }}
            >
              <circle cx={cx} cy="118" r="10" fill="#ffc23a" />
              <text x={cx} y="122" textAnchor="middle" className="story__coin">
                €
              </text>
            </g>
          ))}
          <g className="story-note">
            <g transform="translate(120 28)">
              <rect
                x="0"
                y="0"
                width="240"
                height="64"
                rx="16"
                className="story-card"
              />
              <circle cx="32" cy="32" r="18" fill="#e3f4dc" />
              <text x="32" y="38" textAnchor="middle" className="story__euro">
                €
              </text>
              <text x="60" y="26" className="story__small-muted">
                {texts.salary}
              </text>
              <text x="60" y="48" className="story__amount">
                {texts.amount}
              </text>
            </g>
          </g>
        </g>
      </svg>

      <ol className="story__steps">
        {texts.steps.map((s, i) => (
          <li key={s.title} className={`story-caption story-s${i + 1}`}>
            <span className="story__num">{i + 1}/4</span>
            <strong>{s.title}</strong>
            <span>{s.text}</span>
          </li>
        ))}
      </ol>
      <div className="story__progress" aria-hidden>
        {texts.steps.map((s, i) => (
          <span key={s.title}>
            <i className={`story-bar story-b${i + 1}`} />
          </span>
        ))}
      </div>
      <Link href={href} className="story__cta">
        {texts.cta} <ArrowRight size={16} aria-hidden />
      </Link>
    </div>
  );
}
