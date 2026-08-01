-- Migration 012: CAI Decision Ladder Extension (Decision Ladder Engine V2.0)
-- Date: 2026-08-01

-- 1. Create the ENUM type for decision states (idempotent syntax)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cai_decision_state_enum') THEN
        CREATE TYPE cai_decision_state_enum AS ENUM (
            'ADD',
            'HOLD',
            'ALERT',
            'STRUCTURE',
            'QUIT',
            'NOT_COMPUTED'
        );
    END IF;
END$$;

-- 2. Add columns to cai_position
ALTER TABLE cai_position
ADD COLUMN IF NOT EXISTS add_level DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS alert_level DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS structure_level DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS quit_level DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS decision_state cai_decision_state_enum DEFAULT 'NOT_COMPUTED',
ADD COLUMN IF NOT EXISTS decision_quality VARCHAR(20) DEFAULT 'NORMAL',
ADD COLUMN IF NOT EXISTS decision_calculated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS decision_algorithm_version VARCHAR(20);
