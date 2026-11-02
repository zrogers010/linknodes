/**
 * Shared SEO / social-preview constants.
 * Imported by prerender.js and the React SEO component so tags stay in one place.
 */
export const SITE_URL = 'https://www.linknodes.io'
export const SITE_NAME = 'LinkNodes.io'

/**
 * X/Twitter @handle for twitter:site.
 * Leave empty until the account exists — tags that use this value are omitted.
 * Example once live: '@linknodes'
 */
export const TWITTER_SITE = ''

export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-default.png`

/** Per-page Open Graph images for the launch surfaces that get shared on X. */
export const PAGE_OG_IMAGES = {
  '/agents': `${SITE_URL}/og-agents.png`,
  '/rwa': `${SITE_URL}/og-rwa.png`,
  '/chainlink-247': `${SITE_URL}/og-chainlink-247.png`,
  '/feeds': `${SITE_URL}/og-feeds.png`,
}

export function ogImageForPath(path) {
  if (!path) return DEFAULT_OG_IMAGE
  const normalized = path.startsWith('/') ? path : `/${path}`
  if (PAGE_OG_IMAGES[normalized]) return PAGE_OG_IMAGES[normalized]
  if (normalized.startsWith('/feeds')) return PAGE_OG_IMAGES['/feeds']
  return DEFAULT_OG_IMAGE
}
