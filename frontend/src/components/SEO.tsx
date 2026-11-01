import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  DEFAULT_OG_IMAGE,
  SITE_NAME,
  SITE_URL,
  TWITTER_SITE,
  ogImageForPath,
} from '../seo-config.js'

interface SEOProps {
  title?: string
  description?: string
  path?: string
  ogImage?: string
  jsonLd?: Record<string, any>
}

const DEFAULT_TITLE = 'LinkNodes.io — The Developer Toolkit for Chainlink'
const DEFAULT_DESCRIPTION = 'Query 1,400+ live Chainlink Data Feeds and explore CCIP lane configuration across 13 mainnets. Free developer toolkit, no wallet required.'

export function SEO({ title, description, path, ogImage, jsonLd }: SEOProps) {
  const location = useLocation()
  const currentPath = path || location.pathname
  const fullTitle = title ? `${title} | ${SITE_NAME}` : DEFAULT_TITLE
  const metaDescription = description || DEFAULT_DESCRIPTION
  const canonicalUrl = `${SITE_URL}${currentPath}`
  const ogImageUrl = ogImage || ogImageForPath(currentPath) || DEFAULT_OG_IMAGE

  useEffect(() => {
    document.title = fullTitle

    const updateMetaTag = (property: string, content: string, useProperty = false) => {
      const attribute = useProperty ? 'property' : 'name'
      let element = document.querySelector(`meta[${attribute}="${property}"]`)
      if (!element) {
        element = document.createElement('meta')
        element.setAttribute(attribute, property)
        document.head.appendChild(element)
      }
      element.setAttribute('content', content)
    }

    const removeMetaTag = (property: string, useProperty = false) => {
      const attribute = useProperty ? 'property' : 'name'
      document.querySelector(`meta[${attribute}="${property}"]`)?.remove()
    }

    updateMetaTag('description', metaDescription)
    updateMetaTag('og:title', fullTitle, true)
    updateMetaTag('og:description', metaDescription, true)
    updateMetaTag('og:url', canonicalUrl, true)
    updateMetaTag('og:type', 'website', true)
    updateMetaTag('og:site_name', SITE_NAME, true)
    updateMetaTag('og:image', ogImageUrl, true)
    updateMetaTag('og:image:width', '1200', true)
    updateMetaTag('og:image:height', '630', true)
    updateMetaTag('twitter:card', 'summary_large_image')
    updateMetaTag('twitter:url', canonicalUrl)
    updateMetaTag('twitter:title', fullTitle)
    updateMetaTag('twitter:description', metaDescription)
    updateMetaTag('twitter:image', ogImageUrl)
    if (TWITTER_SITE) {
      updateMetaTag('twitter:site', TWITTER_SITE)
    } else {
      removeMetaTag('twitter:site')
    }

    let canonical = document.querySelector('link[rel="canonical"]')
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.setAttribute('rel', 'canonical')
      document.head.appendChild(canonical)
    }
    canonical.setAttribute('href', canonicalUrl)

    // JSON-LD structured data
    const existingJsonLd = document.getElementById('jsonld-seo')
    if (existingJsonLd) {
      existingJsonLd.remove()
    }
    
    if (jsonLd) {
      const script = document.createElement('script')
      script.id = 'jsonld-seo'
      script.type = 'application/ld+json'
      script.textContent = JSON.stringify(jsonLd)
      document.head.appendChild(script)
    }
  }, [fullTitle, metaDescription, canonicalUrl, ogImageUrl, jsonLd])

  return null
}
