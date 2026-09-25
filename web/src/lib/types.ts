// Mirrors api/app/schemas.

export type UserRole = "user" | "manager" | "admin";

export type User = {
  id: number;
  email: string | null;
  name: string | null;
  avatar: string | null;
  lang: string;
  role: UserRole;
};

export type AdminUser = {
  id: number;
  email: string | null;
  name: string | null;
  avatar: string | null;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  active_sessions: number;
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
};

export type Localized = Record<"es" | "en" | "uk" | "ru", string>;

// ---------- public taxonomy / locations (one language) ----------

export type AttributeOption = { value: string; label: string };

/** A field of a category or a tag of a whole section, already in the page language. */
export type AttributeDef = {
  key: string;
  type: "bool" | "enum" | "multi_enum" | "int_range";
  label: string;
  options: AttributeOption[];
  filterable: boolean;
  facet_order: number;
  required: boolean;
  seo_indexable: boolean;
  defined_on: number | null;
};

export type CategoryNode = {
  id: number;
  slug: string;
  slugs: Localized;
  name: string;
  icon: string | null;
  synonyms: string[];
  attributes?: AttributeDef[];
  children: CategoryNode[];
};

export type Taxonomy = {
  sections: {
    key: string;
    slug: string;
    slugs: Localized;
    name: string;
    is_enabled: boolean;
    /** listings: vacancies and ads; services: permanent agency services (catalog + service pages) */
    kind: "listings" | "services";
    attributes?: AttributeDef[];
    categories: CategoryNode[];
  }[];
};

export type LocationRef = { level: string; slug: string; name: string; id?: number | null };

/** Option lists for the application form, prepared on the server. */
export type ApplicationOptions = {
  sectors: { id: number; name: string }[];
  cities: { slug: string; name: string }[];
};

// ---------- listings ----------

export type Lang = "es" | "en" | "uk" | "ru";
export type ListingStatus = "draft" | "pending" | "active" | "paused" | "expired" | "closed" | "rejected";
export type SalaryPeriod = "hour" | "day" | "week" | "month";
export type ListingAction = "publish" | "pause" | "resume" | "close" | "extend";

export type LocationBrief = { id: number; level: string; slug: string; name: string; parent_name: string | null };

export type ListingCategoryRef = { key: string; slug: string; name: string; icon: string | null };

export type ListingCard = {
  id: number;
  slug: string;
  /** without the language prefix: {section}/{offer word}/{slug}-{id} */
  path: string;
  lang: Lang;
  is_translated: boolean;
  title: string;
  section_key: string;
  category: ListingCategoryRef;
  sector: ListingCategoryRef | null;
  location: LocationBrief | null;
  location_scope: "local" | "spain_wide";
  salary_min: number | null;
  salary_max: number | null;
  salary_period: SalaryPeriod | null;
  /** everything outside jobs: the price shown on the card */
  price?: number | null;
  price_period?: SalaryPeriod | null;
  price_kind?: "fixed" | "negotiable" | "free" | "from";
  /** path of the first photo, e.g. /media/2026/09/ab12.jpg */
  photo?: string | null;
  /** paid placement: shown in the top block */
  promoted?: boolean;
  housing: boolean;
  no_language: boolean;
  no_experience: boolean;
  /** "private" = posted by a person about their own thing */
  source: "agency" | "partner" | "employer" | "private";
  /** null for agency listings */
  employer_name: string | null;
  is_urgent: boolean;
  is_pinned: boolean;
  published_at: string | null;
  schedule: string[];
  contract: string | null;
  vacancies: number | null;
  /** features from the listing's attributes, already in the page language */
  tags: CardTag[];
};

export type CardTag = { key: string; label: string; kind: "lang" | "doc" | "ok" | "perk" | "info" };

export type ListingStats = { total: number; today: number };

// ---------- search ----------

export type FacetValue = { value: string; count: number; label: string | null };
export type FacetGroup = { key: string; tier: 2 | 3; label: string | null; type: "bool" | "multi" | "single"; values: FacetValue[] };
export type CategoryFacet = { id: number; slug: string; key: string; name: string; count: number; selected: boolean };
export type PlaceFacet = { slug: string; name: string; count: number; selected: boolean };
export type SelectedCategory = {
  id: number;
  key: string;
  slug: string;
  slugs: Localized;
  name: string;
  parent: SelectedCategory | null;
};
export type SelectedPlace = { slug: string; level: string; name: string; parent_slug: string | null; parent_name: string | null };
export type Relaxation = {
  kind: "attributes" | "radius" | "province" | "spain";
  count: number;
  query: string;
  location: string | null;
  label_value: string | null;
};

export type SearchResponse = {
  items: (ListingCard & { distance_km: number | null })[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  canonical_query: string;
  sort: "relevance" | "new" | "salary";
  category: SelectedCategory | null;
  location: SelectedPlace | null;
  categories: CategoryFacet[];
  places: PlaceFacet[];
  spain_wide: number;
  facets: FacetGroup[];
  understood: { category: SelectedCategory | null; location: SelectedPlace | null; rest_q: string; complete: boolean } | null;
  relaxations: Relaxation[];
  fuzzy: boolean;
};

// ---------- public pages ----------

export type NamedSlug = { key: string; slug: string; name: string };
export type PlaceRef = { slug: string; level: string; name: string; parent_slug: string | null; parent_name: string | null };

export type ResolveOut = {
  /** services: agency services catalog (sector = chosen sector); service: one service (profession = the service) */
  type: "list" | "listing" | "services" | "service" | "redirect" | "not_found";
  redirect: string | null;
  section: NamedSlug | null;
  sector: NamedSlug | null;
  profession: NamedSlug | null;
  feature: "housing" | null;
  location: PlaceRef | null;
  listing_id: number | null;
  listing_state: "active" | "closed" | "closed_noindex" | "gone" | null;
  alternates: Partial<Record<Lang, string>>;
  tier: string | null;
  indexable: boolean;
  count: number | null;
  title_override: string | null;
  description_override: string | null;
};

/** One section as the home page shows it: name, how many live ads, a few category names. */
export type HomeSection = {
  key: string;
  slug: string;
  name: string;
  count: number;
  categories: { slug: string; name: string }[];
};

export type Home = {
  totals: { listings: number; today: number; sections: number };
  sections: HomeSection[];
  /** paid placement */
  promoted: ListingCard[];
  fresh: ListingCard[];
};

export type ListingPhoto = { path: string; thumb: string; width: number; height: number };

/** A firm in the directory. */
export type CompanyCard = {
  id: number;
  slug: string;
  name: string;
  about: string;
  lang: Lang;
  city_name: string | null;
  categories: string[];
  logo: string | null;
  is_verified: boolean;
  rating: number | null;
  reviews_count: number;
  listings_count: number;
};

export type CompanyPageData = CompanyCard & {
  owner_id: number;
  address: string | null;
  hours: string | null;
  site: string | null;
  created_at: string;
  reviews: SellerReview[];
  listings: ListingCard[];
};

export type MyCompany = CompanyPageData & {
  status: "draft" | "pending" | "active" | "rejected" | "hidden";
  reject_reason: string | null;
  reject_note: string | null;
  category_ids: number[];
  city_id: number | null;
  phone: string | null;
  whatsapp: string | null;
  telegram: string | null;
  email: string | null;
  updated_at: string;
};

export type CompanyContact = {
  phone: string | null;
  whatsapp: string | null;
  telegram: string | null;
  email: string | null;
};

/** Who is behind an ad a person posted themselves. */
export type SellerBrief = { id: number; name: string; rating: number | null; reviews_count: number };

export type SellerReview = {
  id: number;
  rating: number;
  text: string;
  reply: string | null;
  replied_at: string | null;
  author_name: string;
  seller_name: string;
  listing_id: number | null;
  created_at: string;
};

export type SellerPageData = {
  id: number;
  name: string;
  since: string;
  rating: number | null;
  reviews_count: number;
  reviews: SellerReview[];
  listings: ListingCard[];
};

/** An ad of the signed-in visitor, in their own area. */
export type MyListingStatus = "draft" | "pending" | "active" | "paused" | "expired" | "closed" | "rejected";

export type MyListing = {
  id: number;
  status: MyListingStatus;
  title: string;
  lang: Lang;
  /** address on the site; only once it is published */
  path: string | null;
  photo: string | null;
  price: number | null;
  price_period: SalaryPeriod | null;
  price_kind: "fixed" | "negotiable" | "free" | "from";
  category_name: string;
  location_name: string | null;
  published_at: string | null;
  expires_at: string | null;
  reject_reason: string | null;
  reject_note: string | null;
  photos_count: number;
  updated_at: string;
};

export type MyListingDetail = MyListing & {
  category_id: number;
  location_id: number | null;
  description: string;
  attributes: Record<string, unknown>;
  contact: Record<string, string>;
  photos: (ListingPhoto & { id: number })[];
};

export type MyLimits = { open: number; max_listings: number; max_photos: number; days: number };

export type LanguageLevel = "a1" | "a2" | "b1" | "b2" | "c1" | "native";
export type Licence = "b" | "c" | "ce" | "d" | "code95" | "adr" | "forklift" | "crane";

/** The candidate's CV, filled in once and sent with one press. */
export type Resume = {
  id: number;
  title: string;
  about: string;
  city_id: number | null;
  city_name: string | null;
  relocate: boolean;
  experience_years: number | null;
  languages: Partial<Record<Lang, LanguageLevel>>;
  licences: Licence[];
  has_car: boolean;
  work_permit: boolean;
  schedule: string[];
  salary_min: number | null;
  salary_period: SalaryPeriod | null;
  is_public: boolean;
  file_name: string | null;
  file_size: number | null;
  updated_at: string;
};

export type ResumeInput = Omit<Resume, "id" | "city_name" | "file_name" | "file_size" | "updated_at">;

/** Somebody who answered one of my vacancies. */
export type Candidate = {
  id: number;
  listing_id: number | null;
  listing_title: string;
  name: string;
  phone: string | null;
  status: ApplicationStatus;
  lang: string;
  comment: string | null;
  answers: { question: string; answer: string }[];
  has_cv: boolean;
  headline: string | null;
  experience_years: number | null;
  licences: string[];
  languages: Record<string, string>;
  notes: { text: string; author: string | null; created_at: string }[];
  created_at: string;
};

/** The seller's contacts, asked for one ad at a time (never part of the page itself). */
export type SellerContact = {
  name: string | null;
  phone: string | null;
  whatsapp: string | null;
  telegram: string | null;
  email: string | null;
  can_chat: boolean;
};

/** One line in a buyer↔seller conversation (the orange window with the managers is ChatMessage). */
export type DirectMessage = {
  id: number;
  mine: boolean;
  text: string;
  created_at: string;
  read_at: string | null;
};

export type Chat = {
  id: number;
  listing_id: number;
  listing_title: string;
  listing_path: string | null;
  listing_photo: string | null;
  other_name: string;
  /** true when I am the one who posted the ad */
  selling: boolean;
  last_text: string;
  last_at: string;
  unread: number;
};

export type ChatDetail = Chat & { messages: DirectMessage[] };

export type ListingQuestionSetting = { key: string; text?: Partial<Record<"es" | "en" | "uk" | "ru", string>> };

/** A ready-made question the manager can tick, in the admin language. */
export type QuestionPreset = { key: string; text: string };

/** A question on the job page, in the visitor's language. */
export type ListingQuestion = { key: string; text: string; options: { value: string; label: string }[] };

export type ListingDetail = ListingCard & {
  /** optional questions to the candidate, answered in the application form */
  questions: ListingQuestion[];
  description: string;
  photos: ListingPhoto[];
  seller?: SellerBrief | null;
  requirements: string | null;
  conditions: string | null;
  original_lang: Lang;
  translations: Lang[];
  schedule: string[];
  contract: string | null;
  salary_monthly_min: number | null;
  vacancies: number | null;
  start_date: string | null;
  duration_months: number | null;
  /** group "tags": section tags (for students, documents...); "category": profession attributes */
  attributes: { key: string; label: string; values: string[]; group: "tags" | "category" }[];
  expires_at: string | null;
  closed_at: string | null;
  state: "active" | "closed" | "closed_noindex" | "gone";
  section_slug: string;
  section_name: string;
  category_path: NamedSlug[];
  location_detail: LocationBrief | null;
  province: PlaceRef | null;
  lat: number | null;
  lon: number | null;
  similar: ListingCard[];
};

export type ContentBlock = { key: string; lang: string; title: string; body: string; data: Record<string, unknown>; updated_at: string };

export type SitemapPage = { items: { path: string; lastmod: string | null; alternates: Partial<Record<Lang, string>> }[]; page: number; pages: number };

export type SuggestProfession ={ slug: string; key: string; section_key: string; name: string; count: number };
export type SuggestPlace = { slug: string; level: string; name: string; parent_name: string | null; count: number };
export type SuggestResponse = {
  professions: SuggestProfession[];
  places: SuggestPlace[];
  combos: { category: SuggestProfession; place: SuggestPlace; count: number }[];
};

export type ListingTranslation = {
  lang: Lang;
  title: string;
  description: string;
  requirements: string | null;
  conditions: string | null;
  slug: string;
  is_machine: boolean;
};

export type AdminListingItem = {
  id: number;
  status: ListingStatus;
  title: string;
  langs: Lang[];
  original_lang: Lang;
  category_name: string;
  sector_name: string | null;
  location: LocationBrief | null;
  location_scope: "local" | "spain_wide";
  salary_min: number | null;
  salary_max: number | null;
  salary_period: SalaryPeriod | null;
  is_pinned: boolean;
  published_at: string | null;
  expires_at: string | null;
  created_by_email: string | null;
  updated_at: string;
  can_edit: boolean;
};

export type AdminListingDetail = {
  id: number;
  status: ListingStatus;
  section_id: number;
  category_id: number;
  location_scope: "local" | "spain_wide";
  location: LocationBrief | null;
  point: { lat: number; lon: number } | null;
  original_lang: Lang;
  salary_min: number | null;
  salary_max: number | null;
  salary_period: SalaryPeriod | null;
  salary_monthly_min: number | null;
  housing: boolean;
  no_language: boolean;
  no_experience: boolean;
  schedule: string[];
  contract: string | null;
  vacancies: number | null;
  start_date: string | null;
  is_urgent: boolean;
  duration_months: number | null;
  attributes: Record<string, unknown>;
  contact: { name?: string; phone?: string; whatsapp?: string; telegram?: string; email?: string };
  /** optional questions to the candidate: a ready-made one by key, or an own one with its text per language */
  questions: ListingQuestionSetting[];
  source: "agency" | "partner" | "employer";
  employer_name: string | null;
  is_pinned: boolean;
  published_at: string | null;
  expires_at: string | null;
  closed_at: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
  translations: ListingTranslation[];
  can_edit: boolean;
};

/** A signed-in visitor (not the team: their area is /admin). */
export type Account = {
  id: number;
  email: string | null;
  name: string | null;
  phone: string | null;
  avatar: string | null;
  lang: string;
  role: string;
  created_at: string;
  /** how the person agreed to hear about waiting messages */
  notify_email?: boolean;
  notify_telegram?: boolean;
  /** the account is linked to Telegram, so notifications there are possible at all */
  has_telegram?: boolean;
};

export type ApplicationStatus = "new" | "in_progress" | "done" | "rejected";

export type AdminApplication = {
  id: number;
  name: string;
  /** null: a site chat message without a phone (reply in the chat) */
  phone: string | null;
  messenger: "phone" | "telegram" | "whatsapp" | "viber";
  status: ApplicationStatus;
  lang: string;
  source: string;
  category_name: string | null;
  location_name: string | null;
  /** the job the candidate responded to */
  listing: AppliedListing | null;
  in_spain: boolean | null;
  comment: string | null;
  notes_count: number;
  created_at: string;
  updated_at: string;
  /** new/in progress without changes for 48 h */
  stale: boolean;
  /** site chat / Telegram messages staff has not read yet */
  unread: number;
  /** the candidate attached a CV */
  has_cv: boolean;
};

export type ChatMessage = { id: number; author: "visitor" | "staff"; text: string; created_at: string };

export type AdminChatMessage = {
  id: number;
  /** note: the team's note in the Telegram topic */
  author: "visitor" | "staff" | "note";
  /** a manager who wrote in Telegram, or the admin user */
  author_name: string | null;
  text: string;
  /** Telegram: text, photo, voice, document... */
  content_type: string | null;
  /** Telegram: did the reply reach the client */
  delivery: "pending" | "delivered" | "failed" | null;
  created_at: string;
};

export type BotInfo = {
  app_id: number;
  title: string | null;
  /** the questionnaire card as plain text */
  card: string | null;
  username: string | null;
  topic_url: string | null;
  manager_name: string | null;
  status: string | null;
};

export type AppliedListing = {
  id: number;
  title: string;
  status: ListingStatus;
  location_name: string | null;
};

export type Traffic = {
  visitors: number;
  sessions: number;
  pageviews: number;
  avg_session_sec: number;
  bounces: number;
  viewed_job: number;
  opened: number;
  sent: number;
};

type Counted<K extends string> = Record<K, string> & { count: number };

export type DashboardListing = {
  id: number;
  status: ListingStatus;
  title: string | null;
  views: number;
  applications: number;
  no_salary: boolean;
};

export type AdminDashboard = {
  days: 1 | 7 | 30 | 90;
  start: string;
  end: string;
  traffic: Traffic;
  traffic_prev: Traffic;
  daily: { day: string; visitors: number; applications: number }[];
  sources: { source: string; visitors: number; applications: number }[];
  campaigns: {
    id: number;
    code: string;
    name: string;
    channel: string;
    cost: string | null;
    is_active: boolean;
    clicks: number;
    visitors: number;
    applications: number;
  }[];
  devices: { key: string; visitors: number }[];
  langs: { key: string; visitors: number }[];
  landing: { path: string; sessions: number }[];
  exits: { path: string; sessions: number }[];
  top_listings: DashboardListing[];
  unanswered_listings: DashboardListing[];
  searches: Counted<"q">[];
  misses: { q: string; lang: string; hits: number }[];
  work: {
    new: number;
    in_progress: number;
    stale: number;
    period: number;
    period_prev: number;
    responses: number;
    callbacks: number;
    done: number;
    rejected: number;
  };
  stale: { id: number; name: string; status: ApplicationStatus; updated_at: string }[];
  by_category: Counted<"name">[];
  by_city: Counted<"name">[];
  listings: {
    active: number;
    active_no_salary: number;
    expiring: number;
    drafts: number;
    active_no_uk: number;
    active_no_ru: number;
  };
};

export type LinkChannel =
  | "blogger"
  | "instagram"
  | "tiktok"
  | "facebook"
  | "telegram"
  | "youtube"
  | "google"
  | "partner"
  | "other";

export type TrackedLink = {
  id: number;
  code: string;
  name: string;
  channel: LinkChannel;
  target_path: string;
  cost: string | null;
  notes: string | null;
  /** false: closed, shown in the history tab */
  is_active: boolean;
  closed_at: string | null;
  created_at: string;
  clicks: number;
  visitors: number;
  applications: number;
  last_click_at: string | null;
};

export type AdminApplicationDetail =AdminApplication & {
  utm: Record<string, string>;
  /** other applications from the same phone */
  history: AdminApplication[];
  notes: { id: number; text: string; created_at: string }[];
  /** the conversation: site chat (the orange window) or the Telegram bot */
  messages: AdminChatMessage[];
  /** an application from the Telegram bot */
  bot: BotInfo | null;
  /** answers to the listing's questions, in the admin language */
  answers: { question: string; answer: string }[];
  /** the candidate's CV */
  files: { id: number; filename: string; size: number; created_at: string }[];
  consent_at: string;
  consent_version: string;
  /** personal data erased (GDPR) */
  anonymized_at: string | null;
  /** applications of this person (same phone), this one included */
  person_applications: number;
};

export type AdminStats = {
  sections: number;
  categories: number;
  attributes: number;
  comunidades: number;
  provincias: number;
  municipios: number;
  localidades: number;
  applications_new: number;
  listings_active: number;
};

export type AdminAttribute = {
  id: number;
  key: string;
  type: "bool" | "enum" | "multi_enum" | "int_range";
  label: Localized;
  options: { value: string; label: Localized }[];
  filterable: boolean;
  facet_order: number;
  required: boolean;
  seo_indexable: boolean;
};

export type AdminCategory = {
  id: number;
  parent_id: number | null;
  slug: Localized;
  name: Localized;
  synonyms: Partial<Record<keyof Localized, string[]>>;
  icon: string | null;
  sort: number;
  is_enabled: boolean;
  attributes: AdminAttribute[];
  children: AdminCategory[];
};

export type AdminSection = {
  id: number;
  key: string;
  slug: Localized;
  name: Localized;
  is_enabled: boolean;
  kind: "listings" | "services";
  sort: number;
  /** listing tags of the whole section (for students, documents, languages...) */
  attributes: AdminAttribute[];
  categories: AdminCategory[];
};

export type LocationLevel = "comunidad" | "provincia" | "municipio" | "localidad";

export type AdminLocation = {
  id: number;
  level: LocationLevel;
  slug: string;
  ine_code: string;
  names: Partial<Localized> & { es: string };
  aliases: string[];
  population: number | null;
  lat: number | null;
  lon: number | null;
  parent_name: string | null;
};
