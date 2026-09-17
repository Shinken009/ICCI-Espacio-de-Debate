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
	let choice = $state('');
	let confidence = $state(3);
	let justification = $state('');
	let reflection = $state('');
	let saved = $state(false);
	let error = $state('');

	const numericQuestionIndex = () => Number(question_index);

	const isSubmitted = (phase: ActivityPhase) => submitted_phases.includes(phase);

	const requestState = () => {
		socket.emit('get_activity_state', { question_index: numericQuestionIndex() });
	};

	onMount(requestState);

	socket.on('activity_state', (data: ActivityStateEvent) => {
		if (data.state && data.state.question_index !== numericQuestionIndex()) return;
		state = data.state;
		submitted_phases = data.submitted_phases ?? [];
	});

	socket.on('activity_phase_changed', (data: ActivityState) => {
		if (data.question_index !== numericQuestionIndex()) return;
		state = data;
		saved = false;
		error = '';
		choice = '';
		confidence = 3;
		justification = '';
		reflection = '';
	});

	socket.on('activity_response_saved', (data) => {
		if (data.question_index !== numericQuestionIndex()) return;
		if (!submitted_phases.includes(data.phase)) {
			submitted_phases = [...submitted_phases, data.phase];
		}
		saved = true;
	});

	socket.on('activity_error', (data) => {
		error = data?.code ?? 'activity_error';
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
		}
		if (state.phase === ActivityPhase.INITIAL_RESPONSE) payload.justification = justification;
		if (state.phase === ActivityPhase.REFLECTION) payload.reflection = reflection;

		socket.emit('submit_activity_response', payload);
	};

	const canSubmit = $derived.by(() => {
		if (!state || isSubmitted(state.phase)) return false;
		if (state.phase === ActivityPhase.INITIAL_RESPONSE) {
			return Boolean(choice && justification.trim().length > 0);
		}
		if (state.phase === ActivityPhase.SECOND_RESPONSE) return Boolean(choice);
		if (state.phase === ActivityPhase.REFLECTION) return reflection.trim().length > 0;
		return false;
	});

	const votingAnswers = $derived((question.answers ?? []) as VotingAnswer[]);
</script>

<div class="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-5 px-4 py-6 text-slate-900 dark:text-slate-100">
	<header class="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/90">
		<p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">ICCI · Espacio de debate</p>
		<h1 class="mt-2 text-xl font-semibold">{@html question.question}</h1>
	</header>

	{#if !state}
		<section class="rounded-2xl border border-dashed border-slate-300 p-6 text-center dark:border-slate-700">
			<p class="font-medium">Esperando que el docente inicie la actividad.</p>
		</section>
	{:else if state.phase === ActivityPhase.DISCUSSION}
		<section class="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
			<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Fase de conversación</p>
			<h2 class="mt-2 text-2xl font-semibold">Explica tu razonamiento y escucha una postura distinta.</h2>
			<p class="mt-3 text-sm text-slate-600 dark:text-slate-300">No necesitas llegar a consenso. Identifica al menos un argumento que te haga reconsiderar, precisar o sostener mejor tu posición.</p>
		</section>
	{:else if state.phase === ActivityPhase.RESULTS}
		<section class="rounded-2xl border border-slate-200 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900">
			<h2 class="text-2xl font-semibold">Actividad completada</h2>
			<p class="mt-2 text-slate-600 dark:text-slate-300">Los resultados se mostrarán de forma agregada para apoyar la discusión.</p>
		</section>
	{:else if isSubmitted(state.phase) || saved}
		<section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-100">
			<h2 class="text-xl font-semibold">Respuesta registrada</h2>
			<p class="mt-2">Espera la siguiente fase indicada por el docente.</p>
		</section>
	{:else}
		<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
			{#if state.phase === ActivityPhase.INITIAL_RESPONSE || state.phase === ActivityPhase.SECOND_RESPONSE}
				<p class="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
					{state.phase === ActivityPhase.INITIAL_RESPONSE ? 'Primera respuesta' : 'Segunda respuesta'}
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
					<label for="confidence" class="block text-sm font-medium">¿Qué tan convencido/a estás? {confidence}/5</label>
					<input id="confidence" class="mt-2 w-full" type="range" min="1" max="5" step="1" bind:value={confidence} />
				</div>

				{#if state.phase === ActivityPhase.INITIAL_RESPONSE}
					<div class="mt-5">
						<label for="justification" class="block text-sm font-medium">Resume la razón principal de tu elección.</label>
						<textarea id="justification" maxlength="1000" rows="4" class="mt-2 w-full rounded-xl border border-slate-300 bg-transparent p-3" bind:value={justification}></textarea>
					</div>
				{/if}
			{:else if state.phase === ActivityPhase.REFLECTION}
				<p class="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Reflexión final</p>
				<label for="reflection" class="block text-sm font-medium">¿Qué argumento, duda o idea de otra persona influyó más en tu razonamiento?</label>
				<textarea id="reflection" maxlength="1000" rows="5" class="mt-2 w-full rounded-xl border border-slate-300 bg-transparent p-3" bind:value={reflection}></textarea>
			{/if}

			<button type="button" class="mt-5 w-full rounded-xl bg-slate-900 px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40" disabled={!canSubmit} onclick={submitResponse}>Enviar</button>
			{#if error}<p class="mt-3 text-sm text-red-600">No se pudo registrar: {error}</p>{/if}
		</section>
	{/if}
</div>
