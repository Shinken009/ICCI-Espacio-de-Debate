// SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
//
// SPDX-License-Identifier: MPL-2.0

export const PEER_DELIBERATION = 'PEER_DELIBERATION' as const;

export enum FacilitationMode {
	WAITING = 'WAITING',
	MICROGROUP = 'MICROGROUP',
	CLASSROOM = 'CLASSROOM'
}

export enum ActivityPhase {
	INITIAL_RESPONSE = 'INITIAL_RESPONSE',
	DISCUSSION = 'DISCUSSION',
	SECOND_RESPONSE = 'SECOND_RESPONSE',
	REFLECTION = 'REFLECTION',
	RESULTS = 'RESULTS'
}

export interface ActivityState {
	question_index: number;
	interaction_mode: typeof PEER_DELIBERATION;
	phase: ActivityPhase;
	phase_started_at: string;
	phase_deadline?: string | null;
}

export interface ActivityOwnResponse {
	choice?: string | null;
	confidence?: number | null;
	justification?: string | null;
	reflection?: string | null;
}

export interface ActivityStateEvent {
	state: ActivityState | null;
	submitted_phases: ActivityPhase[];
	my_responses?: Partial<Record<ActivityPhase, ActivityOwnResponse>>;
	response_count: number;
	player_count: number;
	facilitation_mode: FacilitationMode;
}

export interface ActivityProgress {
	question_index: number;
	phase: ActivityPhase;
	response_count: number;
	player_count: number;
	facilitation_mode: FacilitationMode;
}

export interface ActivityResults {
	question_index: number;
	initial_counts: Record<string, number>;
	second_counts: Record<string, number>;
	transitions: Record<string, Record<string, number>>;
	stance: { maintained: number; changed: number };
	confidence_change: { increased: number; decreased: number; unchanged: number };
	matched_participants: number;
	reflection_count: number;
	player_count: number;
	facilitation_mode: FacilitationMode;
}
