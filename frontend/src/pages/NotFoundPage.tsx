import { Link } from 'react-router-dom'
import { PageLayout } from '../components/PageLayout'
import { SEO } from '../components/SEO'

export function NotFoundPage() {
  return (
    <PageLayout>
      <SEO
        title="Page Not Found"
        description="The page you are looking for does not exist."
        path="/404"
      />
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="mx-auto max-w-md text-center">
          <h1 className="mb-4 text-6xl font-bold text-white">404</h1>
          <h2 className="mb-2 text-2xl font-bold text-slate-200">Page Not Found</h2>
          <p className="mb-6 text-slate-400">
            The page you are looking for does not exist or has been moved.
          </p>
          <div className="flex justify-center gap-3">
            <Link
              to="/"
              className="rounded-lg bg-accent-500 px-6 py-3 font-medium text-white hover:bg-accent-600"
            >
              Go Home
            </Link>
            <Link
              to="/feeds"
              className="rounded-lg border border-ink-700 bg-ink-900 px-6 py-3 font-medium text-white hover:bg-ink-800"
            >
              Browse Feeds
            </Link>
          </div>
        </div>
      </div>
    </PageLayout>
  )
}
