import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Job, Tag } from '../types/index';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';
import { PlusIcon, FunnelIcon } from '@heroicons/react/24/outline';

const STATUSES = ['ALL', 'SAVED', 'SHORTLISTED', 'DRAFTING', 'SUBMITTED', 'INTERVIEW', 'OFFER', 'REJECTED', 'WITHDRAWN'];

export function JobListPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('ALL');
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    api.getTags().then(setAllTags).catch(() => {});
  }, []);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await api.getJobs({
        status: status === 'ALL' ? undefined : status,
        q: search || undefined,
        tag: selectedTag || undefined,
        page,
      });
      setJobs(res.jobs);
      setTotal(res.total);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchJobs(); }, [status, page, search, selectedTag]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Jobs</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          Add Job
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search jobs..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {allTags.length > 0 && (
            <select
              value={selectedTag}
              onChange={(e) => { setSelectedTag(e.target.value); setPage(1); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            >
              <option value="">All tags</option>
              {allTags.map((t) => (
                <option key={t.id} value={t.name}>{t.name}</option>
              ))}
            </select>
          )}
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          <FunnelIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => { setStatus(s); setPage(1); }}
              className={`px-3 py-1 text-xs font-medium rounded-full whitespace-nowrap ${
                status === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Job list */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">No jobs found.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="text-blue-600 hover:underline text-sm"
          >
            Add your first job
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border divide-y">
          {jobs.map((job) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="block p-4 hover:bg-gray-50"
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <p className="font-medium text-gray-900 truncate">{job.title}</p>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="flex items-center gap-4 mt-1">
                    {job.organisation && (
                      <span className="text-sm text-gray-500">{job.organisation}</span>
                    )}
                    {job.location && (
                      <span className="text-sm text-gray-400">{job.location}</span>
                    )}
                    {job.deadline_date && (
                      <span className="text-xs text-orange-600">Due: {job.deadline_date}</span>
                    )}
                  </div>
                  {job.tags.length > 0 && (
                    <div className="flex gap-1 mt-2">
                      {job.tags.map((t) => (
                        <span key={t} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right text-xs text-gray-400 ml-4 flex-shrink-0">
                  <div>{job.capture_count} captures</div>
                  <div>{job.document_count} docs</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-gray-500">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 20 >= total}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Create modal */}
      <CreateJobModal open={showCreate} onClose={() => setShowCreate(false)} onCreated={fetchJobs} />
    </div>
  );
}

function CreateJobModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [title, setTitle] = useState('');
  const [organisation, setOrganisation] = useState('');
  const [url, setUrl] = useState('');
  const [location, setLocation] = useState('');
  const [deadlineDate, setDeadlineDate] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.createJob({
        title,
        organisation: organisation || undefined,
        url: url || undefined,
        location: location || undefined,
        deadline_type: deadlineDate ? 'fixed' : 'unknown',
        deadline_date: deadlineDate || undefined,
        notes: notes || undefined,
      });
      setTitle(''); setOrganisation(''); setUrl(''); setLocation(''); setDeadlineDate(''); setNotes('');
      onCreated();
      onClose();
    } catch { /* ignore */ }
    setSubmitting(false);
  };

  return (
    <Modal open={open} onClose={onClose} title="Add Job">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Job Title *</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Software Engineer" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Organisation</label>
          <input type="text" value={organisation} onChange={(e) => setOrganisation(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Acme Corp" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
          <input type="url" value={url} onChange={(e) => setUrl(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="https://..." />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
            <input type="text" value={location} onChange={(e) => setLocation(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="e.g. Remote" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Deadline</label>
            <input type="date" value={deadlineDate} onChange={(e) => setDeadlineDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="Any notes..." />
        </div>
        <button type="submit" disabled={submitting || !title}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300 hover:bg-blue-700">
          {submitting ? 'Creating...' : 'Create Job'}
        </button>
      </form>
    </Modal>
  );
}
