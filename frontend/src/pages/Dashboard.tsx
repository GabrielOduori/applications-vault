import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Job, AppEvent, Analytics } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  BriefcaseIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const STATUS_GROUPS = [
  { label: 'Active', statuses: ['SAVED', 'SHORTLISTED', 'DRAFTING'], color: 'text-blue-600', bg: 'bg-blue-50' },
  { label: 'Submitted', statuses: ['SUBMITTED', 'INTERVIEW'], color: 'text-purple-600', bg: 'bg-purple-50' },
  { label: 'Decided', statuses: ['OFFER'], color: 'text-green-600', bg: 'bg-green-50' },
  { label: 'Closed', statuses: ['REJECTED', 'WITHDRAWN', 'EXPIRED'], color: 'text-gray-600', bg: 'bg-gray-50' },
];

function RateStat({ label, value, color }: { label: string; value: number | null; color: string }) {
  if (value === null) return (
    <div className="text-center">
      <p className="text-2xl font-bold text-gray-300">—</p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </div>
  );
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}%</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [upcoming, setUpcoming] = useState<AppEvent[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getJobs({ page: 1 }),
      api.getUpcomingEvents(),
      api.getAnalytics(),
    ]).then(([jobRes, events, analyticsData]) => {
      setJobs(jobRes.jobs);
      setUpcoming(events);
      setAnalytics(analyticsData);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  // Use analytics.by_status for accurate totals across all jobs, not just the
  // first page returned by getJobs.
  const counts = STATUS_GROUPS.map((g) => ({
    ...g,
    count: analytics
      ? g.statuses.reduce((sum, s) => sum + (analytics.by_status[s] ?? 0), 0)
      : jobs.filter((j) => g.statuses.includes(j.status)).length,
  }));

  const recentJobs = [...jobs].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 5);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {counts.map((g) => (
          <div key={g.label} className={`${g.bg} rounded-lg p-4`}>
            <p className={`text-2xl font-bold ${g.color}`}>{g.count}</p>
            <p className="text-sm text-gray-600">{g.label}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent jobs */}
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <BriefcaseIcon className="w-5 h-5" />
              Recent Jobs
            </h3>
            <Link to="/jobs" className="text-sm text-blue-600 hover:underline">View all</Link>
          </div>
          {recentJobs.length === 0 ? (
            <p className="text-gray-500 text-sm">No jobs yet. Start by adding one!</p>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <Link
                  key={job.id}
                  to={`/jobs/${job.id}`}
                  className="block p-3 rounded-lg hover:bg-gray-50 border border-gray-100"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{job.title}</p>
                      {job.organisation && (
                        <p className="text-sm text-gray-500">{job.organisation}</p>
                      )}
                    </div>
                    <StatusBadge status={job.status} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming deadlines */}
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <ClockIcon className="w-5 h-5" />
            Upcoming Actions
          </h3>
          {upcoming.length === 0 ? (
            <p className="text-gray-500 text-sm">No upcoming deadlines or actions.</p>
          ) : (
            <div className="space-y-3">
              {upcoming.slice(0, 5).map((ev) => (
                <div key={ev.id} className="p-3 rounded-lg border border-gray-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{ev.event_type}</p>
                      {ev.notes && <p className="text-xs text-gray-500">{ev.notes}</p>}
                    </div>
                    <span className="text-xs text-gray-500">{ev.next_action_date}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Analytics section — only shown once there are submissions */}
      {analytics && analytics.submitted_count > 0 && (
        <div className="space-y-4">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <ChartBarIcon className="w-5 h-5" />
            Pipeline Analytics
          </h3>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Rate metrics */}
            <div className="bg-white rounded-lg border p-4">
              <p className="text-sm font-medium text-gray-500 mb-4">
                Based on {analytics.submitted_count} submitted application{analytics.submitted_count !== 1 ? 's' : ''}
              </p>
              <div className="grid grid-cols-3 gap-4">
                <RateStat label="Response rate" value={analytics.response_rate} color="text-blue-600" />
                <RateStat label="Interview rate" value={analytics.interview_rate} color="text-purple-600" />
                <RateStat label="Offer rate" value={analytics.offer_rate} color="text-green-600" />
              </div>
              {(analytics.avg_days_to_interview !== null || analytics.avg_days_to_decision !== null) && (
                <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-4">
                  {analytics.avg_days_to_interview !== null && (
                    <div className="text-center">
                      <p className="text-xl font-bold text-gray-800">{analytics.avg_days_to_interview}d</p>
                      <p className="text-xs text-gray-500 mt-1">Avg. to interview</p>
                    </div>
                  )}
                  {analytics.avg_days_to_decision !== null && (
                    <div className="text-center">
                      <p className="text-xl font-bold text-gray-800">{analytics.avg_days_to_decision}d</p>
                      <p className="text-xs text-gray-500 mt-1">Avg. to decision</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Ghost applications */}
            <div className="space-y-4">
              {analytics.ghost_count > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <ExclamationTriangleIcon className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-amber-800">
                        {analytics.ghost_count} ghost application{analytics.ghost_count !== 1 ? 's' : ''}
                      </p>
                      <p className="text-sm text-amber-700 mt-1">
                        Submitted {analytics.ghost_count > 1 ? 'applications have' : 'application has'} had no movement
                        for 30+ days. Consider following up or marking as expired.
                      </p>
                      <Link to="/jobs?status=SUBMITTED" className="text-sm text-amber-800 underline mt-2 inline-block">
                        View submitted →
                      </Link>
                    </div>
                  </div>
                </div>
              )}

              {/* Top orgs */}
              {analytics.top_orgs.length > 0 && (
                <div className="bg-white rounded-lg border p-4">
                  <p className="text-sm font-medium text-gray-700 mb-3">Top organisations</p>
                  <div className="space-y-2">
                    {analytics.top_orgs.map((org) => (
                      <div key={org.name} className="flex items-center justify-between text-sm">
                        <span className="text-gray-800 truncate max-w-[140px]" title={org.name}>{org.name}</span>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span>{org.total} applied</span>
                          {org.interviews > 0 && <span className="text-purple-600">{org.interviews} interview{org.interviews !== 1 ? 's' : ''}</span>}
                          {org.offers > 0 && <span className="text-green-600 font-medium">{org.offers} offer{org.offers !== 1 ? 's' : ''}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
