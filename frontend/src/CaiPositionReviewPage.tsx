import React from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { CaiPositionReview } from './CaiPositionReview';
import { ArrowLeft } from 'lucide-react';

export const CaiPositionReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const fromSaturday = searchParams.get('from') === 'saturday';
  const backUrl = fromSaturday ? '/cai/saturday-review' : '/caiportfolio';
  const backText = fromSaturday ? 'Back to Saturday Review' : 'Back to Portfolio';

  if (!id) return <div className="p-8 text-center text-red-500 bg-gray-900 h-full">Invalid Position ID</div>;

  return (
    <div className="flex flex-col h-full bg-[#0B0F19] p-2 sm:p-6 min-h-screen">
      <div className="flex items-center mb-6 w-full">
        <button 
          onClick={() => navigate(backUrl)}
          className="flex items-center text-gray-400 hover:text-white transition-colors bg-gray-800/50 hover:bg-gray-800 px-4 py-2 rounded-lg border border-gray-700"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          <span className="font-semibold">{backText}</span>
        </button>
      </div>
      <div className="flex-1 w-full flex flex-col">
        <CaiPositionReview 
          positionId={id} 
          onReviewSaved={() => navigate(backUrl)}
          onClose={() => navigate(backUrl)}
        />
      </div>
    </div>
  );
};
