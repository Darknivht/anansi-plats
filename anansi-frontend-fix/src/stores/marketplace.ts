/**
 * Marketplace Zustand Store — Browse, search, install, reviews, categories.
 *
 * Manages marketplace state: listings, search, filters, categories, featured,
 * installation flow, and reviews.
 */

import { create } from "zustand";
import { api } from "../lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface MarketplaceListing {
  id: string;
  agent_id: string | null;
  user_id: string;
  title: string;
  description: string | null;
  price_cents: number;
  price_display: string;
  category: string | null;
  tags: string[];
  screenshots: string[];
  rating_avg: number;
  rating_count: number;
  install_count: number;
  status: string;
  is_featured: boolean;
  agent_name: string | null;
  agent_version: number | null;
  memory_nodes_per_run: number | null;
  memory_links_per_run: number | null;
  rejection_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MarketplaceListingDetail extends MarketplaceListing {
  version_history: {
    version: number;
    created_at: string;
    change_notes: string | null;
  }[];
  creator: {
    id: string | null;
    display_name: string;
    avatar_url: string | null;
  };
  reviews: MarketplaceReview[];
}

export interface MarketplaceReview {
  id: string;
  listing_id: string;
  user_id: string;
  rating: number;
  review: string | null;
  created_at: string | null;
  reviewer_name?: string;
  listing_title?: string;
}

export interface MarketplaceCategory {
  slug: string;
  display_name: string;
  count: number;
}

export interface PaginatedResponse {
  items: MarketplaceListing[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// ─── Filter / Sort Types ──────────────────────────────────────────────────

export type SortOption = "popular" | "newest" | "rating" | "price_low" | "price_high";

export interface MarketplaceFilters {
  category: string | null;
  tags: string[];
  sort: SortOption;
  price_min: number | null;
  price_max: number | null;
  price_free: boolean | null;
  search: string;
}

// ─── Creator Dashboard Types ──────────────────────────────────────────────

export interface CreatorListing {
  id: string;
  agent_id: string | null;
  title: string;
  description: string | null;
  price_cents: number;
  price_display: string;
  category: string | null;
  status: string;
  is_featured: boolean;
  rating_avg: number;
  rating_count: number;
  install_count: number;
  is_published: boolean;
  estimated_earnings_cents: number;
  agent_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SalesAnalytics {
  period: string;
  total_installs: number;
  total_installs_all_time: number;
  total_reviews: number;
  average_rating: number;
  total_revenue_cents: number;
  total_platform_fees_cents: number;
  top_listing: {
    title: string | null;
    installs: number;
    price_cents: number;
  } | null;
  installs_over_time: {
    date: string;
    installs: number;
  }[];
}

export interface EarningsData {
  total_revenue_cents: number;
  total_earnings_cents: number;
  total_earnings_display: string;
  platform_fees_cents: number;
  platform_fees_display: string;
  pending_payout_cents: number;
  pending_payout_display: string;
  total_installs: number;
  paid_installs: number;
  free_installs: number;
  listings_count: number;
  payout_history: {
    id: string;
    amount_cents: number;
    amount_display: string;
    status: string;
    paid_at: string;
    period: string;
  }[];
  revenue_share: {
    creator_percentage: number;
    platform_percentage: number;
  };
}

// ─── Store Interface ─────────────────────────────────────────────────────

interface MarketplaceState {
  // Listing data
  listings: MarketplaceListing[];
  totalListings: number;
  currentPage: number;
  totalPages: number;

  // Detail
  selectedListing: MarketplaceListingDetail | null;

  // Categories
  categories: MarketplaceCategory[];
  featuredListings: MarketplaceListing[];

  // Filters
  filters: MarketplaceFilters;

  // Loading states
  isLoading: boolean;
  isInstalling: boolean;
  isSubmittingReview: boolean;
  error: string | null;

  // Creator dashboard
  myListings: CreatorListing[];
  analytics: SalesAnalytics | null;
  earnings: EarningsData | null;
  creatorReviews: MarketplaceReview[];

  // Actions
  fetchListings: (page?: number) => Promise<void>;
  fetchListingDetail: (id: string) => Promise<void>;
  installAgent: (listingId: string) => Promise<{ agent: { id: string; name: string } } | null>;
  submitReview: (listingId: string, rating: number, review?: string) => Promise<void>;
  fetchCategories: () => Promise<void>;
  fetchFeatured: () => Promise<void>;
  searchListings: (query: string, page?: number) => Promise<void>;
  setFilters: (filters: Partial<MarketplaceFilters>) => void;
  clearFilters: () => void;

  // Creator actions
  fetchMyListings: () => Promise<void>;
  fetchAnalytics: (period?: string) => Promise<void>;
  fetchEarnings: () => Promise<void>;
  fetchCreatorReviews: () => Promise<void>;
}

// ─── Initial Filters ────────────────────────────────────────────────────

const DEFAULT_FILTERS: MarketplaceFilters = {
  category: null,
  tags: [],
  sort: "popular",
  price_min: null,
  price_max: null,
  price_free: null,
  search: "",
};

// ─── Store ─────────────────────────────────────────────────────────────

export const useMarketplaceStore = create<MarketplaceState>((set, get) => ({
  // ── State ──
  listings: [],
  totalListings: 0,
  currentPage: 1,
  totalPages: 0,
  selectedListing: null,
  categories: [],
  featuredListings: [],
  filters: { ...DEFAULT_FILTERS },
  isLoading: false,
  isInstalling: false,
  isSubmittingReview: false,
  error: null,

  myListings: [],
  analytics: null,
  earnings: null,
  creatorReviews: [],

  // ── Actions ──

  fetchListings: async (page?: number) => {
    const { filters } = get();
    set({ isLoading: true, error: null });

    try {
      const params: Record<string, string | number | boolean> = {
        page: page ?? get().currentPage,
        limit: 20,
        sort: filters.sort,
      };
      if (filters.category) params.category = filters.category;
      if (filters.price_min !== null) params.price_min = filters.price_min;
      if (filters.price_max !== null) params.price_max = filters.price_max;
      if (filters.tags.length > 0) params.tags = filters.tags.join(",");

      const data = await api.get<PaginatedResponse>("/api/v1/marketplace", { params });

      set({
        listings: data.items,
        totalListings: data.total,
        currentPage: data.page,
        totalPages: data.pages,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load marketplace";
      set({ isLoading: false, error: message });
    }
  },

  fetchListingDetail: async (id: string) => {
    set({ isLoading: true, error: null, selectedListing: null });

    try {
      const data = await api.get<MarketplaceListingDetail>(`/api/v1/marketplace/${id}`);
      set({ selectedListing: data, isLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load listing";
      set({ isLoading: false, error: message });
    }
  },

  installAgent: async (listingId: string) => {
    set({ isInstalling: true, error: null });

    try {
      const data = await api.post<{ agent: { id: string; name: string } }>(
        `/api/v1/marketplace/${listingId}/install`
      );

      // Update local listing count
      const { listings, selectedListing } = get();
      set({
        listings: listings.map(l =>
          l.id === listingId ? { ...l, install_count: l.install_count + 1 } : l
        ),
        selectedListing: selectedListing?.id === listingId
          ? { ...selectedListing, install_count: selectedListing.install_count + 1 }
          : selectedListing,
        isInstalling: false,
      });

      return data;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to install agent";
      set({ isInstalling: false, error: message });
      return null;
    }
  },

  submitReview: async (listingId: string, rating: number, review?: string) => {
    set({ isSubmittingReview: true, error: null });

    try {
      const data = await api.post<MarketplaceReview>(
        `/api/v1/marketplace/${listingId}/review`,
        { rating, review }
      );

      // Reload detail to get updated reviews
      get().fetchListingDetail(listingId);
      set({ isSubmittingReview: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to submit review";
      set({ isSubmittingReview: false, error: message });
    }
  },

  fetchCategories: async () => {
    try {
      const data = await api.get<MarketplaceCategory[]>("/api/v1/marketplace/categories");
      set({ categories: data });
    } catch {
      // Non-critical, silently fail
    }
  },

  fetchFeatured: async () => {
    try {
      const data = await api.get<MarketplaceListing[]>("/api/v1/marketplace/featured");
      set({ featuredListings: data });
    } catch {
      // Non-critical
    }
  },

  searchListings: async (query: string, page?: number) => {
    set({ isLoading: true, error: null });

    try {
      const params: Record<string, string | number | boolean> = {
        q: query,
        page: page ?? 1,
        limit: 20,
      };

      const { filters } = get();
      if (filters.category) params.category = filters.category;
      if (filters.price_free !== null) params.price_free = filters.price_free;

      const data = await api.get<PaginatedResponse>("/api/v1/marketplace/search", { params });

      set({
        listings: data.items,
        totalListings: data.total,
        currentPage: data.page,
        totalPages: data.pages,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Search failed";
      set({ isLoading: false, error: message });
    }
  },

  setFilters: (filters: Partial<MarketplaceFilters>) => {
    set(state => ({
      filters: { ...state.filters, ...filters },
      currentPage: 1, // Reset to first page on filter change
    }));
    // Auto-fetch with new filters
    get().fetchListings(1);
  },

  clearFilters: () => {
    set({ filters: { ...DEFAULT_FILTERS }, currentPage: 1 });
    get().fetchListings(1);
  },

  // ── Creator Actions ──

  fetchMyListings: async () => {
    try {
      const data = await api.get<CreatorListing[]>("/api/v1/marketplace/my-listings");
      set({ myListings: data });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load listings";
      set({ error: message });
    }
  },

  fetchAnalytics: async (period?: string) => {
    try {
      const params: Record<string, string> = {};
      if (period) params.period = period;

      const data = await api.get<SalesAnalytics>("/api/v1/marketplace/analytics", { params });
      set({ analytics: data });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load analytics";
      set({ error: message });
    }
  },

  fetchEarnings: async () => {
    try {
      const data = await api.get<EarningsData>("/api/v1/marketplace/earnings");
      set({ earnings: data });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load earnings";
      set({ error: message });
    }
  },

  fetchCreatorReviews: async () => {
    try {
      const data = await api.get<MarketplaceReview[]>("/api/v1/marketplace/reviews");
      set({ creatorReviews: data });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load reviews";
      set({ error: message });
    }
  },
}));
