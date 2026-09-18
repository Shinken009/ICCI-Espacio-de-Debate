<!--
SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz

SPDX-License-Identifier: MPL-2.0
-->

<script lang="ts">
	import { onMount } from 'svelte';
	import { socket } from '$lib/socket';
	import type { Question, VotingAnswer } from '$lib/quiz_types';
	import {
		ActivityPhase,
		FacilitationMode,
		type ActivityOwnResponse,
		type ActivityState,
		type ActivityStateEvent
	} from '$lib/play/activity/types';

	interface Props {
		question: Question;
		question_index: string | number;
	}

	let { question, question_index }: Props = $props();
	let state: ActivityState | null = $state(null);
	let submitted_phases: ActivityPhase[] = $state([]);
	let my_responses: Partial<Record<ActivityPhase, ActivityOwnResponse>> = $state({});
	let facilitation_mode = $state(FacilitationMode.WAITING);
	let choice = $state('');
	let confidence = $state(3);
	let justification = $state('');
	let reflection = $state('');
	let saved = $state(false);
	let error = $state('');

	const numericQuestionIndex = () => Number(question_index);
	const isSubmitted = (phase: ActivityPhase) => submitted_phases.includes(phase);
	const isMicrogroup = $derived(facilitation_mode === FacilitationMode.MICROGROUP);

	const requestState = () => {
		socket.emit('get_activity_state', { question_index: numericQuestionIndex() });
	};

	const resetDraft = () => {
		choice = '';
		confidence = 3;
		justification = '';
		reflection = '';
	};

	onMount(() => {
		const onActivityState = (data: ActivityStateEvent) => {
			if (data.state && data.state.question_index !== numericQuestionIndex()) return;
			state = data.state;
			submitted_phases = data.submitted_phases ?? [];
			my_responses = data.my_responses ?? {};
			facilitation_mode = data.facilitation_mode ?? FacilitationMode.WAITING;
		};

		const onPhaseChanged = (data: ActivityState) => {
			if (data.question_index !== numericQuestionIndex()) return;
			state = data;
			saved = false;
			error = '';
			resetDraft();
			requestState();
		};

		const onResponseSaved = (data: { question_index: number; phase: ActivityPhase }) => {
			if (data.question_index !== numericQuestionIndex()) return;
			if (!submitted_phases.includes(data.phase)) {
				submitted_phases = [...submitted_phases, data.phase];
			}
			saved = true;
			requestState();
		};

		const onActivityError = (data: { code?: string }) => {
			error = data?.code ?? 'activity_error';
		};

		socket.on('activity_state', onActivityState);
		socket.on('activity_phase_changed', onPhaseChanged);
		socket.on('activity_response_saved', onResponseSaved);
		socket.on('activity_error', onActivityError);
		requestState();

		return () => {
			socket.off('activity_state', onActivityState);
			socket.off('activity_phase_changed', onPhaseChanged);
			socket.off('activity_response_saved', onResponseSaved);
			socket.off('activity_error', onActivityError);
		};
	});

	const submitResponse = () => {
		if (!state) return;
		const payload: Record<string, unknown> = {
			question_index: numericQuestionIndex(),
			phase: state.phase
		};

		if (
			state.phase === ActivityPhase.INITIAL_RESPONSE ||
			state.phase === ActivityPhase.SECOND_RESPONSE
		) {
			payload.choice = choice;
			payload.confidence = confidence;
			payload.justification = justification;
		}
		if (state.phase === ActivityPhase.REFLECTION) payload.reflection = reflection;

		error = '';
		socket.emit('submit_activity_response', payload);
	};

	const canSubmit = $derived.by(() => {
		if (!state || isSubmitted(state.phase)) return false;
		if (
			state.phase === ActivityPhase.INITIAL_RESPONSE ||
			state.phase === ActivityPhase.SECOND_RESPONSE
		) {
			return Boolean(choice && justification.trim().length > 0);
		}
		if (state.phase === ActivityPhase.REFLECTION) return reflection.trim().length > 0;
		return false;
	});

	const votingAnswers = $derived((question.answers ?? []) as VotingAnswer[]);
	const r1_response = $derived(my_responses[ActivityPhase.INITIAL_RESPONSE]);
	const r2_response = $derived(my_responses[ActivityPhase.SECOND_RESPONSE]);
</script>

<div class="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-5 px-4 py-6 text-slate-900 dark:text-slate-100">
	<header class="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/90">
		<div class="flex flex-wrap items-center gap-2">
			<p class="mr-auto text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
				ICCI · Espacio de debate
			</p>
			{#if isMicrogroup}
				<span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold dark:bg-slate-800">
					Modo microgrupo
				</span>
			{/if}
		</div>
		<h1 class="mt-2 text-xl font-semibold">{@html question.question}</h1>
	</header>

	{#if !state}
		<section class="rounded-2xl border border-dashed border-slate-300 p-6 text-center dark:border-slate-700">
			<p class="font-medium">Esperando que el docente inicie la actividad.</p>
		</section>
	{:else if state.phase === ActivityPhase.DISCUSSION}
		<section class="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
			<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Discusión</p>
			<h2 class="mt-2 text-2xl font-semibold">Contrasta razones antes de responder nuevamente.</h2>
			<p class="mt-3 text-sm text-slate-600 dark:text-slate-300">
				No es necesario llegar a consenso. Escucha, pregunta y examina qué razones sostienes o revisarías.
			</p>

			{#if r1_response}
				<div class="mt-5 rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
					<p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Tu R1</p>
					<p class="mt-2"><strong>Alternativa:</strong> {r1_response.choice}</p>
					<p class="mt-1"><strong>Convicción:</strong> {r1_response.confidence}/5</p>
					<p class="mt-1"><strong>Justificación:</strong> {r1_response.justification}</p>
				</div>
			{/if}

			{#if isMicrogroup}
				<div class="mt-5 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
					<p class="font-semibold">Protocolo de microgrupo</p>
					<ol class="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-600 dark:text-slate-300">
						<li>Cada participante expone su razón principal sin interrupciones.</li>
						<li>Cada participante responde o pregunta sobre al menos un argumento ajeno, cuando haya otra persona presente.</li>
						<li>Antes de R2, identifica qué razones mantienes y cuáles revisarías.</li>
					</ol>
				</div>
			{/if}
		</section>
	{:else if state.phase === ActivityPhase.RESULTS}
		<section class="rounded-2xl border border-slate-200 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900">
			<h2 class="text-2xl font-semibold">Actividad completada</h2>
			<p class="mt-2 text-slate-600 dark:text-slate-300">
				Los resultados se muestran al docente de forma agregada y descriptiva.
			</p>
			{#if r2_response}
				<p class="mt-4 text-sm text-slate-500">
					Tu R2 quedó registrada con convicción {r2_response.confidence}/5.
				</p>
			{/if}
		</section>
	{:else if isSubmitted(state.phase) || saved}
		<section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-100">
			<h2 class="text-xl font-semibold">Respuesta registrada</h2>
			<p class="mt-2">Espera la siguiente fase indicada por el docente.</p>
		</section>
	{:else}
		<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
			{#if state.phase === ActivityPhase.INITIAL_RESPONSE || state.phase === ActivityPhase.SECOND_RESPONSE}
				<p class="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
					{state.phase === ActivityPhase.INITIAL_RESPONSE ? 'R1 · respuesta individual' : 'R2 · respuesta individual'}
				</p>
				<p class="mb-4 text-sm text-slate-600 dark:text-slate-300">
					Elige una alternativa, indica tu nivel de convicción y explica la razón principal.
				</p>

				<div class="grid gap-3 sm:grid-cols-2">
					{#each votingAnswers as answer}
						<button
							type="button"
							class="rounded-xl border p-4 text-left transition"
							class:border-slate-900={choice === answer.answer}
							class:bg-slate-100={choice === answer.answer}
							class:border-slate-200={choice !== answer.answer}
							onclick={() => (choice = answer.answer)}
						>
							{answer.answer}
						</button>
					{/each}
				</div>

				<div class="mt-5">
					<label for="confidence" class="block text-sm font-medium">
						Convicción: {confidence}/5
					</label>
					<input
						id="confidence"
						class="mt-2 w-full"
						type="range"
						min="1"
						max="5"
						step="1"
						bind:value={confidence}
					/>
					<div class="mt-1 flex justify-between text-xs text-slate-500">
						<span>1 · baja</span>
						<span>5 · alta</span>
					</div>
				</div>

				<div class="mt-5">
					<label for="justification" class="block text-sm font-medium">
						¿Cuál es la razón principal de tu elección?
					</label>
					<textarea
						id="justification"
						maxlength="1000"
						rows="4"
						class="mt-2 w-full rounded-xl border border-slate-300 bg-transparent p-3"
						bind:value={justification}
					></textarea>
				</div>
			{:else if state.phase === ActivityPhase.REFLECTION}
				<p class="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">Reflexión final</p>
				<p class="mb-4 text-sm text-slate-600 dark:text-slate-300">
					La reflexión no evalúa si cambiar o mantener fue mejor; registra cómo evolucionó tu razonamiento.
				</p>
				<label for="reflection" class="block text-sm font-medium">
					¿Qué razones explican que mantuvieras o cambiaras tu respuesta entre R1 y R2?
				</label>
				<textarea
					id="reflection"
					maxlength="1000"
					rows="5"
					class="mt-2 w-full rounded-xl border border-slate-300 bg-transparent p-3"
					bind:value={reflection}
				></textarea>
			{/if}

			<button
				type="button"
				class="mt-5 w-full rounded-xl bg-slate-900 px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
				disabled={!canSubmit}
				onclick={submitResponse}
			>
				Enviar
			</button>
			{#if error}<p class="mt-3 text-sm text-red-600">No se pudo registrar: {error}</p>{/if}
		</section>
	{/if}
</div>
