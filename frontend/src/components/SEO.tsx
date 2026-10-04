import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

interface SEOProps {
  title?: string
  description?: string
  path?: string
}

const SITE_URL = 'https://www.linknodes.io'
const SITE_NAME = 'LinkNodes.io'
const DEFAULT_TITLE = 'LinkNodes.io — The Developer Toolkit for Chainlink'
const DEFAULT_DESCRIPTION = 'Query 1,400+ live Chainlink Data Feeds and explore CCIP lane configuration across 13 mainnets. Free developer toolkit, no wallet required.'

export function SEO({ title, description, path }: SEOProps) {
  const location = useLocation()
  const currentPath = path || location.pathname
  const fullTitle = title ? `${title} | ${SITE_NAME}` : DEFAULT_TITLE
  const metaDescription = description || DEFAULT_DESCRIPTION
  const canonicalUrl = `${SITE_URL}${currentPath}`

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

    updateMetaTag('description', metaDescription)
    updateMetaTag('og:title', fullTitle, true)
    updateMetaTag('og:description', metaDescription, true)
    updateMetaTag('og:url', canonicalUrl, true)
    updateMetaTag('og:type', 'website', true)
    updateMetaTag('og:site_name', SITE_NAME, true)
    updateMetaTag('twitter:card', 'summary_large_image')
    updateMetaTag('twitter:title', fullTitle)
    updateMetaTag('twitter:description', metaDescription)

    let canonical = document.querySelector('link[rel="canonical"]')
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.setAttribute('rel', 'canonical')
      document.head.appendChild(canonical)
    }
    canonical.setAttribute('href', canonicalUrl)
  }, [fullTitle, metaDescription, canonicalUrl])

  return null
}
