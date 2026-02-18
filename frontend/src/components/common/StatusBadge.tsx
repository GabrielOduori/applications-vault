const STATUS_COLORS: Record<string, string> = {
  SAVED: 'bg-gray-100 text-gray-700',
  SHORTLISTED: 'bg-blue-100 text-blue-700',
  DRAFTING: 'bg-yellow-100 text-yellow-700',
  SUBMITTED: 'bg-purple-100 text-purple-700',
  INTERVIEW: 'bg-indigo-100 text-indigo-700',
  OFFER: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  WITHDRAWN: 'bg-orange-100 text-orange-700',
  EXPIRED: 'bg-gray-200 text-gray-500',
};

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || 'bg-gray-100 text-gray-700';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}
