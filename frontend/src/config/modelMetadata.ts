export const MODEL_METADATA: Record<string, any> = {
  CANSLIM: {
    id: 'CANSLIM',
    displayName: 'CANSLIM',
    category: 'Growth',
    getColor: (status: string) => {
      if (status === 'PASS') return 'bg-emerald-900/50 text-emerald-400 border-emerald-500/30';
      if (status === 'NEUTRAL') return 'bg-amber-900/50 text-amber-400 border-amber-500/30';
      return 'bg-rose-900/50 text-rose-400 border-rose-500/30';
    }
  },
  RRG: {
    id: 'RRG',
    displayName: 'RRG',
    category: 'Momentum',
    getColor: (status: string) => {
      if (status === 'LEADING') return 'bg-emerald-900/50 text-emerald-400 border-emerald-500/30';
      if (status === 'IMPROVING') return 'bg-amber-900/50 text-amber-400 border-amber-500/30';
      if (status === 'WEAKENING') return 'bg-orange-900/50 text-orange-400 border-orange-500/30';
      return 'bg-rose-900/50 text-rose-400 border-rose-500/30';
    }
  }
};
