import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Job, Capture, AppEvent, Document as DocType } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';
import {
  ArrowLeftIcon,
  CalendarIcon,
  DocumentArrowUpIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

const TABS = ['Overview', 'Captures', 'Timeline', 'Documents'];
const EVENT_TYPES = ['SHORTLISTED', 'DRAFTING', 'SUBMITTED', 'INTERVIEW', 'OFFER', 'REJECTED', 'WITHDRAWN'];

// Defines the natural flow of a job application
const NEXT_STEPS: Record<string, { primary: string; label: string; secondary?: { type: string; label: string }[] }> = {
  SAVED:       { primary: 'SHORTLISTED', label: 'Shortlist', secondary: [{ type: 'DRAFTING', label: 'Start Drafting' }, { type: 'WITHDRAWN', label: 'Withdraw' }] },
  SHORTLISTED: { primary: 'DRAFTING',    label: 'Start Drafting', secondary: [{ type: 'SUBMITTED', label: 'Mark Submitted' }, { type: 'WITHDRAWN', label: 'Withdraw' }] },
  DRAFTING:    { primary: 'SUBMITTED',   label: 'Mark as Submitted', secondary: [{ type: 'WITHDRAWN', label: 'Withdraw' }] },
  SUBMITTED:   { primary: 'INTERVIEW',   label: 'Got Interview', secondary: [{ type: 'REJECTED', label: 'Rejected' }, { type: 'OFFER', label: 'Got Offer' }] },
  INTERVIEW:   { primary: 'OFFER',       label: 'Got Offer', secondary: [{ type: 'REJECTED', label: 'Rejected' }, { type: 'WITHDRAWN', label: 'Withdraw' }] },
};
const DOC_TYPES = ['cv', 'cover_letter', 'research_statement', 'teaching_statement', 'transcript', 'portfolio', 'other'];

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [events, setEvents] = useState<AppEvent[]>([]);
  const [documents, setDocuments] = useState<DocType[]>([]);
  const [tab, setTab] = useState('Overview');
  const [loading, setLoading] = useState(true);

  const loadJob = async () => {
    if (!id) return;
    try {
      const [j, c, e, d] = await Promise.all([
        api.getJob(id),
        api.getCaptures(id),
        api.getEvents(id),
        api.getDocuments(id),
      ]);
      setJob(j); setCaptures(c); setEvents(e); setDocuments(d);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { loadJob(); }, [id]);

  const handleDelete = async () => {
    if (!id || !confirm('Delete this job and all associated data?')) return;
    await api.deleteJob(id);
    navigate('/jobs');
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!job) return <div className="text-center py-12 text-gray-500">Job not found</div>;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/jobs" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeftIcon className="w-4 h-4 mr-1" /> Back to jobs
          </Link>
          <h2 className="text-2xl font-bold text-gray-900">{job.title}</h2>
          <div className="flex items-center gap-3 mt-1">
            {job.organisation && <span className="text-gray-600">{job.organisation}</span>}
            <StatusBadge status={job.status} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          {job.deadline_date && (
            <a
              href={api.getCalendarUrl(job.id)}
              className="inline-flex items-center px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
              target="_blank"
            >
              <CalendarIcon className="w-4 h-4 mr-1" /> .ics
            </a>
          )}
          <button onClick={handleDelete} className="inline-flex items-center px-3 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
            <TrashIcon className="w-4 h-4 mr-1" /> Delete
          </button>
        </div>
      </div>

      {/* Status transition bar */}
      {NEXT_STEPS[job.status] && (
        <StatusTransitionBar job={job} onUpdate={loadJob} />
      )}

      {/* Tabs */}
      <div className="border-b">
        <div className="flex gap-4">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-2 px-1 text-sm font-medium border-b-2 ${
                tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t}
              {t === 'Captures' && ` (${captures.length})`}
              {t === 'Timeline' && ` (${events.length})`}
              {t === 'Documents' && ` (${documents.length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'Overview' && <OverviewTab job={job} onUpdate={loadJob} />}
      {tab === 'Captures' && <CapturesTab jobId={job.id} captures={captures} onUpdate={loadJob} />}
      {tab === 'Timeline' && <TimelineTab jobId={job.id} events={events} onUpdate={loadJob} />}
      {tab === 'Documents' && <DocumentsTab jobId={job.id} documents={documents} onUpdate={loadJob} />}
    </div>
  );
}

function StatusTransitionBar({ job, onUpdate }: { job: Job; onUpdate: () => void }) {
  const next = NEXT_STEPS[job.status];
  const [submitting, setSubmitting] = useState(false);

  if (!next) return null;

  const transition = async (eventType: string) => {
    setSubmitting(true);
    try {
      await api.addEvent(job.id, { event_type: eventType, notes: `Status changed to ${eventType}` });
      onUpdate();
    } catch { /* ignore */ }
    setSubmitting(false);
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
      <div className="text-sm text-blue-800">
        <span className="font-medium">Next step:</span> Move this job forward in your pipeline
      </div>
      <div className="flex items-center gap-2">
        {next.secondary?.map((s) => (
          <button
            key={s.type}
            onClick={() => transition(s.type)}
            disabled={submitting}
            className="px-3 py-1.5 text-xs font-medium border border-gray-300 text-gray-600 rounded-lg hover:bg-white disabled:opacity-50"
          >
            {s.label}
          </button>
        ))}
        <button
          onClick={() => transition(next.primary)}
          disabled={submitting}
          className="px-4 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? '...' : next.label}
        </button>
      </div>
    </div>
  );
}

function OverviewTab({ job, onUpdate }: { job: Job; onUpdate: () => void }) {
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState(job.notes || '');
  const [allTags, setAllTags] = useState<import('../types/index').Tag[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [tagLoading, setTagLoading] = useState(false);

  useEffect(() => {
    api.getTags().then(setAllTags).catch(() => {});
  }, []);

  const saveNotes = async () => {
    await api.updateJob(job.id, { notes });
    setEditing(false);
    onUpdate();
  };

  const handleAddTag = async () => {
    if (!tagInput.trim()) return;
    setTagLoading(true);
    try {
      await api.addTagToJob(job.id, tagInput.trim());
      setTagInput('');
      const tags = await api.getTags();
      setAllTags(tags);
      onUpdate();
    } catch { /* ignore */ }
    setTagLoading(false);
  };

  const handleRemoveTag = async (tagName: string) => {
    const tag = allTags.find((t) => t.name === tagName);
    if (!tag) return;
    try {
      await api.removeTagFromJob(job.id, tag.id);
      onUpdate();
    } catch { /* ignore */ }
  };

  return (
    <div className="bg-white rounded-lg border p-6 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <InfoRow label="Organisation" value={job.organisation} />
        <InfoRow label="Location" value={job.location} />
        <InfoRow label="Salary Range" value={job.salary_range} />
        <InfoRow label="Deadline" value={job.deadline_date ? `${job.deadline_date} (${job.deadline_type})` : job.deadline_type} />
        {job.url && (
          <div className="col-span-2">
            <span className="text-sm text-gray-500">URL:</span>{' '}
            <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline break-all">
              {job.url}
            </a>
          </div>
        )}
      </div>

      {/* Tags */}
      <div>
        <span className="text-sm font-medium text-gray-700">Tags</span>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {job.tags.map((name) => (
            <span key={name} className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
              {name}
              <button
                onClick={() => handleRemoveTag(name)}
                className="text-blue-400 hover:text-blue-700 ml-0.5 leading-none font-bold"
                title="Remove tag"
              >
                ×
              </button>
            </span>
          ))}
          <div className="flex items-center gap-1">
            <input
              list="tags-datalist"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
              placeholder="Add tag…"
              className="px-2.5 py-1 border border-dashed border-gray-300 rounded-full text-xs w-28 focus:outline-none focus:border-blue-400"
            />
            <datalist id="tags-datalist">
              {allTags.filter((t) => !job.tags.includes(t.name)).map((t) => (
                <option key={t.id} value={t.name} />
              ))}
            </datalist>
            <button
              onClick={handleAddTag}
              disabled={tagLoading || !tagInput.trim()}
              className="text-xs text-blue-600 hover:underline disabled:opacity-40"
            >
              {tagLoading ? '…' : 'Add'}
            </button>
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">Notes</span>
          <button onClick={() => editing ? saveNotes() : setEditing(true)} className="text-xs text-blue-600 hover:underline">
            {editing ? 'Save' : 'Edit'}
          </button>
        </div>
        {editing ? (
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={4}
            className="w-full px-3 py-2 border rounded-lg text-sm" />
        ) : (
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{job.notes || 'No notes yet.'}</p>
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <span className="text-sm text-gray-500">{label}:</span>{' '}
      <span className="text-sm text-gray-900">{value || '—'}</span>
    </div>
  );
}

function CapturesTab({ jobId, captures, onUpdate }: { jobId: string; captures: Capture[]; onUpdate: () => void }) {
  const [showAdd, setShowAdd] = useState(false);
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleAdd = async () => {
    setSubmitting(true);
    await api.createCapture(jobId, { text_snapshot: text, url: url || undefined, capture_method: 'manual_paste' });
    setText(''); setUrl(''); setShowAdd(false); setSubmitting(false);
    onUpdate();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowAdd(true)} className="text-sm text-blue-600 hover:underline">+ Add capture</button>
      </div>

      {captures.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-8">No captures yet. Paste a job description or use the browser extension.</p>
      ) : (
        captures.map((cap) => (
          <div key={cap.id} className="bg-white rounded-lg border p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{cap.capture_method}</span>
                {cap.page_title && <span className="text-sm font-medium text-gray-700">{cap.page_title}</span>}
              </div>
              <span className="text-xs text-gray-400">{new Date(cap.captured_at).toLocaleString()}</span>
            </div>
            {cap.url && (
              <a href={cap.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:underline break-all block mb-2">{cap.url}</a>
            )}
            {cap.text_snapshot && (
              <pre className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 rounded p-3 max-h-64 overflow-y-auto">{cap.text_snapshot}</pre>
            )}
          </div>
        ))
      )}

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Capture">
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL (optional)</label>
            <input type="url" value={url} onChange={(e) => setUrl(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="https://..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Job Description Text</label>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8}
              className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Paste the job description here..." />
          </div>
          <button onClick={handleAdd} disabled={submitting || !text}
            className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300 hover:bg-blue-700">
            {submitting ? 'Saving...' : 'Save Capture'}
          </button>
        </div>
      </Modal>
    </div>
  );
}

function TimelineTab({ jobId, events, onUpdate }: { jobId: string; events: AppEvent[]; onUpdate: () => void }) {
  const [showAdd, setShowAdd] = useState(false);
  const [eventType, setEventType] = useState('SHORTLISTED');
  const [notes, setNotes] = useState('');
  const [nextDate, setNextDate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleAdd = async () => {
    setSubmitting(true);
    await api.addEvent(jobId, { event_type: eventType, notes: notes || undefined, next_action_date: nextDate || undefined });
    setNotes(''); setNextDate(''); setShowAdd(false); setSubmitting(false);
    onUpdate();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowAdd(true)} className="text-sm text-blue-600 hover:underline">+ Add event</button>
      </div>

      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />
        <div className="space-y-4">
          {events.map((ev) => (
            <div key={ev.id} className="relative pl-10">
              <div className="absolute left-2.5 w-3 h-3 rounded-full bg-blue-500 border-2 border-white" />
              <div className="bg-white rounded-lg border p-3">
                <div className="flex items-center justify-between">
                  <StatusBadge status={ev.event_type} />
                  <span className="text-xs text-gray-400">{new Date(ev.occurred_at).toLocaleString()}</span>
                </div>
                {ev.notes && <p className="text-sm text-gray-600 mt-1">{ev.notes}</p>}
                {ev.next_action_date && (
                  <p className="text-xs text-orange-600 mt-1">Next action: {ev.next_action_date}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Event">
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
            <select value={eventType} onChange={(e) => setEventType(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm">
              {EVENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
              className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Next Action Date</label>
            <input type="date" value={nextDate} onChange={(e) => setNextDate(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <button onClick={handleAdd} disabled={submitting}
            className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300 hover:bg-blue-700">
            {submitting ? 'Adding...' : 'Add Event'}
          </button>
        </div>
      </Modal>
    </div>
  );
}

function DocumentsTab({ jobId, documents, onUpdate }: { jobId: string; documents: DocType[]; onUpdate: () => void }) {
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('cv');
  const [versionLabel, setVersionLabel] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verifyResults, setVerifyResults] = useState<Record<string, boolean>>({});
  const [matching, setMatching] = useState<string | null>(null);
  const [matchResults, setMatchResults] = useState<Record<string, import('../types').MatchResult>>({});
  const [togglingSubmit, setTogglingSubmit] = useState<string | null>(null);

  const handleVerify = async (doc: DocType) => {
    setVerifying(doc.id);
    try {
      const result = await api.verifyDocument(jobId, doc.id);
      setVerifyResults((prev) => ({ ...prev, [doc.id]: result.verified }));
    } catch { /* ignore */ }
    setVerifying(null);
  };

  const handleSubmitToggle = async (doc: DocType) => {
    setTogglingSubmit(doc.id);
    try {
      if (doc.submitted_at) {
        await api.unsubmitDocument(jobId, doc.id);
      } else {
        await api.submitDocument(jobId, doc.id);
      }
      onUpdate();
    } catch { /* ignore */ }
    setTogglingSubmit(null);
  };

  const handleMatch = async (doc: DocType) => {
    setMatching(doc.id);
    try {
      const result = await api.matchDocument(jobId, doc.id);
      setMatchResults((prev) => ({ ...prev, [doc.id]: result }));
    } catch { /* ignore */ }
    setMatching(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setSubmitting(true);
    setError('');
    try {
      await api.uploadDocument(jobId, file, docType, versionLabel || undefined);
      setFile(null); setVersionLabel(''); setShowUpload(false);
      onUpdate();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    }
    setSubmitting(false);
  };

  const handleDownload = async (doc: DocType) => {
    const res = await api.downloadDocument(jobId, doc.id);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.original_filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => setShowUpload(true)}
          className="inline-flex items-center text-sm text-blue-600 hover:underline">
          <DocumentArrowUpIcon className="w-4 h-4 mr-1" /> Upload document
        </button>
      </div>

      {documents.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-8">No documents yet. Upload your CV, cover letter, or other materials.</p>
      ) : (
        <div className="bg-white rounded-lg border divide-y">
          {documents.map((doc) => (
            <div key={doc.id} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{doc.original_filename}</p>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{doc.doc_type}</span>
                    {doc.version_label && <span className="text-xs text-gray-500">{doc.version_label}</span>}
                    <span className="text-xs text-gray-400">{formatSize(doc.file_size_bytes)}</span>
                    <span className="text-xs text-gray-400 font-mono">{doc.file_hash.slice(0, 8)}</span>
                    {doc.submitted_at && (
                      <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full font-medium">
                        Submitted {new Date(doc.submitted_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                  {verifyResults[doc.id] !== undefined && (
                    <span className={`text-xs font-medium ${verifyResults[doc.id] ? 'text-green-600' : 'text-red-600'}`}>
                      {verifyResults[doc.id] ? '✓ Intact' : '✗ Tampered'}
                    </span>
                  )}
                  <button
                    onClick={() => handleVerify(doc)}
                    disabled={verifying === doc.id}
                    className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-40"
                  >
                    {verifying === doc.id ? 'Verifying…' : 'Verify'}
                  </button>
                  <button
                    onClick={() => handleSubmitToggle(doc)}
                    disabled={togglingSubmit === doc.id}
                    className={`text-xs font-medium disabled:opacity-40 ${doc.submitted_at ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'}`}
                  >
                    {togglingSubmit === doc.id ? '…' : doc.submitted_at ? 'Unsubmit' : 'Mark Submitted'}
                  </button>
                  <button
                    onClick={() => handleMatch(doc)}
                    disabled={matching === doc.id}
                    className="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-40"
                  >
                    {matching === doc.id ? 'Scoring…' : 'Match'}
                  </button>
                  <button onClick={() => handleDownload(doc)} className="text-xs text-blue-600 hover:underline">
                    Download
                  </button>
                </div>
              </div>
              {matchResults[doc.id] && (
                <div className="mt-3 bg-purple-50 rounded-lg p-3 text-xs space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-purple-900">Keyword match:</span>
                    <span className={`font-bold text-lg ${matchResults[doc.id].score >= 60 ? 'text-green-600' : matchResults[doc.id].score >= 30 ? 'text-orange-500' : 'text-red-500'}`}>
                      {matchResults[doc.id].score}%
                    </span>
                  </div>
                  {matchResults[doc.id].matched.length > 0 && (
                    <p className="text-purple-700"><span className="font-medium">Matched:</span> {matchResults[doc.id].matched.slice(0, 20).join(', ')}</p>
                  )}
                  {matchResults[doc.id].missing.length > 0 && (
                    <p className="text-red-600"><span className="font-medium">Missing:</span> {matchResults[doc.id].missing.slice(0, 20).join(', ')}</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal open={showUpload} onClose={() => setShowUpload(false)} title="Upload Document">
        <div className="space-y-3">
          {error && <div className="bg-red-50 text-red-700 text-sm rounded-lg p-3">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">File</label>
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
            <select value={docType} onChange={(e) => setDocType(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm">
              {DOC_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Version Label</label>
            <input type="text" value={versionLabel} onChange={(e) => setVersionLabel(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="e.g. v1, final, tailored" />
          </div>
          <button onClick={handleUpload} disabled={submitting || !file}
            className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300 hover:bg-blue-700">
            {submitting ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
